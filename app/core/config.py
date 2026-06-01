from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Lead Line API", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_prefix: str = Field(default="/v1", alias="API_PREFIX")

    database_url: str = Field(
        default="postgresql+asyncpg://leadline:leadline@localhost:5432/leadline",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_access_key_id: str | None = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str | None = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_endpoint_url: str | None = Field(default=None, alias="AWS_ENDPOINT_URL")

    sqs_ai_jobs_queue_url: str | None = Field(default=None, alias="SQS_AI_JOBS_QUEUE_URL")
    sqs_routing_jobs_queue_url: str | None = Field(default=None, alias="SQS_ROUTING_JOBS_QUEUE_URL")
    sqs_email_jobs_queue_url: str | None = Field(default=None, alias="SQS_EMAIL_JOBS_QUEUE_URL")
    sqs_sms_jobs_queue_url: str | None = Field(default=None, alias="SQS_SMS_JOBS_QUEUE_URL")
    sqs_sequence_jobs_queue_url: str | None = Field(
        default=None,
        alias="SQS_SEQUENCE_JOBS_QUEUE_URL",
    )
    sqs_integration_jobs_queue_url: str | None = Field(
        default=None,
        alias="SQS_INTEGRATION_JOBS_QUEUE_URL",
    )

    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_audience: str = Field(default="leadline-api", alias="JWT_AUDIENCE")
    jwt_issuer: str = Field(default="leadline", alias="JWT_ISSUER")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model_mini: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL_MINI")
    openai_model_full: str = Field(default="gpt-4o", alias="OPENAI_MODEL_FULL")
    ai_prompt_version: str = Field(default="v1", alias="AI_PROMPT_VERSION")
    ai_cache_ttl_seconds: int = Field(default=3600, alias="AI_CACHE_TTL_SECONDS")

    ses_from_email: str | None = Field(default=None, alias="SES_FROM_EMAIL")
    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_from_phone: str | None = Field(default=None, alias="TWILIO_FROM_PHONE")

    hubspot_api_base_url: str = Field(
        default="https://api.hubapi.com",
        alias="HUBSPOT_API_BASE_URL",
    )
    hubspot_access_token: str | None = Field(default=None, alias="HUBSPOT_ACCESS_TOKEN")
    hubspot_webhook_secret: str | None = Field(default=None, alias="HUBSPOT_WEBHOOK_SECRET")

    google_calendar_api_base_url: str = Field(
        default="https://www.googleapis.com/calendar/v3",
        alias="GOOGLE_CALENDAR_API_BASE_URL",
    )
    google_calendar_access_token: str | None = Field(
        default=None,
        alias="GOOGLE_CALENDAR_ACCESS_TOKEN",
    )

    slack_webhook_url: str | None = Field(default=None, alias="SLACK_WEBHOOK_URL")
    slack_signing_secret: str | None = Field(default=None, alias="SLACK_SIGNING_SECRET")

    svix_server_url: str = Field(default="https://api.svix.com", alias="SVIX_SERVER_URL")
    svix_token: str | None = Field(default=None, alias="SVIX_TOKEN")
    svix_app_id: str | None = Field(default=None, alias="SVIX_APP_ID")
    svix_webhook_secret: str | None = Field(default=None, alias="SVIX_WEBHOOK_SECRET")

    integration_max_retries: int = Field(default=3, alias="INTEGRATION_MAX_RETRIES")

    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")
    otel_service_name: str = Field(default="leadline-api", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )

    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=120, alias="RATE_LIMIT_PER_MINUTE")

    audit_log_enabled: bool = Field(default=True, alias="AUDIT_LOG_ENABLED")
    pii_masking_enabled: bool = Field(default=True, alias="PII_MASKING_ENABLED")

    app_data_encryption_key: str | None = Field(default=None, alias="APP_DATA_ENCRYPTION_KEY")
    enforce_tenant_header_match: bool = Field(default=True, alias="ENFORCE_TENANT_HEADER_MATCH")

    auto_create_tables: bool = Field(default=False, alias="AUTO_CREATE_TABLES")


@lru_cache
def get_settings() -> Settings:
    return Settings()
