"""Unit tests for Mermaid → PNG export rendering helper."""

from __future__ import annotations

import base64

from app.proposals.export_service import _enrich_diagrams_for_visual_export
from app.proposals.mermaid_render import (
    enrich_diagrams_with_svg,
    normalize_mermaid_for_portrait,
    render_mermaid_png,
)


SAMPLE_FLOW = """graph TD;
  A[ユーザーインターフェース] --> B[モバイルアプリ];
  B --> C[クラウドAIサービス];
"""


def test_normalize_mermaid_for_portrait_converts_lr_to_td():
    src = """flowchart LR
  A[開始] --> B[要件定義]
  B --> C[完了]
"""
    out = normalize_mermaid_for_portrait(src)
    assert out.startswith("flowchart TD")
    assert "flowchart LR" not in out
    assert "開始" in out


def test_normalize_mermaid_for_portrait_direction_statement():
    src = """flowchart
  direction RL
  A --> B
"""
    out = normalize_mermaid_for_portrait(src)
    assert "direction TD" in out
    assert "direction RL" not in out


def test_normalize_mermaid_keeps_existing_td():
    src = "graph TD\n  A --> B\n"
    assert normalize_mermaid_for_portrait(src) == src.strip()


def test_render_mermaid_png_empty_returns_none():
    assert render_mermaid_png("") is None
    assert render_mermaid_png("   ") is None


def test_enrich_diagrams_with_png_invokes_renderer(monkeypatch):
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

    monkeypatch.setattr(
        "app.proposals.mermaid_render.render_mermaid_png",
        lambda source: fake_png,
    )
    out = enrich_diagrams_with_svg([{"title": "提案されたアーキテクチャ", "source": SAMPLE_FLOW}])
    assert out[0]["title"] == "提案されたアーキテクチャ"
    assert out[0]["png_base64"] == base64.b64encode(fake_png).decode("ascii")


def test_visual_export_enrichment_covers_top_and_poc(monkeypatch):
    fake_png = b"\x89PNG\r\n\x1a\n" + b"abc"
    monkeypatch.setattr(
        "app.proposals.mermaid_render.render_mermaid_png",
        lambda source: fake_png,
    )
    ctx = {
        "diagrams": [{"title": "Top", "source": "graph TD; A-->B"}],
        "poc": {
            "diagrams": [{"title": "PoC", "source": "flowchart LR; X-->Y"}],
            "sections": [],
        },
    }
    enriched = _enrich_diagrams_for_visual_export(ctx)
    assert enriched["diagrams"][0]["png_base64"]
    assert enriched["poc"]["diagrams"][0]["png_base64"]
    assert "png_base64" not in ctx["diagrams"][0]


def test_enrich_skips_render_when_png_already_present(monkeypatch):
    called = {"n": 0}

    def boom(_source: str) -> bytes | None:
        called["n"] += 1
        return b"\x89PNG\r\n\x1a\n"

    monkeypatch.setattr("app.proposals.mermaid_render.render_mermaid_png", boom)
    out = enrich_diagrams_with_svg(
        [{"title": "A", "source": "graph TD; A-->B", "png_base64": "keep"}]
    )
    assert out[0]["png_base64"] == "keep"
    assert called["n"] == 0


def test_render_mermaid_png_integration_when_node_available():
    """Exercise real mermaid-cli when Node/Chromium are present (Docker api image)."""
    png = render_mermaid_png(SAMPLE_FLOW)
    if png is None:
        return
    assert png.startswith(b"\x89PNG")
    assert len(png) > 1000
    from io import BytesIO

    from PIL import Image

    image = Image.open(BytesIO(png))
    # Compact export: not a full-page poster.
    assert image.width <= 720
    assert image.height <= 900


def test_trim_and_fit_png_crops_whitespace():
    from io import BytesIO

    from PIL import Image

    from app.proposals.mermaid_render import _trim_and_fit_png

    canvas = Image.new("RGB", (400, 600), (255, 255, 255))
    for x in range(40, 120):
        for y in range(50, 90):
            canvas.putpixel((x, y), (30, 30, 30))
    buf = BytesIO()
    canvas.save(buf, format="PNG")
    trimmed = _trim_and_fit_png(buf.getvalue())
    out = Image.open(BytesIO(trimmed))
    assert out.width < 400
    assert out.height < 600
