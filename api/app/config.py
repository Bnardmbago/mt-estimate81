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

    quotation_company_name: str = "株式会社 Beyond AI"
    quotation_company_brand: str = "Beyond AI"
    quotation_company_postal_code: str = "103-0027"
    quotation_company_address: str = (
        "東京都中央区日本橋 2丁目1番3号\n"
        "アーバンネット日本橋二丁目ビル 10階"
    )
    quotation_company_tel: str = "03-6262-0742"
    quotation_company_email: str = "ai@beyondai.co.jp"
    quotation_invoice_registration_number: str = ""
    quotation_contact_person: str = ""
    quotation_payment_terms_ja: str = "納品後7日以内"
    quotation_payment_terms_en: str = "Within 7 days after delivery"
    quotation_validity_days: int = 30
    quotation_bank_details_ja: str = (
        "株式会社Beyond AI\n"
        "住信SBIネット銀行 法人第一支店（ 106） 普通口座 2112728"
    )
    quotation_bank_details_en: str = (
        "Beyond AI Co., Ltd.\n"
        "SBI Sumishin Net Bank, Corporate First Branch (106), Ordinary Account 2112728"
    )
    quotation_remarks_ja: str = "ご検討のほど、よろしくお願い申し上げます。"
    quotation_remarks_en: str = "Thank you for your consideration."

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    web_base_url: str = "http://localhost:3000"
    turnstile_secret_key: str = ""
    contact_jwt_expiry_hours: int = 72
    contact_magic_link_ttl_minutes: int = 15
    contact_export_limit: int = 3
    contact_magic_link_rate_limit_per_email: int = 3
    contact_magic_link_rate_limit_per_ip: int = 10

    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/integrations/google/callback"

    canva_client_id: str = ""
    canva_client_secret: str = ""
    canva_redirect_uri: str = "http://localhost:8000/integrations/canva/callback"
    canva_template_proposal_en: str = ""
    canva_template_proposal_ja: str = ""
    canva_template_poc_en: str = ""
    canva_template_poc_ja: str = ""


settings = Settings()
