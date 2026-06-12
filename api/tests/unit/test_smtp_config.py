import pytest

from app.admin.smtp_config import SMTPConfig, smtp_runtime_config


def test_smtp_runtime_config_maps_fields():
    config = SMTPConfig(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="pass",
        smtp_from="from@example.com",
        smtp_use_tls=True,
    )

    runtime = smtp_runtime_config(config)

    assert runtime.host == "smtp.example.com"
    assert runtime.port == 587
    assert runtime.user == "user"
    assert runtime.password == "pass"
    assert runtime.from_address == "from@example.com"
    assert runtime.use_tls is True


@pytest.mark.asyncio
async def test_get_smtp_config_uses_env_fallback(db_session):
    from app.admin.smtp_config import get_smtp_config

    config = await get_smtp_config(db_session)

    assert config.smtp_port == 587
    assert isinstance(config.smtp_use_tls, bool)
