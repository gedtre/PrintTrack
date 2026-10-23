from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://printtrack@db/printtrack"
    admin_username: str = "admin"
    admin_password: str = ""
    demo_mode: bool = False
    cookie_secure: bool = True
    session_hours: int = 8


settings = Settings()
