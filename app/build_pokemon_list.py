"""
build_pokemon_list.py

Combines pvpoke_data.py (rankings + base stats) and iv_calculator.py (ideal IVs)
to produce the final "top N Pokemon + ideal IVs" list for a league.

Usage:
    python build_pokemon_list.py
"""

import re

from pvpoke_data import get_top_n, fetch_gamemaster, build_species_lookup, LEAGUE_CP_CAPS
from iv_calculator import best_iv_for_cap
from type_colors import row_style

# Strips a trailing parenthetical form/variant tag, e.g.
# "Mimikyu (Busted)" -> "Mimikyu", "Altaria (Shadow)" -> "Altaria"
_FORM_SUFFIX_RE = re.compile(r"\s*\([^)]*\)")


def clean_search_name(species_name: str) -> str:
    """Base species name, lowercased, with any (Shadow)/(Busted)/etc. tag stripped."""
    return _FORM_SUFFIX_RE.sub("", species_name).strip().lower()


def build_list(league: str = "great", category: str = "overall", n: int = 100,
                species_lookup: dict | None = None) -> list[dict]:
    cp_cap = LEAGUE_CP_CAPS[league]

    rankings = get_top_n(league, category, n)

    if species_lookup is None:
        gamemaster = fetch_gamemaster()
        species_lookup = build_species_lookup(gamemaster)

    results = []
    for rank, mon in enumerate(rankings, start=1):
        species = species_lookup.get(mon["speciesId"])
        if species is None:
            continue  # e.g. a form not present in gamemaster

        base = species["baseStats"]
        ideal = best_iv_for_cap(base["atk"], base["def"], base["hp"], cp_cap)
        types = [t for t in species.get("types", []) if t != "none"]
        style = row_style(types)

        results.append({
            "rank": rank,
            "speciesId": mon["speciesId"],
            "name": mon["speciesName"],
            "search_name": clean_search_name(mon["speciesName"]),
            "score": mon["score"],
            "types": types,
            "row_background": style["background"],
            "row_text_color": style["color"],
            "ideal_iv": f"{ideal['atk']}/{ideal['def']}/{ideal['hp']}",
            "ideal_atk_iv": ideal["atk"],
            "ideal_def_iv": ideal["def"],
            "ideal_hp_iv": ideal["hp"],
            "ideal_level": ideal["level"],
            "cp_at_ideal": ideal["cp"],
        })

    return results


def build_low_atk_list(pokemon_list: list[dict]) -> list[str]:
    """
    Search names for Pokemon whose ideal spread has low attack (IV 0-5) with
    strong bulk (def/hp IV >= 10) -- the classic tanky PVP spread.
    """
    return [
        p["search_name"] for p in pokemon_list
        if p["ideal_atk_iv"] in range(0, 6)
        and p["ideal_def_iv"] >= 10
        and p["ideal_hp_iv"] >= 10
    ]


def build_high_atk_list(pokemon_list: list[dict]) -> list[str]:
    """
    Search names for Pokemon whose ideal spread has high attack (IV >= 10)
    alongside strong bulk (def/hp IV >= 10) -- a rarer, near-perfect spread.
    """
    return [
        p["search_name"] for p in pokemon_list
        if p["ideal_atk_iv"] >= 10
        and p["ideal_def_iv"] >= 10
        and p["ideal_hp_iv"] >= 10
    ]


if __name__ == "__main__":
    top_pokemon = build_list("great", "overall", 10)
    for mon in top_pokemon:
        print(f"{mon['rank']:>3}. {mon['name']:<28} search_name={mon['search_name']}")
  