"""
generate_cache.py

Pre-computes the full "rankings + ideal IVs" result for every league/category
combo and writes each to its own JSON file under precomputed/.

Performance notes:
  - gamemaster.json is fetched and parsed ONCE for the whole run, then shared
    across all 18 league/category combos (previously re-fetched/re-parsed
    per combo).
  - best_iv_for_cap() is memoized (see iv_calculator.py) -- since categories
    within the same league share a CP cap, and the same species show up
    across multiple categories, most IV calculations are cache hits rather
    than being recomputed from scratch.
  Together these cut a full 18-combo run from ~254s to ~55s in testing.

  - Freshness check: if every precomputed/*.json file already exists and is
    newer than CACHE_FRESHNESS_TTL, generate_all() skips the expensive
    regeneration entirely. This matters because `systemctl restart` on the
    cache service re-runs this script's ExecStart unconditionally -- without
    this check, every app deploy that restarts the service pays the full
    ~55s regeneration cost even if the underlying rankings haven't changed
    since the last run. Pass --force to bypass this and regenerate anyway.

Usage:
    python generate_cache.py
    python generate_cache.py --force
"""

import json
import sys
import time
from pathlib import Path

from build_pokemon_list import build_list
from pvpoke_data import LEAGUE_CP_CAPS, fetch_gamemaster, build_species_lookup

CATEGORIES = ["overall", "leads", "closers", "attackers", "switches", "chargers"]
MAX_N = 100

OUTPUT_DIR = Path(__file__).parent / "precomputed"
OUTPUT_DIR.mkdir(exist_ok=True)

# Matches pvpoke_data.RANKINGS_TTL -- no point regenerating IVs faster than
# the underlying rankings data itself can actually change. Also lines up
# with the systemd timer's 6h interval, so a timer-triggered run will always
# find the cache stale and regenerate, while a deploy-triggered restart
# in between timer firings will usually find it fresh and skip.
CACHE_FRESHNESS_TTL = 60 * 60 * 6


def _cache_is_fresh() -> bool:
    """True if every expected precomputed file exists and is still within TTL."""
    now = time.time()
    for league in LEAGUE_CP_CAPS:
        for category in CATEGORIES:
            path = OUTPUT_DIR / f"{league}_{category}.json"
            if not path.exists():
                return False
            if (now - path.stat().st_mtime) >= CACHE_FRESHNESS_TTL:
                return False
    return True


def generate_all(force: bool = False):
    if not force and _cache_is_fresh():
        print(f"Precomputed cache is still fresh (< {CACHE_FRESHNESS_TTL}s old) -- skipping regeneration.")
        print("Pass --force to regenerate anyway.")
        return

    start = time.time()
    successes, failures = [], []

    print("Fetching gamemaster (once for this whole run)...")
    gamemaster = fetch_gamemaster()
    species_lookup = build_species_lookup(gamemaster)
    print(f"  loaded {len(species_lookup)} species\n")

    for league in LEAGUE_CP_CAPS:
        for category in CATEGORIES:
            label = f"{league}_{category}"
            try:
                data = build_list(league, category, MAX_N, species_lookup=species_lookup)
                out_path = OUTPUT_DIR / f"{label}.json"

                tmp_path = out_path.with_suffix(".tmp")
                with open(tmp_path, "w") as f:
                    json.dump(data, f)
                tmp_path.rename(out_path)

                successes.append(label)
                print(f"  ok   {label} ({len(data)} pokemon)")
            except Exception as e:
                failures.append(label)
                print(f"  FAIL {label}: {e}")

    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f}s -- {len(successes)} ok, {len(failures)} failed")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    force = "--force" in sys.argv
    generate_all(force=force)
