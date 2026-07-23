"""Unit tests for proposal DOCX/XLSX content parity with the PDF pack."""

from __future__ import annotations

from io import BytesIO

from docx import Document
from openpyxl import load_workbook

from app.proposals.export_formats import generate_proposal_docx, generate_proposal_xlsx
from app.proposals.svg_raster import svg_to_png_bytes


def _sample_ctx(**overrides):
    ctx = {
        "labels": {
            "title": "Project Proposal Pack",
            "toc": "Table of Contents",
            "assessment": "Project Assessment",
            "proposal": "Project Proposal",
            "poc": "Proof of Concept",
            "one_time": "One-time project cost",
            "monthly": "Monthly recurring cost",
            "first_year": "First-year total",
            "timeline": "Project timeline",
            "milestones": "Milestones",
            "project_brief": "Project brief",
            "brief_project_name": "Project name",
            "brief_description": "Project description",
            "brief_business_problem": "Business problem",
            "brief_target_users": "Target users",
            "brief_technology_stack": "Technology stack",
            "brief_constraints": "Constraints",
            "poc_tables": "Tables",
            "poc_diagrams": "Illustrations",
            "poc_milestones": "Proof of Concept milestones",
            "official_poc_cost": "Official Proof of Concept cost",
            "suggested_window": "Suggested validation window",
            "effort_hours": "Estimated effort (hours)",
        },
        "locale": "en",
        "variant": "full",
        "project_name": "Portal Redesign",
        "client_name": "ACME Corp",
        "toc": [
            {"id": "assessment", "title": "Project Assessment", "level": "1"},
            {"id": "proposal", "title": "Project Proposal", "level": "1"},
        ],
        "assessment": {
            "sections": [
                {
                    "id": "overview",
                    "title": "Assessment Overview",
                    "body": "Assessment body text",
                    "bullets": ["Risk A"],
                    "rating": "high",
                }
            ]
        },
        "proposal_body": {
            "sections": [
                {
                    "id": "approach",
                    "title": "Delivery Approach",
                    "body": "We will deliver in phases.",
                    "bullets": ["Phase 1", "Phase 2"],
                }
            ]
        },
        "poc": {
            "project_brief": {
                "project_name": "Portal Redesign",
                "project_description": "Modernize the portal",
                "business_problem": "Legacy UX",
                "target_users": "Employees",
                "technology_stack": "Next.js",
                "constraints": "8 weeks",
            },
            "sections": [
                {
                    "id": "scope",
                    "title": "PoC Scope",
                    "body": "Validate authentication",
                    "bullets": ["SSO"],
                }
            ],
            "tables": [
                {
                    "title": "Effort table",
                    "headers": ["Role", "Hours"],
                    "rows": [["Developer", "40"]],
                }
            ],
            "diagrams": [
                {
                    "title": "PoC Flow",
                    "source": "flowchart LR\n  A --> B",
                }
            ],
            "milestones": [{"name": "PoC kickoff", "date": "2026-09-01"}],
            "official": {
                "total_effort_hours": 80,
                "estimated_one_time_cost_jpy": 800000,
            },
            "suggested_validation_window": "4–6 weeks",
        },
        "diagrams": [
            {
                "title": "Architecture Overview",
                "source": "graph TD\n  Client --> API",
            }
        ],
        "milestones": [{"name": "Go-live", "date": "2026-12-01"}],
        "cost_summary": {
            "one_time_project_cost_jpy": 5000000,
            "monthly_recurring_cost_jpy": 200000,
            "first_year_total_jpy": 7400000,
        },
        "gantt": {
            "project_start_date": "2026-08-01",
            "tasks": [
                {
                    "name": "Design UI",
                    "phase": "design",
                    "start_date": "2026-08-01",
                    "end_date": "2026-08-10",
                    "duration_working_days": 7,
                    "hours": 40,
                }
            ],
            "phases": [],
        },
        "gantt_svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="40">'
            '<rect width="100" height="40" fill="#1E3A5F"/>'
            "</svg>"
        ),
        "include_poc": True,
        "theme": {"primary": "1E3A5F"},
    }
    ctx.update(overrides)
    return ctx


def _docx_text(content: bytes) -> str:
    document = Document(BytesIO(content))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    return "\n".join(parts)


def test_proposal_docx_nonempty_and_contains_pack_content():
    content = generate_proposal_docx(_sample_ctx())
    assert content[:2] == b"PK"
    assert len(content) > 1000
    text = _docx_text(content)
    assert "Portal Redesign" in text
    assert "Assessment Overview" in text
    assert "Delivery Approach" in text
    assert "PoC Scope" in text
    assert "Architecture Overview" in text
    assert "graph TD" in text
    assert "Client --> API" in text
    assert "Effort table" in text
    assert "Developer" in text
    assert "Go-live" in text
    assert "Modernize the portal" in text


def test_proposal_docx_embeds_gantt_picture_when_svg_present():
    # Prefer real cairosvg rasterization when available in the test environment.
    png = svg_to_png_bytes(_sample_ctx()["gantt_svg"])
    if png is None:
        # Environment without Cairo — skip visual embed assertion.
        return
    content = generate_proposal_docx(_sample_ctx())
    document = Document(BytesIO(content))
    assert document.inline_shapes
    text = _docx_text(content)
    assert "Project timeline" in text


def test_proposal_docx_skips_gantt_picture_when_raster_fails(monkeypatch):
    monkeypatch.setattr(
        "app.proposals.export_formats.svg_to_png_bytes",
        lambda _svg, **_kwargs: None,
    )
    content = generate_proposal_docx(_sample_ctx())
    document = Document(BytesIO(content))
    assert len(document.inline_shapes) == 0


def test_proposal_xlsx_sheets_and_content():
    content = generate_proposal_xlsx(_sample_ctx())
    assert content[:2] == b"PK"
    wb = load_workbook(BytesIO(content))
    assert "Summary" in wb.sheetnames
    assert "Assessment" in wb.sheetnames
    assert "Proposal" in wb.sheetnames
    assert "PoC" in wb.sheetnames
    assert "PoC Tables" in wb.sheetnames
    assert "Diagrams" in wb.sheetnames
    assert "Timeline" in wb.sheetnames
    assert "Milestones" in wb.sheetnames

    summary = wb["Summary"]
    assert summary["B1"].value == "Value" or summary["A2"].value == "Project"
    assert any(cell.value == "Portal Redesign" for row in summary.iter_rows() for cell in row)

    assessment = wb["Assessment"]
    assert any(cell.value == "Assessment Overview" for row in assessment.iter_rows() for cell in row)

    timeline = wb["Timeline"]
    assert any(cell.value == "Design UI" for row in timeline.iter_rows() for cell in row)

    diagrams = wb["Diagrams"]
    values = [cell.value for row in diagrams.iter_rows() for cell in row]
    assert "Architecture Overview" in values
    assert any(isinstance(v, str) and "graph TD" in v for v in values)
    assert "PoC Flow" in values


def test_proposal_xlsx_project_name_override_reflected():
    content = generate_proposal_xlsx(_sample_ctx(project_name="Custom Export Name"))
    wb = load_workbook(BytesIO(content))
    summary = wb["Summary"]
    assert any(
        cell.value == "Custom Export Name" for row in summary.iter_rows() for cell in row
    )


def test_svg_to_png_bytes_empty_returns_none():
    assert svg_to_png_bytes("") is None
    assert svg_to_png_bytes("   ") is None


def test_svg_to_png_bytes_invalid_returns_none():
    assert svg_to_png_bytes("<not-valid-svg") is None


def test_docx_embeds_diagram_png_when_svg_present():
    ctx = _sample_ctx()
    # Minimal valid 1x1 PNG
    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00"
        b"\x00\x03\x00\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    # Use a known-good tiny PNG from cairosvg of a simple SVG instead if needed
    from app.proposals.svg_raster import svg_to_png_bytes

    rendered = svg_to_png_bytes(
        '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="40">'
        '<rect width="80" height="40" fill="#1E3A5F"/></svg>'
    )
    assert rendered
    import base64

    ctx["diagrams"] = [
        {
            "title": "Architecture Overview",
            "source": "graph TD\n  Client --> API",
            "png_base64": base64.b64encode(rendered).decode("ascii"),
        }
    ]
    content = generate_proposal_docx(ctx)
    document = Document(BytesIO(content))
    assert document.inline_shapes
    text = _docx_text(content)
    assert "Architecture Overview" in text
    assert "graph TD" not in text


def test_enrich_diagrams_copies_existing_svg(monkeypatch):
    from app.proposals.mermaid_render import enrich_diagrams_with_svg

    called = {"n": 0}

    def boom(_source: str):
        called["n"] += 1
        return b"\x89PNG\r\n\x1a\n"

    monkeypatch.setattr("app.proposals.mermaid_render.render_mermaid_png", boom)
    out = enrich_diagrams_with_svg(
        [{"title": "A", "source": "graph TD; A-->B", "png_base64": "already"}]
    )
    assert out[0]["png_base64"] == "already"
    assert called["n"] == 0
