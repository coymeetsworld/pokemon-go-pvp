"""
Tests for type_colors.py

row_style() reads static/pokemontypes.css as its source of truth (see the
module docstring for why), so these tests run against the real file rather
than mocking it -- the whole point is confirming the parser correctly
extracts what's actually in that file.
"""

from type_colors import row_style, _load_type_styles


class TestLoadTypeStyles:
    def test_parses_known_type(self):
        styles = _load_type_styles()
        assert styles["fire"]["bg"] == "rgb(240, 128, 48)"
        assert styles["fire"]["text"] == "#000"

    def test_parses_white_text_type(self):
        styles = _load_type_styles()
        assert styles["ghost"]["text"] == "#fff"

    def test_all_eighteen_types_present(self):
        styles = _load_type_styles()
        expected = {
            "normal", "fire", "water", "grass", "electric", "ice", "fighting",
            "poison", "ground", "flying", "psychic", "bug", "rock", "ghost",
            "dragon", "dark", "steel", "fairy",
        }
        assert expected.issubset(styles.keys())


class TestRowStyle:
    def test_single_type_flat_background(self):
        style = row_style(["fire"])
        assert style["background"] == "rgb(240, 128, 48)"
        assert style["color"] == "#000"

    def test_dual_type_hard_stop_gradient(self):
        """Both color stops must sit at the same 50% mark -- that's what
        makes it a hard diagonal split rather than a blended gradient."""
        style = row_style(["ghost", "fairy"])
        assert style["background"] == (
            "linear-gradient(135deg, rgb(112, 88, 152) 50%, rgb(242, 162, 231) 50%)"
        )
        assert "50%, rgb" in style["background"]

    def test_dual_type_uses_primary_type_text_color(self):
        style = row_style(["ghost", "fairy"])
        assert style["color"] == "#fff"  # ghost's text color, per the "primary type wins" rule

    def test_no_types_falls_back_to_default(self):
        style = row_style([])
        assert style["background"] == "#CCCCCC"
        assert style["color"] == "#000"

    def test_unknown_type_falls_back_to_default(self):
        style = row_style(["not-a-real-type"])
        assert style["background"] == "#CCCCCC"

    def test_custom_gradient_angle(self):
        style = row_style(["fire", "water"], angle=90)
        assert style["background"].startswith("linear-gradient(90deg,")
