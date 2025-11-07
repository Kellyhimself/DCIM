from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=False,
	)

	environment: str = Field(default="dev")
	secret_key: str = Field(default="dev-secret")

	database_url: str = Field(default="postgresql+psycopg://app:app@localhost:5432/app")
	redis_url: str = Field(default="redis://localhost:6379/0")

	s3_endpoint: str = Field(default="http://minio:9000")
	s3_public_endpoint: str = Field(default="http://192.168.1.105:9000")  # URL that mobile clients can access
	s3_bucket: str = Field(default="app")
	s3_access_key: str = Field(default="minioadmin")
	s3_secret_key: str = Field(default="minioadmin")
	s3_region: str = Field(default="auto")

	access_token_expire_minutes: int = Field(default=30)
	refresh_token_expire_minutes: int = Field(default=60 * 24 * 30)

	# M-Pesa Daraja (sandbox by default)
	mpesa_env: str = Field(default="sandbox")
	mpesa_consumer_key: str = Field(default="")
	mpesa_consumer_secret: str = Field(default="")
	mpesa_short_code: str = Field(default="")
	mpesa_passkey: str = Field(default="")
	mpesa_callback_url: str = Field(default="")

	# OpenAI (for NLP entity extraction)
	openai_api_key: Optional[str] = Field(default=None)


settings = Settings()
