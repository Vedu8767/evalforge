from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://evalforge:evalforge_dev@localhost:5432/evalforge"
    database_url_sync: str = "postgresql://evalforge:evalforge_dev@localhost:5432/evalforge"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080

    # Encryption
    encryption_key: str = "change-me-32-bytes-hex-in-prod!!"

    # OpenAI (optional — leave empty to use Ollama)
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Ollama (free local AI — http://localhost:11434)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embed_model: str = "nomic-embed-text"

    # Billing (optional — needed only for Stripe)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    stripe_team_price_id: str = ""

    # Email (optional)
    resend_api_key: str = ""
    email_from: str = "noreply@evalforge.app"

    # App
    frontend_url: str = "http://localhost:3000"
    environment: str = "development"
    log_level: str = "INFO"
    sentry_dsn: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
