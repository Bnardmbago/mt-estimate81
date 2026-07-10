from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.storage.factory import get_storage_backend

DEFAULT_BANK_DETAILS_JA = (
    "株式会社Beyond AI\n"
    "住信SBIネット銀行 法人第一支店（ 106） 普通口座 2112728"
)
DEFAULT_BANK_DETAILS_EN = (
    "Beyond AI Co., Ltd.\n"
    "SBI Sumishin Net Bank, Corporate First Branch (106), Ordinary Account 2112728"
)
DEFAULT_POSTAL_CODE = "103-0027"
DEFAULT_ADDRESS_LINES_JA = [
    "東京都中央区日本橋 2丁目1番3号",
    "アーバンネット日本橋二丁目ビル 10階",
]
DEFAULT_COMPANY_TEL = "03-6262-0742"
DEFAULT_COMPANY_EMAIL = "ai@beyondai.co.jp"

DEFAULT_LOGO_SVG = (
    Path(__file__).resolve().parents[1] / "exports" / "templates" / "assets" / "BI_logo.svg"
)
DEFAULT_LOGO_PNG = (
    Path(__file__).resolve().parents[1] / "exports" / "templates" / "assets" / "BI_logo.png"
)

ALLOWED_LOGO_EXTENSIONS = {"png", "jpg", "jpeg", "svg", "webp"}
MAX_LOGO_BYTES = 2 * 1024 * 1024
LOGO_STORAGE_PREFIX = "system/quotation-logo"


@dataclass(frozen=True)
class QuotationCompanyConfig:
    postal_code: str
    address: str
    tel: str
    email: str
    bank_details_ja: str
    bank_details_en: str
    logo_storage_path: str | None
    has_custom_logo: bool


async def _get_config_row(db: AsyncSession):
    from app.models.system_config import SystemConfig

    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemConfig(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


def _first_nonempty(*values: str | None, fallback: str) -> str:
    for value in values:
        if value is not None and value.strip():
            return value.strip()
    return fallback


def _default_address() -> str:
    configured = settings.quotation_company_address.strip()
    if configured:
        return configured
    return "\n".join(DEFAULT_ADDRESS_LINES_JA)


async def get_quotation_company_config(db: AsyncSession) -> QuotationCompanyConfig:
    row = await _get_config_row(db)
    logo_path = (row.quotation_logo_storage_path or "").strip() or None
    return QuotationCompanyConfig(
        postal_code=_first_nonempty(
            row.quotation_company_postal_code,
            settings.quotation_company_postal_code,
            fallback=DEFAULT_POSTAL_CODE,
        ),
        address=_first_nonempty(
            row.quotation_company_address,
            settings.quotation_company_address,
            fallback=_default_address(),
        ),
        tel=_first_nonempty(
            row.quotation_company_tel,
            settings.quotation_company_tel,
            fallback=DEFAULT_COMPANY_TEL,
        ),
        email=_first_nonempty(
            row.quotation_company_email,
            settings.quotation_company_email,
            fallback=DEFAULT_COMPANY_EMAIL,
        ),
        bank_details_ja=_first_nonempty(
            row.quotation_bank_details_ja,
            settings.quotation_bank_details_ja,
            fallback=DEFAULT_BANK_DETAILS_JA,
        ),
        bank_details_en=_first_nonempty(
            row.quotation_bank_details_en,
            settings.quotation_bank_details_en,
            fallback=DEFAULT_BANK_DETAILS_EN,
        ),
        logo_storage_path=logo_path,
        has_custom_logo=bool(logo_path),
    )


async def update_quotation_company_config(
    db: AsyncSession,
    *,
    postal_code: str | None = None,
    address: str | None = None,
    tel: str | None = None,
    email: str | None = None,
    bank_details_ja: str | None = None,
    bank_details_en: str | None = None,
) -> QuotationCompanyConfig:
    row = await _get_config_row(db)

    if postal_code is not None:
        row.quotation_company_postal_code = postal_code.strip() or None
    if address is not None:
        row.quotation_company_address = address.strip() or None
    if tel is not None:
        row.quotation_company_tel = tel.strip() or None
    if email is not None:
        row.quotation_company_email = email.strip() or None
    if bank_details_ja is not None:
        row.quotation_bank_details_ja = bank_details_ja.strip() or None
    if bank_details_en is not None:
        row.quotation_bank_details_en = bank_details_en.strip() or None

    row.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return await get_quotation_company_config(db)


def _logo_extension(filename: str | None, content_type: str | None) -> str:
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ALLOWED_LOGO_EXTENSIONS:
            return "jpg" if ext == "jpeg" else ext
    if content_type:
        mapping = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/svg+xml": "svg",
            "image/webp": "webp",
        }
        mapped = mapping.get(content_type.lower())
        if mapped:
            return mapped
    raise ValueError("Logo must be PNG, JPG, SVG, or WebP")


