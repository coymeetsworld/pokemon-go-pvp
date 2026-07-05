"""
app.py

Flask web app for browsing top PvP Pokemon rankings with their ideal IVs.

Routes:
    GET /                -> HTML table (league/category/count selectable via query params)
    GET /api/rankings     -> same data as JSON

Run:
    python app.py
    then open http://127.0.0.1:5000
"""

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

from pvpoke_data import LEAGUE_CP_CAPS
from build_pokemon_list import build_list, build_low_atk_list, build_high_atk_list

app = Flask(__name__)

CATEGORIES = ["overall", "leads", "closers", "attackers", "switches", "chargers"]


def _parse_query_args():
    league = request.args.get("league", "great")
    category = request.args.get("category", "overall")
    n = request.args.get("n", 100, type=int)

    if league not in LEAGUE_CP_CAPS:
        league = "great"
    if category not in CATEGORIES:
        category = "overall"
    n = max(1, min(n, 500))

    return league, category, n


@app.route("/")
def index():
    league, category, n = _parse_query_args()
    pokemon = build_list(league, category, n)
    low_atk_list = build_low_atk_list(pokemon)
    high_atk_list = build_high_atk_list(pokemon)

    return render_template(
        "index.html",
        pokemon=pokemon,
        low_atk_list=low_atk_list,
        high_atk_list=high_atk_list,
        league=league,
        category=category,
        n=n,
        leagues=LEAGUE_CP_CAPS.keys(),
        categories=CATEGORIES,
    )


@app.route("/api/rankings")
def api_rankings():
    league, category, n = _parse_query_args()
    pokemon = build_list(league, category, n)
    return jsonify(pokemon)


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)
