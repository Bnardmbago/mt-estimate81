from app.models.estimate import EstimateStatus


def test_estimate_status_values():
    assert EstimateStatus.DRAFT.value == "draft"
    assert EstimateStatus.COMPLETED.value == "completed"