async def save_quotation_logo(
    db: AsyncSession,
    *,
    content: bytes,
    filename: str | None,
    content_type: str | None,
) -> QuotationCompanyConfig:
    if not content:
        raise ValueError("Logo file is empty")
    if len(content) > MAX_LOGO_BYTES:
        raise ValueError("Logo file must be 2MB or smaller")

    extension = _logo_extension(filename, content_type)
    storage_path = f"{LOGO_STORAGE_PREFIX}.{extension}"
    storage = get_storage_backend()

    row = await _get_config_row(db)
    previous = (row.quotation_logo_storage_path or "").strip()
    await storage.save(storage_path, content)
    row.quotation_logo_storage_path = storage_path
    row.updated_at = datetime.utcnow()
    await db.commit()

    if previous and previous != storage_path and await storage.exists(previous):
        await storage.delete(previous)

    return await get_quotation_company_config(db)


async def clear_quotation_logo(db: AsyncSession) -> QuotationCompanyConfig:
    row = await _get_config_row(db)
    previous = (row.quotation_logo_storage_path or "").strip()
    if previous:
        storage = get_storage_backend()
        if await storage.exists(previous):
            await storage.delete(previous)
    row.quotation_logo_storage_path = None
    row.updated_at = datetime.utcnow()
    await db.commit()
    return await get_quotation_company_config(db)


async def read_quotation_logo_bytes(
    db: AsyncSession,
) -> tuple[bytes, str]:
    """Return (content, media_type) for custom logo or bundled default."""
    config = await get_quotation_company_config(db)
    if config.logo_storage_path:
        storage = get_storage_backend()
        if await storage.exists(config.logo_storage_path):
            content = await storage.read(config.logo_storage_path)
            ext = config.logo_storage_path.rsplit(".", 1)[-1].lower()
            media_types = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "svg": "image/svg+xml",
                "webp": "image/webp",
            }
            return content, media_types.get(ext, "application/octet-stream")

    if DEFAULT_LOGO_PNG.exists():
        return DEFAULT_LOGO_PNG.read_bytes(), "image/png"
    if DEFAULT_LOGO_SVG.exists():
        return DEFAULT_LOGO_SVG.read_bytes(), "image/svg+xml"
    raise FileNotFoundError("Default quotation logo is missing")


def logo_data_uri(content: bytes, media_type: str) -> str:
    import base64

    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


async def resolve_logo_for_export(db: AsyncSession) -> dict[str, str | bytes | None]:
    """Return logo fields for quotation export context."""
    config = await get_quotation_company_config(db)
    if config.logo_storage_path:
        storage = get_storage_backend()
        if await storage.exists(config.logo_storage_path):
            content = await storage.read(config.logo_storage_path)
            ext = config.logo_storage_path.rsplit(".", 1)[-1].lower()
            media_types = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "svg": "image/svg+xml",
                "webp": "image/webp",
            }
            media_type = media_types.get(ext, "application/octet-stream")
            return {
                "logo_src": logo_data_uri(content, media_type),
                "logo_bytes": content,
                "logo_media_type": media_type,
                "logo_ext": ext,
            }

    return {
        "logo_src": "assets/BI_logo.svg",
        "logo_bytes": None,
        "logo_media_type": "image/svg+xml",
        "logo_ext": "svg",
    }
