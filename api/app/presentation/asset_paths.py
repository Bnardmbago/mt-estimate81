"""Storage path helpers for Cover / presentation assets.

Assets must live under ``uploads/`` so they persist on the Docker volume
mounted at ``/data/uploads`` (``presentation-assets/`` at the storage root
was ephemeral and wiped on container recreate).
"""

from __future__ import annotations

from pathlib import PurePosixPath

DRAFT_ASSET_ROOT = "uploads/presentation-drafts"
TEMPLATE_ASSET_ROOT = "uploads/presentation-assets"
LEGACY_DRAFT_ASSET_ROOT = "presentation-drafts"
LEGACY_TEMPLATE_ASSET_ROOT = "presentation-assets"

_ALLOWED_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".svg"})


def draft_asset_prefix(draft_id: str) -> str:
    return f"{DRAFT_ASSET_ROOT}/{draft_id}"


def template_asset_prefix(template_id: str) -> str:
    return f"{TEMPLATE_ASSET_ROOT}/{template_id}"


def draft_asset_path(draft_id: str, asset_id: str, extension: str) -> str:
    return f"{draft_asset_prefix(draft_id)}/{asset_id}{extension}"


def template_asset_path(template_id: str, asset_id: str, extension: str) -> str:
    return f"{template_asset_prefix(template_id)}/{asset_id}{extension}"


def promote_destination(template_id: str, filename: str) -> str:
    return f"{TEMPLATE_ASSET_ROOT}/{template_id}/{filename}"


def is_presentation_asset_path(path: str) -> bool:
    return path.startswith(
        (
            f"{DRAFT_ASSET_ROOT}/",
            f"{TEMPLATE_ASSET_ROOT}/",
            f"{LEGACY_DRAFT_ASSET_ROOT}/",
            f"{LEGACY_TEMPLATE_ASSET_ROOT}/",
        )
    )


def draft_prefixes_for(draft_id: str) -> tuple[str, ...]:
    """Current + legacy prefixes for a draft (read/list/cleanup)."""
    return (
        draft_asset_prefix(draft_id),
        f"{LEGACY_DRAFT_ASSET_ROOT}/{draft_id}",
    )


def template_prefixes_for(template_id: str) -> tuple[str, ...]:
    return (
        template_asset_prefix(template_id),
        f"{LEGACY_TEMPLATE_ASSET_ROOT}/{template_id}",
    )


def find_asset_under_prefixes(
    candidates: list[str],
    *,
    prefixes: tuple[str, ...],
    asset_id: str,
) -> str | None:
    """Return the storage path whose stem matches ``asset_id`` under any prefix."""
    prefix_paths = {PurePosixPath(prefix) for prefix in prefixes}
    for candidate in candidates:
        pure = PurePosixPath(candidate)
        if pure.parent not in prefix_paths:
            continue
        if pure.stem != asset_id:
            continue
        if pure.suffix.lower() not in _ALLOWED_EXTENSIONS:
            continue
        return candidate
    return None
