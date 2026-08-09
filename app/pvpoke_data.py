"""
pvpoke_data.py

Fetches Pokemon GO PvP data directly from PvPoke's public JSON files.

Two files matter:
  - rankings-<cp>.json   -> ranked list of Pokemon for a given CP cap/league
  - gamemaster.json       -> base stats, types, moves for every Pokemon

Both are mirrored on GitHub (same repo that powers pvpoke.com), so we pull
from there.

Options:
League: great (1500), ultra (2500), and master (10000)
Category:
  Overall: The best Pokemon overall across multiple roles. They have the typing, moves, and stats to succeed as top contenders.
  Leads: The best Pokemon with shields in play. Capable of applying pressure or winning extended fights, they're ideal leads in battle.
  Closers: The best Pokemon with no shields in play. Bulk or hard-hitting moves allow them to close out matchups.
  Switches: The best Pokemon to switch to from an unfavorable lead. These Pokemon have safe matchups and can pressure shields or deal heavy damage even in their losses.
  Chargers: The best Pokemon with an energy advantage. Fast energy gain or powerful moves make them dangerous after building up energy. This category also factors in a Pokemon's ability to farm down weakened opponent or overfarm in advantageous matchups.
  Attackers: The best Pokemon against shielded opponents, while unshielded. Their natural bulk, resistances, and strong attacks allow them to power through a disadvantage.
  Consistency: These Pokemon perform the most dependably. They provide consistent damage and rely less on baiting shields than other Pokemon. Shorter Fast Moves also help improve consistency.
    

"""

import json
import time
from pathlib import Path

import requests

BASE_URL = "https://raw.githubusercontent.com/pvpoke/pvpoke/master/src/data"

# PvPoke league -> CP cap used in their rankings file paths
LEAGUE_CP_CAPS = {
    "great": 1500,
    "ultra": 2500,
    "master": 10000,
}

# --- simple on-disk cache -------------------------------------------------
# gamemaster.json is ~5MB and rarely changes, and rankings only change when
# PvPoke re-runs simulations (every so often). No need to hit the network on
# every request -- cache to disk with a TTL instead.
CACHE_DIR = Path(__file__).parent / ".pvpoke_cache"
CACHE_DIR.mkdir(exist_ok=True)

GAMEMASTER_TTL = 60 * 60 * 24  # 24 hours
RANKINGS_TTL = 60 * 60 * 6     # 6 hours


def _cached_get(url: str, cache_key: str, ttl: int) -> dict | list:
    """Fetch JSON from url, using a cached copy on disk if it's still fresh."""
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < ttl:
        with open(cache_file) as f:
            return json.load(f)

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    with open(cache_file, "w") as f:
        json.dump(data, f)

    return data


def fetch_rankings(league: str = "great", category: str = "overall") -> list[dict]:
    """
    Fetch the ranked Pokemon list for a league/category.

    Returns a list of dicts like:
      {"speciesId": "mimikyu", "speciesName": "Mimikyu (Busted)", "rating": 777,
       "score": 95.9, "stats": {"product": 1842, "atk": 121.5, "def": 141.6, "hp": 107}, ...}
    """
    cp_cap = LEAGUE_CP_CAPS[league]
    url = f"{BASE_URL}/rankings/all/{category}/rankings-{cp_cap}.json"
    return _cached_get(url, f"rankings_{league}_{category}", RANKINGS_TTL)


def fetch_gamemaster() -> dict:
    """Fetch the full gamemaster (base stats, types, moves, etc. for every Pokemon)."""
    url = f"{BASE_URL}/gamemaster.json"
    return _cached_get(url, "gamemaster", GAMEMASTER_TTL)


def build_species_lookup(gamemaster: dict) -> dict[str, dict]:
    """Turn gamemaster['pokemon'] into a dict keyed by speciesId for fast lookup."""
    return {p["speciesId"]: p for p in gamemaster["pokemon"]}


def get_top_n(league: str = "great", category: str = "overall", n: int = 100) -> list[dict]:
    """Convenience wrapper: top N ranked Pokemon for a league/category."""
    rankings = fetch_rankings(league, category)
    return rankings[:n]


if __name__ == "__main__":
    top = get_top_n("great", "overall", 5)
    for i, mon in enumerate(top, 1):
        print(f"{i}. {mon['speciesName']} (score {mon['score']})")
