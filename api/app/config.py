from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://estimate:change_me@localhost:5432/ai_estimate"
    jwt_secret: str = "dev-secret"
    jwt_expiry_hours: int = 8
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    hermes_url: str = "http://localhost:8080"
    storage_backend: str = "local"
    storage_path: str = "./data"
    default_locale: str = "ja"
    app_env: str = "development"
    calculation_policy_version: str = "1.0.0"
    fx_refresh_interval_seconds: int = 3600

    quotation_company_name: str = "MTECH Corporation"
    quotation_company_brand: str = "MTECH"
    quotation_company_postal_code: str = ""
    quotation_company_address: str = ""
    quotation_company_tel: str = ""
    quotation_company_email: str = ""
    quotation_invoice_registration_number: str = ""
    quotation_payment_terms_ja: str = "納品後30日以内"
    quotation_payment_terms_en: str = "Within 30 days after delivery"
    quotation_validity_days: int = 30
    quotation_bank_details_ja: str = ""
    quotation_bank_details_en: str = ""
    quotation_remarks_ja: str = "ご検討のほど、よろしくお願い申し上げます。"
    quotation_remarks_en: str = "Thank you for your consideration."

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True


settings = Settings()
