"""Koyeb REST API client.

Deploys one CallCenterJared service per tenant, each with its own
credentials injected as environment variables.

Ref: https://www.koyeb.com/docs/reference/api
"""

import httpx

from .config import settings

KOYEB_API = "https://app.koyeb.com/v1"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.koyeb_token}"}


async def deploy_tenant(
    tenant_id: str,
    openai_key: str,
    sn_instance: str,
    sn_user: str,
    sn_pass: str,
) -> dict:
    """Create a new Koyeb service for this tenant. Returns the Koyeb service object."""
    service_name = f"ccj-{tenant_id[:8]}"

    payload = {
        "service": {
            "name": service_name,
            "app_id": settings.koyeb_app_id,
            "definition": {
                "name": service_name,
                "type": "WEB",
                "docker": {
                    "image": settings.tenant_image,
                },
                "env": [
                    {"key": "OPENAI_API_KEY", "value": openai_key},
                    {"key": "SERVICENOW_INSTANCE", "value": sn_instance},
                    {"key": "SERVICENOW_USERNAME", "value": sn_user},
                    {"key": "SERVICENOW_PASSWORD", "value": sn_pass},
                    {"key": "PORT", "value": "8000"},
                ],
                "ports": [{"port": 8000, "protocol": "http"}],
                "routes": [{"port": 8000, "path": "/"}],
                "regions": [settings.tenant_region],
                "instance_types": [{"type": settings.tenant_instance_type}],
                "scaling": {"fixed": {"targets": 1}},
            },
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{KOYEB_API}/services",
            json=payload,
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def redeploy_tenant(
    service_id: str,
    openai_key: str,
    sn_instance: str,
    sn_user: str,
    sn_pass: str,
) -> dict:
    """Update env vars on an existing service (triggers a redeploy)."""
    payload = {
        "definition": {
            "env": [
                {"key": "OPENAI_API_KEY", "value": openai_key},
                {"key": "SERVICENOW_INSTANCE", "value": sn_instance},
                {"key": "SERVICENOW_USERNAME", "value": sn_user},
                {"key": "SERVICENOW_PASSWORD", "value": sn_pass},
            ]
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{KOYEB_API}/services/{service_id}",
            json=payload,
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def delete_service(service_id: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{KOYEB_API}/services/{service_id}",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()


async def get_service(service_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{KOYEB_API}/services/{service_id}",
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


def extract_app_url(koyeb_response: dict) -> str | None:
    """Pull the public hostname out of a Koyeb service creation response."""
    try:
        deployments = koyeb_response["service"]["definition"]["routes"]
        # Koyeb public URL format: <service-name>-<org>.koyeb.app
        # The deployment hostname is returned in the service object
        domain = koyeb_response["service"].get("latest_deployment", {}).get("urls", [None])[0]
        if domain:
            return f"https://{domain}"
    except (KeyError, IndexError, TypeError):
        pass
    return None
