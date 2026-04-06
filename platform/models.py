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

    # Encrypted credentials — never store plaintext
    enc_openai_key: str = Column(Text, nullable=False)
    enc_sn_instance: str = Column(Text, nullable=False)
    enc_sn_user: str = Column(Text, nullable=False)
    enc_sn_pass: str = Column(Text, nullable=False)

    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
