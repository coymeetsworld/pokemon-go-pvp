"""
generate_cache.py

Pre-computes the full "rankings + ideal IVs" result for every league/category
combo and writes each to its own JSON file under precomputed/.

This is meant to run on a schedule (systemd timer / cron), NOT per web request.
app.py then just reads these files directly -- no computation happens while
a user is waiting on a response.

Usage:
    python generate_cache.py
"""

import json
import time
from pathlib import Path

from build_pokemon_list import build_list
from pvpoke_data import LEAGUE_CP_CAPS

CATEGORIES = ["overall", "leads", "closers", "attackers", "switches", "chargers"]
MAX_N = 100  # generate the deepest list any request could ask for; app.py slices down from this

OUTPUT_DIR = Path(__file__).parent / "precomputed"
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_all():
    start = time.time()
    successes, failures = [], []

    for league in LEAGUE_CP_CAPS:
        for category in CATEGORIES:
            label = f"{league}_{category}"
            try:
                data = build_list(league, category, MAX_N)
                out_path = OUTPUT_DIR / f"{label}.json"

                # Write to a temp file then rename -- atomic on POSIX, so app.py
                # never reads a half-written file mid-update.
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
        # Non-zero exit so systemd/cron can flag a failed run (e.g. for alerting).
        raise SystemExit(1)


if __name__ == "__main__":
    generate_all()
