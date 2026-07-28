from app.models.presentation_draft import PresentationPresetDraft
from app.presentation.seeds import CLASSIC_LINEAR_TEMPLATE


def test_seed_template_has_page_and_cover_defaults():
    assert CLASSIC_LINEAR_TEMPLATE["page"] == {"size": "A4", "orientation": "portrait"}
    assert "cover_fields" in CLASSIC_LINEAR_TEMPLATE
    assert "cover_design" in CLASSIC_LINEAR_TEMPLATE


def test_draft_model_tablename():
    assert PresentationPresetDraft.__tablename__ == "presentation_preset_drafts"
