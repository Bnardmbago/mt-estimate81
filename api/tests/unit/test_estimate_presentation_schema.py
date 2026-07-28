from app.models.estimate import Estimate
from app.schemas.estimate import EstimateDetail, EstimateUpdate
from app.schemas.export import ExportRequest


def test_estimate_model_exposes_presentation_columns() -> None:
    columns = Estimate.__table__.columns

    assert columns["theme_id"].nullable is True
    assert columns["style_id"].nullable is True
    assert columns["template_id"].nullable is True
    assert columns["cover_values"].nullable is False


def test_estimate_update_accepts_presentation_values() -> None:
    body = EstimateUpdate.model_validate(
        {
            "theme_id": "brand-theme",
            "style_id": "dense",
            "template_id": "landscape-cover",
            "cover_values": {"subtitle": {"_i18n": {"en": {"value": "Estimate"}}}},
        }
    )

    assert body.theme_id == "brand-theme"
    assert body.style_id == "dense"
    assert body.template_id == "landscape-cover"
    assert body.cover_values["subtitle"]["_i18n"]["en"]["value"] == "Estimate"


def test_estimate_detail_defaults_cover_values() -> None:
    assert EstimateDetail.model_fields["theme_id"].default is None
    assert EstimateDetail.model_fields["style_id"].default is None
    assert EstimateDetail.model_fields["template_id"].default is None
    assert EstimateDetail.model_fields["cover_values"].default_factory() == {}


def test_export_request_accepts_presentation_overrides() -> None:
    body = ExportRequest.model_validate(
        {
            "format": "pdf",
            "locale": "en",
            "theme_id": "brand-theme",
            "style_id": "dense",
            "template_id": "landscape-cover",
            "include_cover": True,
            "cover_values": {"subtitle": "Estimate"},
        }
    )

    assert body.theme_id == "brand-theme"
    assert body.style_id == "dense"
    assert body.template_id == "landscape-cover"
    assert body.include_cover is True
    assert body.cover_values == {"subtitle": "Estimate"}
