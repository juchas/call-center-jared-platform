from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: str = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    label: str = Column(String(255), nullable=True)

    # Koyeb
    koyeb_service_id: str = Column(String(255), nullable=True)
    koyeb_app_url: str = Column(String(512), nullable=True)
    status: str = Column(String(64), default="provisioning")

    # Twilio — phone number bought for this tenant
    twilio_phone_number: str = Column(String(32), nullable=True)   # e.g. +48221234567
    twilio_phone_sid: str = Column(String(64), nullable=True)       # PN... resource SID
    twilio_country: str = Column(String(8), nullable=True)          # ISO country code

    # Encrypted credentials — never store plaintext
    enc_openai_key: str = Column(Text, nullable=False)
    enc_sn_instance: str = Column(Text, nullable=False)
    enc_sn_user: str = Column(Text, nullable=False)
    enc_sn_pass: str = Column(Text, nullable=False)
    enc_twilio_sid: str = Column(Text, nullable=True)
    enc_twilio_token: str = Column(Text, nullable=True)

    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
