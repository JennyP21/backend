from pydantic_settings import BaseSettings, SettingsConfigDict


class TestSettings(BaseSettings):
    database_url: str

    model_config = SettingsConfigDict(
        env_file=".env.test",
        env_prefix="TEST_",
        extra="ignore",
    )


test_settings = TestSettings()  # pyright: ignore[reportCallIssue]