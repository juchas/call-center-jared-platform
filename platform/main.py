from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import koyeb as koyeb_client
from .crypto import decrypt, encrypt
from .database import AsyncSessionLocal, get_session, init_db
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
    """Provision a new tenant: encrypt credentials, store in DB, deploy to Koyeb."""
    tenant = Tenant(
        label=body.label,
        enc_openai_key=encrypt(body.openai_key),
        enc_sn_instance=encrypt(body.sn_instance),
        enc_sn_user=encrypt(body.sn_user),
        enc_sn_pass=encrypt(body.sn_pass),
        status="provisioning",
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    try:
        result = await koyeb_client.deploy_tenant(
            tenant_id=tenant.id,
            openai_key=body.openai_key,
            sn_instance=body.sn_instance,
            sn_user=body.sn_user,
            sn_pass=body.sn_pass,
        )
        service_id = result["service"]["id"]
        app_url = koyeb_client.extract_app_url(result)

        tenant.koyeb_service_id = service_id
        tenant.koyeb_app_url = app_url
        tenant.status = "deploying"
        await db.commit()
        await db.refresh(tenant)
    except Exception as exc:
        tenant.status = "error"
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Koyeb deployment failed: {exc}")

    return TenantResponse.from_tenant(tenant)


@app.get("/api/tenants", response_model=List[TenantResponse])
async def list_tenants(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    return [TenantResponse.from_tenant(t) for t in tenants]


@app.get("/api/tenants/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, db: AsyncSession = Depends(get_session)):
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Sync status from Koyeb
    if tenant.koyeb_service_id:
        try:
            svc = await koyeb_client.get_service(tenant.koyeb_service_id)
            tenant.status = svc["service"].get("status", tenant.status).lower()
            if not tenant.koyeb_app_url:
                tenant.koyeb_app_url = koyeb_client.extract_app_url(svc)
            await db.commit()
            await db.refresh(tenant)
        except Exception:
            pass  # return stale status rather than error

    return TenantResponse.from_tenant(tenant)


@app.put("/api/tenants/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update credentials (re-deploys the Koyeb service with new env vars)."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if body.label is not None:
        tenant.label = body.label

    # Decrypt existing values, apply updates
    openai_key = decrypt(tenant.enc_openai_key)
    sn_instance = decrypt(tenant.enc_sn_instance)
    sn_user = decrypt(tenant.enc_sn_user)
    sn_pass = decrypt(tenant.enc_sn_pass)

    if body.openai_key:
        openai_key = body.openai_key
        tenant.enc_openai_key = encrypt(openai_key)
    if body.sn_instance:
        sn_instance = body.sn_instance
        tenant.enc_sn_instance = encrypt(sn_instance)
    if body.sn_user:
        sn_user = body.sn_user
        tenant.enc_sn_user = encrypt(sn_user)
    if body.sn_pass:
        sn_pass = body.sn_pass
        tenant.enc_sn_pass = encrypt(sn_pass)

    await db.commit()

    if tenant.koyeb_service_id and any([body.openai_key, body.sn_instance, body.sn_user, body.sn_pass]):
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

    await db.refresh(tenant)
    return TenantResponse.from_tenant(tenant)


@app.delete("/api/tenants/{tenant_id}", status_code=204)
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Delete the Koyeb service and remove the tenant record."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if tenant.koyeb_service_id:
        try:
            await koyeb_client.delete_service(tenant.koyeb_service_id)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Koyeb teardown failed: {exc}")

    await db.delete(tenant)
    await db.commit()
