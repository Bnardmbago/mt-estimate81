from app.calculation.line_items import build_nrc_line_items


def test_qa_role_labor_folds_into_development_for_quotation():
    line_items = build_nrc_line_items(
        role_breakdown=[
            {"role": "Full Stack Engineer", "cost_jpy": 100_000},
            {"role": "QA Specialist", "cost_jpy": 50_000},
            {"role": "Tech Lead", "cost_jpy": 25_000},
        ],
        setup_items=[{"name": "Infrastructure Setup", "amount_jpy": 200_000}],
        contingency_jpy=10_000,
        overhead_jpy=5_000,
    )
    by_item = {row["item"]: row["cost_jpy"] for row in line_items}

    assert "QA" not in by_item
    assert by_item["Development"] == 175_000
    assert by_item["Infrastructure Setup"] == 200_000
