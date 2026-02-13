from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "carrier_load_automation"
    API_KEY: str = "changeme"

    model_config = {"env_file": ".env"}


settings = Settings()
