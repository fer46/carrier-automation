import warnings

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "carrier_load_automation"
    API_KEY: str = "changeme"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8000"
    DOCS_ENABLED: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()

if settings.API_KEY == "changeme":
    warnings.warn(
        "API_KEY is set to the default value 'changeme'. "
        "Set a strong API_KEY in your .env file for production.",
        stacklevel=1,
    )
