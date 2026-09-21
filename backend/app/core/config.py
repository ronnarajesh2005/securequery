from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    auth_db_url: str = "postgresql://auth_admin:auth_pass@127.0.0.1:5436/auth_db"
    audit_db_url: str = "postgresql://audit_admin:audit_pass@127.0.0.1:5432/audit_db"
    hospital_a_db_url: str = "postgresql://hospital_admin:hospital_pass@127.0.0.1:5433/hospital_a_db"
    hospital_b_db_url: str = "postgresql://hospital_admin:hospital_pass@127.0.0.1:5434/hospital_b_db"
    hospital_c_db_url: str = "postgresql://hospital_admin:hospital_pass@127.0.0.1:5435/hospital_c_db"
    
    # Secret Key & Algorithm aliases for security module compatibility
    secret_key: str = "supersecretkey123"
    jwt_secret_key: str = "supersecretkey123"
    algorithm: str = "HS256"
    jwt_algorithm: str = "HS256"
    
    # Expiration aliases
    jwt_expire_minutes: int = 60
    access_token_expire_minutes: int = 60

    # Mock mode support
    mock_ollama: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()