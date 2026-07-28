from app.presentation.background_style import cover_background_inline_css


def test_cover_background_inline_css_includes_horizontal_anchor():
    css = cover_background_inline_css({"x": 15, "y": 50, "zoom": 1, "fit": "cover"})
    assert "left:15%" in css
    assert "transform:translate(-15%, -50%)" in css
    assert "min-width:100%" in css
    assert "min-height:100%" in css


def test_cover_background_inline_css_zoom_enables_dual_axis_pan_room():
    css = cover_background_inline_css({"x": 85, "y": 20, "zoom": 1.5, "opacity": 0.75})
    assert "left:85%" in css
    assert "top:20%" in css
    assert "transform:translate(-85%, -20%)" in css
    assert "min-width:150%" in css
    assert "min-height:150%" in css
    assert "opacity:0.75" in css


def test_cover_background_inline_css_fill_and_contain():
    fill = cover_background_inline_css({"x": 0, "y": 100, "zoom": 1.25, "fit": "fill"})
    assert "left:0%" in fill
    assert "width:125%" in fill
    assert "height:125%" in fill
    assert "transform:translate(0%, -100%)" in fill

    contain = cover_background_inline_css({"x": 10, "y": 90, "zoom": 2, "fit": "contain"})
    assert "max-width:200%" in contain
    assert "max-height:200%" in contain
    assert "transform:translate(-10%, -90%)" in contain
