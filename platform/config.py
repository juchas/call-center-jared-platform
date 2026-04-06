from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    koyeb_token: str
    koyeb_app_id: str
    encryption_key: str
    api_secret_key: str = ""

    # Docker image deployed per tenant — override via TENANT_IMAGE env var to use a fork or private registry
    tenant_image: str = "ghcr.io/juchas/call-center-jared:latest"
    tenant_region: str = "fra"
    tenant_instance_type: str = "nano"

    class Config:
        env_file = ".env"


settings = Settings()
