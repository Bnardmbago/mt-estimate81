from app.ai.prompts import build_rate_card_user_prompt


def test_rate_card_user_prompt_includes_extraction_context():
    prompt = build_rate_card_user_prompt(
        project_name="Portal",
        client_name="ACME",
        form_data={"data_complexity": "high"},
        document_texts=["Requirements doc"],
        feature_items=[{"name": "Login", "hours": 16, "phase": "development", "role": "developer"}],
        extracted_data={
            "functional_requirements": ["User login"],
            "non_functional_requirements": ["SSO"],
            "external_systems": ["Okta"],
        },
        complexity_profile={
            "level": "medium",
            "overall_score": 48,
            "phase_guidance": {"development": 0.4},
        },
    )

    assert "## Extracted Requirements Summary" in prompt
    assert "## Feature Items Summary" in prompt
    assert "## Complexity Analysis" in prompt
    assert "Login" in prompt
    assert "SSO" in prompt
