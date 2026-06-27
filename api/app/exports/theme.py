"""Shared color tokens for branded PDF and Excel exports."""

PRIMARY = "1E3A5F"
PRIMARY_LIGHT = "E8EEF4"
SURFACE = "F8FAFC"
BORDER = "E2E8F0"
BORDER_LIGHT = "CBD5E1"
TEXT_BODY = "1E293B"
TEXT_MUTED = "64748B"
ACCENT = "2563EB"

# Legacy aliases (Excel + backward compat)
BLUE_PRIMARY = PRIMARY
BLUE_LIGHT = PRIMARY_LIGHT
YELLOW_SECTION = SURFACE
YELLOW_TOTAL = PRIMARY_LIGHT
TEXT_ON_PRIMARY = "FFFFFF"
BORDER_LEGACY = "4A76A8"

EXPORT_THEME: dict[str, str] = {
    "primary": PRIMARY,
    "primary_light": PRIMARY_LIGHT,
    "surface": SURFACE,
    "border": BORDER,
    "border_light": BORDER_LIGHT,
    "text_body": TEXT_BODY,
    "text_muted": TEXT_MUTED,
    "accent": ACCENT,
    "blue_primary": BLUE_PRIMARY,
    "blue_light": BLUE_LIGHT,
    "yellow_section": YELLOW_SECTION,
    "yellow_total": YELLOW_TOTAL,
    "text_on_primary": TEXT_ON_PRIMARY,
    "border_legacy": BORDER_LEGACY,
}
