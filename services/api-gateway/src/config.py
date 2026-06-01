from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # URL-ы внутренних сервисов
    service_notes_url: str = "http://localhost:8001"
    service_ai_url: str = "http://localhost:8002"
    service_search_url: str = "http://localhost:8003"

    # Redis (для rate limiting, если нужно)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Logging
    log_level: str = "INFO"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()