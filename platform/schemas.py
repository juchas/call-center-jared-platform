from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Request bodies ---

class TenantCreate(BaseModel):
    label: Optional[str] = Field(None, example="Acme Corp")
    openai_key: str = Field(..., example="sk-proj-...")
    sn_instance: str = Field(..., example="myinstance", description="ServiceNow instance name (without .service-now.com)")
    sn_user: str = Field(..., example="admin")
    sn_pass: str = Field(..., example="secret")


class TenantUpdate(BaseModel):
    label: Optional[str] = None
    openai_key: Optional[str] = None
    sn_instance: Optional[str] = None
    sn_user: Optional[str] = None
    sn_pass: Optional[str] = None


# --- Response bodies ---

class TenantResponse(BaseModel):
    id: str
    label: Optional[str]
    status: str
    webhook_url: Optional[str]  # the URL to configure in Twilio
    koyeb_app_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_tenant(cls, tenant) -> "TenantResponse":
        webhook_url = f"{tenant.koyeb_app_url}/voice" if tenant.koyeb_app_url else None
        return cls(
            id=tenant.id,
            label=tenant.label,
            status=tenant.status,
            webhook_url=webhook_url,
            koyeb_app_url=tenant.koyeb_app_url,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
