from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Restaurant Management API"
    secret_key: str = "dev-only-change-me-not-for-production"
    database_url: str = "sqlite:///./data/restaurant.db"
    access_token_minutes: int = 480
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    tax_rate_bps: int = 1000
    uploads_dir: str = "./data/uploads"
    max_qr_image_bytes: int = 2_097_152  # 2 MB
    # Production bootstrap (used only when the deployed DB is empty):
    # structural minimum — one restaurant and one owner. No demo data is ever
    # seeded in production; menus/tables/staff are created through the app.
    restaurant_name: str = ""
    currency_code: str = "USD"
    timezone: str = "UTC"
    bootstrap_owner_email: str = ""
    bootstrap_owner_password: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
