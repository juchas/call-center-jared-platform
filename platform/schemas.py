from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class TenantCreate(BaseModel):
    label: Optional[str] = Field(None, example="Acme Corp")

    # OpenAI
    openai_key: str = Field(..., example="sk-proj-...")

    # ServiceNow
    sn_instance: str = Field(..., example="myinstance", description="Instance name without .service-now.com")
    sn_user: str = Field(..., example="admin")
    sn_pass: str = Field(..., example="secret")

    # Twilio (optional — if omitted, no phone number is provisioned)
    twilio_sid: Optional[str] = Field(None, example="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    twilio_token: Optional[str] = Field(None, example="your_auth_token")
    phone_country: str = Field("US", example="PL", description="ISO country code for number search")


class TenantUpdate(BaseModel):
    label: Optional[str] = None

    # OpenAI
    openai_key: Optional[str] = None

    # ServiceNow
    sn_instance: Optional[str] = None
    sn_user: Optional[str] = None
    sn_pass: Optional[str] = None

    # Twilio
    twilio_sid: Optional[str] = None
    twilio_token: Optional[str] = None


# ---------------------------------------------------------------------------
# Response bodies
# ---------------------------------------------------------------------------

class TenantResponse(BaseModel):
    id: str
    label: Optional[str]
    status: str
    phone_number: Optional[str]   # the number callers dial
    webhook_url: Optional[str]    # the URL set on that number
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
            phone_number=tenant.twilio_phone_number,
            webhook_url=webhook_url,
            koyeb_app_url=tenant.koyeb_app_url,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )
