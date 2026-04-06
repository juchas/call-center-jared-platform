from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import koyeb as koyeb_client
from . import twilio_client
from .crypto import decrypt, encrypt
from .database import get_session, init_db
from .models import Tenant
from .schemas import TenantCreate, TenantResponse, TenantUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Call Center Jared Platform",
    description="Multi-tenant SaaS control plane for CallCenterJared deployments",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------

@app.post("/api/tenants", response_model=TenantResponse, status_code=201)
async def create_tenant(
    body: TenantCreate,
    db: AsyncSession = Depends(get_session),
):
    """Provision a new tenant: deploy Koyeb container, buy + configure Twilio number."""
    tenant = Tenant(
        label=body.label,
        twilio_country=body.phone_country,
        enc_openai_key=encrypt(body.openai_key),
        enc_sn_instance=encrypt(body.sn_instance),
        enc_sn_user=encrypt(body.sn_user),
        enc_sn_pass=encrypt(body.sn_pass),
        enc_twilio_sid=encrypt(body.twilio_sid) if body.twilio_sid else None,
        enc_twilio_token=encrypt(body.twilio_token) if body.twilio_token else None,
        status="provisioning",
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    # 1. Deploy Koyeb container
    try:
        result = await koyeb_client.deploy_tenant(
            tenant_id=tenant.id,
            openai_key=body.openai_key,
            sn_instance=body.sn_instance,
            sn_user=body.sn_user,
            sn_pass=body.sn_pass,
        )
        tenant.koyeb_service_id = result["service"]["id"]
        tenant.koyeb_app_url = koyeb_client.extract_app_url(result)
        tenant.status = "deploying"
        await db.commit()
        await db.refresh(tenant)
    except Exception as exc:
        tenant.status = "error"
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Koyeb deployment failed: {exc}")

    # 2. Buy + configure Twilio number (only if credentials provided and webhook URL is available)
    if body.twilio_sid and body.twilio_token and tenant.koyeb_app_url:
        webhook_url = f"{tenant.koyeb_app_url}/voice"
        try:
            twilio_result = await twilio_client.provision_number(
                account_sid=body.twilio_sid,
                auth_token=body.twilio_token,
                webhook_url=webhook_url,
                country_code=body.phone_country,
            )
            tenant.twilio_phone_number = twilio_result["phone_number"]
            tenant.twilio_phone_sid = twilio_result["phone_sid"]
            await db.commit()
            await db.refresh(tenant)
        except Exception as exc:
            # Non-fatal: Koyeb is up, Twilio provisioning failed
            # Tenant can retry via PUT or /provision-number endpoint
            print(f"Twilio provisioning failed for tenant {tenant.id}: {exc}")

    return TenantResponse.from_tenant(tenant)


@app.get("/api/tenants", response_model=List[TenantResponse])
async def list_tenants(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return [TenantResponse.from_tenant(t) for t in result.scalars().all()]


@app.get("/api/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, db: AsyncSession = Depends(get_session)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Sync Koyeb status
    if tenant.koyeb_service_id:
        try:
            svc = await koyeb_client.get_service(tenant.koyeb_service_id)
            tenant.status = svc["service"].get("status", tenant.status).lower()
            # Capture URL if it wasn't available at creation time
            if not tenant.koyeb_app_url:
                tenant.koyeb_app_url = koyeb_client.extract_app_url(svc)
            await db.commit()
            await db.refresh(tenant)
        except Exception:
            pass

    # If URL is now available but Twilio number is still missing, retry provisioning
    if (
        tenant.koyeb_app_url
        and not tenant.twilio_phone_number
        and tenant.enc_twilio_sid
        and tenant.enc_twilio_token
    ):
        try:
            twilio_result = await twilio_client.provision_number(
                account_sid=decrypt(tenant.enc_twilio_sid),
                auth_token=decrypt(tenant.enc_twilio_token),
                webhook_url=f"{tenant.koyeb_app_url}/voice",
                country_code=tenant.twilio_country or "US",
            )
            tenant.twilio_phone_number = twilio_result["phone_number"]
            tenant.twilio_phone_sid = twilio_result["phone_sid"]
            await db.commit()
            await db.refresh(tenant)
        except Exception as exc:
            print(f"Twilio retry failed for tenant {tenant_id}: {exc}")

    return TenantResponse.from_tenant(tenant)


@app.put("/api/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update credentials. Triggers Koyeb redeploy and Twilio webhook update as needed."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.label is not None:
        tenant.label = body.label

    # Decrypt current values, apply updates
    openai_key = decrypt(tenant.enc_openai_key)
    sn_instance = decrypt(tenant.enc_sn_instance)
    sn_user = decrypt(tenant.enc_sn_user)
    sn_pass = decrypt(tenant.enc_sn_pass)

    creds_changed = False
    for field, enc_field, current in [
        (body.openai_key, "enc_openai_key", openai_key),
        (body.sn_instance, "enc_sn_instance", sn_instance),
        (body.sn_user, "enc_sn_user", sn_user),
        (body.sn_pass, "enc_sn_pass", sn_pass),
    ]:
        if field:
            setattr(tenant, enc_field, encrypt(field))
            creds_changed = True

    # Refresh local vars after potential updates
    openai_key = decrypt(tenant.enc_openai_key)
    sn_instance = decrypt(tenant.enc_sn_instance)
    sn_user = decrypt(tenant.enc_sn_user)
    sn_pass = decrypt(tenant.enc_sn_pass)

    twilio_sid_updated = False
    if body.twilio_sid:
        tenant.enc_twilio_sid = encrypt(body.twilio_sid)
        twilio_sid_updated = True
    if body.twilio_token:
        tenant.enc_twilio_token = encrypt(body.twilio_token)
        twilio_sid_updated = True

    await db.commit()

    # Redeploy Koyeb if app credentials changed
    if creds_changed and tenant.koyeb_service_id:
        try:
            await koyeb_client.redeploy_tenant(
                service_id=tenant.koyeb_service_id,
                openai_key=openai_key,
                sn_instance=sn_instance,
                sn_user=sn_user,
                sn_pass=sn_pass,
            )
            tenant.status = "deploying"
            await db.commit()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Koyeb redeploy failed: {exc}")

    # Update Twilio webhook if Twilio creds changed and number exists
    if twilio_sid_updated and tenant.twilio_phone_sid and tenant.koyeb_app_url:
        try:
            await twilio_client.update_webhook(
                account_sid=decrypt(tenant.enc_twilio_sid),
                auth_token=decrypt(tenant.enc_twilio_token),
                phone_sid=tenant.twilio_phone_sid,
                webhook_url=f"{tenant.koyeb_app_url}/voice",
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Twilio webhook update failed: {exc}")

    await db.refresh(tenant)
    return TenantResponse.from_tenant(tenant)


@app.post("/api/tenants/{tenant_id}/provision-number", response_model=TenantResponse)
async def provision_number(
    tenant_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Manually trigger Twilio number provisioning (useful if it failed at creation time)."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not tenant.enc_twilio_sid or not tenant.enc_twilio_token:
        raise HTTPException(status_code=400, detail="Twilio credentials not configured for this tenant")
    if not tenant.koyeb_app_url:
        raise HTTPException(status_code=400, detail="Koyeb URL not yet available — wait for deployment")
    if tenant.twilio_phone_number:
        raise HTTPException(status_code=409, detail=f"Number already provisioned: {tenant.twilio_phone_number}")

    try:
        result = await twilio_client.provision_number(
            account_sid=decrypt(tenant.enc_twilio_sid),
            auth_token=decrypt(tenant.enc_twilio_token),
            webhook_url=f"{tenant.koyeb_app_url}/voice",
            country_code=tenant.twilio_country or "US",
        )
        tenant.twilio_phone_number = result["phone_number"]
        tenant.twilio_phone_sid = result["phone_sid"]
        await db.commit()
        await db.refresh(tenant)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Twilio provisioning failed: {exc}")

    return TenantResponse.from_tenant(tenant)


@app.delete("/api/tenants/{tenant_id}", status_code=204)
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Tear down Koyeb service, release Twilio number, delete tenant record."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Release Twilio number first (stops billing)
    if tenant.twilio_phone_sid and tenant.enc_twilio_sid and tenant.enc_twilio_token:
        try:
            await twilio_client.release_number(
                account_sid=decrypt(tenant.enc_twilio_sid),
                auth_token=decrypt(tenant.enc_twilio_token),
                phone_sid=tenant.twilio_phone_sid,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Twilio number release failed: {exc}")

    # Tear down Koyeb service
    if tenant.koyeb_service_id:
        try:
            await koyeb_client.delete_service(tenant.koyeb_service_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Koyeb teardown failed: {exc}")

    await db.delete(tenant)
    await db.commit()
