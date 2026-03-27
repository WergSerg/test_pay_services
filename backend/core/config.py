from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    postgres_host: str = Field("localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(5432, alias="POSTGRES_PORT")
    postgres_user: str = Field("postgres", alias="POSTGRES_USER")
    postgres_password: str = Field("postgres", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field("payments_db", alias="POSTGRES_DB")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # RabbitMQ
    rabbitmq_host: str = Field("localhost", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field("guest", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field("guest", alias="RABBITMQ_PASSWORD")

    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"

    # API
    api_key: str = Field("secret-api-key-2024", alias="API_KEY")
    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8000, alias="API_PORT")

    # Outbox
    outbox_poll_interval: int = Field(2, alias="OUTBOX_POLL_INTERVAL")


settings = Settings()