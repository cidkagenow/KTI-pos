from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment: "development" or "production"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql://ktipos:ktipos2024@localhost:5432/ktipos"
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"
    IGV_RATE: float = 0.18

    # CORS — comma-separated origins, "*" for development
    CORS_ORIGINS: str = "*"

    # SUNAT Direct Integration
    SUNAT_ENV: str = "beta"  # "beta" or "production"
    SUNAT_SOL_USER: str = "MODDATOS"
    SUNAT_SOL_PASSWORD: str = "moddatos"
    SUNAT_CERT_PATH: str = ""
    SUNAT_CERT_PASSWORD: str = ""

    # Peru Consult API
    PERU_CONSULT_API_TOKEN: str = ""

    # Empresa
    EMPRESA_RUC: str = "20525996957"
    EMPRESA_RAZON_SOCIAL: str = "INVERSIONES KTI D & E E.I.R.L."
    EMPRESA_DIRECCION: str = ""

    # Gemini AI
    GEMINI_API_KEY: str = ""

    # SMTP (Gmail)
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    # Accountant email (for Registro de Ventas)
    ACCOUNTANT_EMAIL: str = ""

    # Store Server (separate 24/7 VM)
    STORE_SERVER_URL: str = ""
    STORE_API_KEY: str = ""

    # Dashboard (push stats to remote dashboard)
    DASHBOARD_URL: str = ""
    DASHBOARD_API_KEY: str = ""
    DASHBOARD_BRANCH_ID: str = "branch1"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
