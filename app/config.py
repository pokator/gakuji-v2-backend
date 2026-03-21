from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    deepl_key: str
    port: int = 8000
    supabase_url: str = ""
    supabase_key: str = ""
    anki_connect_url: str = "http://localhost:8765"
    anki_connect_timeout: int = 30

settings = Settings()