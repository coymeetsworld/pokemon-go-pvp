"""
build_pokemon_list.py

Combines pvpoke_data.py (rankings + base stats) and iv_calculator.py (ideal IVs)
to produce the final "top N Pokemon + ideal IVs" list for a league.

Usage:
    python build_pokemon_list.py
"""

import json

from pvpoke_data import get_top_n, fetch_gamemaster, build_species_lookup, LEAGUE_CP_CAPS
from iv_calculator import best_iv_for_cap
from type_colors import row_style


def build_list(league: str = "great", category: str = "overall", n: int = 100) -> list[dict]:
    cp_cap = LEAGUE_CP_CAPS[league]

    rankings = get_top_n(league, category, n)
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
            "score": mon["score"],
            "types": types,
            "row_background": style["background"],
            "row_text_color": style["color"],
            "ideal_iv": f"{ideal['atk']}/{ideal['def']}/{ideal['hp']}",
            "ideal_level": ideal["level"],
            "cp_at_ideal": ideal["cp"],
        })

    return results


if __name__ == "__main__":
    top_pokemon = build_list("great", "overall", 100)

    for mon in top_pokemon[:10]:
        print(f"{mon['rank']:>3}. {mon['name']:<28} "
              f"score={mon['score']:<6} ideal IV={mon['ideal_iv']:<8} "
              f"(L{mon['ideal_level']}, CP{mon['cp_at_ideal']})")

    with open("top_100_great_league.json", "w") as f:
        json.dump(top_pokemon, f, indent=2)
    print("\nSaved full list to top_100_great_league.json")
