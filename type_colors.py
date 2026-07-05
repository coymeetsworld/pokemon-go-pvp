"""
type_colors.py

Reads colors from static/pokemontypes.css (the app's existing type stylesheet)
instead of hardcoding a separate palette, so that file is the single source
of truth for type colors.

Expects rules shaped like:
    .fire {
      background-color: rgb(240, 128, 48);
      color: #000;
    }

We parse out {type: {"bg": "rgb(...)", "text": "#..."}} once, cache it, and
use it to build:
  - a flat background for single-type Pokemon
  - a hard-stop diagonal gradient (two triangles, no bleed) for dual-type Pokemon
"""

import re
from pathlib import Path
from functools import lru_cache

CSS_PATH = Path(__file__).parent / "static" / "pokemontypes.css"

DEFAULT_BG = "#CCCCCC"
DEFAULT_TEXT = "#000"

# Matches ".typename { ...block... }" and captures the block contents
_RULE_RE = re.compile(r"\.([a-zA-Z0-9_-]+)\s*\{([^}]*)\}")
_BG_RE = re.compile(r"background-color:\s*([^;]+);")
_COLOR_RE = re.compile(r"(?<!background-)color:\s*([^;]+);")


@lru_cache(maxsize=1)
def _load_type_styles() -> dict[str, dict[str, str]]:
    """Parse static/pokemontypes.css into {type: {"bg": ..., "text": ...}}."""
    css = CSS_PATH.read_text()
    styles = {}

    for match in _RULE_RE.finditer(css):
        type_name, block = match.group(1), match.group(2)
        bg_match = _BG_RE.search(block)
        color_match = _COLOR_RE.search(block)

        styles[type_name] = {
            "bg": bg_match.group(1).strip() if bg_match else DEFAULT_BG,
            "text": color_match.group(1).strip() if color_match else DEFAULT_TEXT,
        }

    return styles


def row_style(types: list[str], angle: int = 135) -> dict[str, str]:
    """
    Build inline CSS for a table row based on 1-2 Pokemon types, using colors
    parsed from pokemontypes.css.

    Returns {"background": <css value>, "color": <text color>}.
    """
    styles = _load_type_styles()
    entries = [styles.get(t, {"bg": DEFAULT_BG, "text": DEFAULT_TEXT}) for t in types]

    if not entries:
        return {"background": DEFAULT_BG, "color": DEFAULT_TEXT}

    if len(entries) == 1:
        return {"background": entries[0]["bg"], "color": entries[0]["text"]}

    # Hard stop: both color-stops at 50% -> sharp diagonal edge, no blending.
    background = f"linear-gradient({angle}deg, {entries[0]['bg']} 50%, {entries[1]['bg']} 50%)"
    # Use the primary type's text color for contrast; good enough for most pairs.
    return {"background": background, "color": entries[0]["text"]}
