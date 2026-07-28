from app.presentation.asset_paths import (
    draft_asset_path,
    draft_prefixes_for,
    find_asset_under_prefixes,
    is_presentation_asset_path,
    promote_destination,
    template_asset_path,
)


def test_asset_paths_live_under_uploads_volume_prefix():
    assert draft_asset_path("d1", "a1", ".png") == "uploads/presentation-drafts/d1/a1.png"
    assert template_asset_path("t1", "a1", ".webp") == "uploads/presentation-assets/t1/a1.webp"
    assert promote_destination("t1", "a1.png") == "uploads/presentation-assets/t1/a1.png"


def test_legacy_and_current_prefixes_are_recognized():
    assert is_presentation_asset_path("uploads/presentation-drafts/d/a.png")
    assert is_presentation_asset_path("presentation-assets/t/a.png")
    assert not is_presentation_asset_path("uploads/other/a.png")
    assert draft_prefixes_for("d1") == (
        "uploads/presentation-drafts/d1",
        "presentation-drafts/d1",
    )


def test_find_asset_matches_stem_under_prefix_only():
    asset_id = "11111111-1111-1111-1111-111111111111"
    found = find_asset_under_prefixes(
        [
            f"uploads/presentation-drafts/other/{asset_id}.png",
            f"uploads/presentation-drafts/d1/{asset_id}.png",
        ],
        prefixes=("uploads/presentation-drafts/d1", "presentation-drafts/d1"),
        asset_id=asset_id,
    )
    assert found == f"uploads/presentation-drafts/d1/{asset_id}.png"
