from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    koyeb_token: str
    koyeb_app_id: str
    encryption_key: str
    api_secret_key: str = ""

    # Docker image deployed per tenant — override to use a custom registry
    tenant_image: str = "docker.io/youjared/callcenterjared:latest"
    tenant_region: str = "fra"
    tenant_instance_type: str = "nano"

    class Config:
        env_file = ".env"


settings = Settings()
