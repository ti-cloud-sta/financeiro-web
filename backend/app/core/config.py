from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3306
    DATABASE_NAME: str = "stamariabd"
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = ""
    
    JWT_KEY: str = "stamaria_default_jwt_secret_key_dev"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Google OAuth e Gmail API
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # "development" habilita Swagger/ReDoc (/docs, /redoc, /openapi.json).
    # Qualquer outro valor (padrão "production") os desativa — a API implantada
    # não deve expor documentação pública.
    ENVIRONMENT: str = "production"

    # Usando o conector assíncrono seria ideal, mas para manter simples no ORM padrão do SQLAlchemy
    # usaremos pymysql
    @property
    def DATABASE_URL(self) -> str:
        import urllib.parse
        # Se a senha estiver vazia, omitir os dois pontos
        pwd_part = f":{urllib.parse.quote_plus(self.DATABASE_PASSWORD)}" if self.DATABASE_PASSWORD else ""
        return f"mysql+pymysql://{self.DATABASE_USER}{pwd_part}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
