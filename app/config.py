from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    clerk_secret_key: str
    clerk_authorized_parties: str
    aws_region: str
    aws_s3_bucket_name: str
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def authorized_parties(self) -> list[str]:
        return [
            party.strip()
            for party in self.clerk_authorized_parties.split(",")
            if party.strip()
        ]

settings = Settings() # pyright: ignore[reportCallIssue]