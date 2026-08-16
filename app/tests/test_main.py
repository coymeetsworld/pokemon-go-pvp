"""
Tests for main.py (the Flask app).

Design note: these tests stub out render_template rather than relying on the
real templates/index.html. This deliberately decouples "does the route
compute and pass the right data" (what these tests check) from "does the
template render that data correctly" (a separate concern -- a visual/manual
check, or a future template-specific test if index.html grows logic worth
covering). Testing against a guessed reconstruction of the real template
would risk false confidence either way.
"""

import json

import pytest

import main as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def _make_pokemon(name="testmon", atk_iv=0, def_iv=14, hp_iv=15):
    return {
        "rank": 1,
        "speciesId": name,
        "name": name.capitalize(),
        "search_name": name,
        "score": 90.0,
        "types": ["normal"],
        "row_background": "#A8A878",
        "row_text_color": "#000",
        "ideal_iv": f"{atk_iv}/{def_iv}/{hp_iv}",
        "ideal_atk_iv": atk_iv,
        "ideal_def_iv": def_iv,
        "ideal_hp_iv": hp_iv,
        "ideal_level": 25.5,
        "cp_at_ideal": 1499,
    }


class TestParseQueryArgs:
    def test_defaults_with_no_query_params(self, client):
        with app_module.app.test_request_context("/"):
            league, category, n = app_module._parse_query_args()
        assert (league, category, n) == ("great", "overall", 100)

    def test_valid_params_pass_through(self, client):
        with app_module.app.test_request_context("/?league=ultra&category=leads&n=50"):
            league, category, n = app_module._parse_query_args()
        assert (league, category, n) == ("ultra", "leads", 50)

    def test_invalid_league_falls_back_to_great(self, client):
        with app_module.app.test_request_context("/?league=not-a-real-league"):
            league, category, n = app_module._parse_query_args()
        assert league == "great"

    def test_invalid_category_falls_back_to_overall(self, client):
        with app_module.app.test_request_context("/?category=not-a-real-category"):
            league, category, n = app_module._parse_query_args()
        assert category == "overall"

    def test_n_clamped_to_minimum_one(self, client):
        with app_module.app.test_request_context("/?n=0"):
            _, _, n = app_module._parse_query_args()
        assert n == 1

    def test_n_clamped_to_maximum_500(self, client):
        with app_module.app.test_request_context("/?n=99999"):
            _, _, n = app_module._parse_query_args()
        assert n == 500

    def test_negative_n_clamped_to_one(self, client):
        with app_module.app.test_request_context("/?n=-10"):
            _, _, n = app_module._parse_query_args()
        assert n == 1


class TestGetPokemon:
    def test_reads_from_precomputed_cache_when_present(self, tmp_path, monkeypatch):
        monkeypatch.setattr(app_module, "PRECOMPUTED_DIR", tmp_path)
        cache_file = tmp_path / "great_overall.json"
        cache_file.write_text(json.dumps([_make_pokemon("a"), _make_pokemon("b"), _make_pokemon("c")]))

        result = app_module.get_pokemon("great", "overall", 2)

        assert len(result) == 2  # respects the n slice
        assert result[0]["search_name"] == "a"

    def test_falls_back_to_live_build_when_cache_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(app_module, "PRECOMPUTED_DIR", tmp_path)  # empty dir, no cache file

        fake_result = [_make_pokemon("fallback-mon")]
        called_with = {}

        def fake_build_list(league, category, n):
            called_with["args"] = (league, category, n)
            return fake_result

        monkeypatch.setattr(app_module, "build_list", fake_build_list)

        result = app_module.get_pokemon("ultra", "leads", 10)

        assert result == fake_result
        assert called_with["args"] == ("ultra", "leads", 10)

    def test_logs_warning_on_cache_miss(self, tmp_path, monkeypatch, caplog):
        monkeypatch.setattr(app_module, "PRECOMPUTED_DIR", tmp_path)
        monkeypatch.setattr(app_module, "build_list", lambda l, c, n: [])

        with caplog.at_level("WARNING"):
            app_module.get_pokemon("great", "overall", 5)

        assert "No precomputed cache" in caplog.text


class TestIndexRoute:
    def test_returns_200(self, client, monkeypatch):
        monkeypatch.setattr(app_module, "get_pokemon", lambda l, c, n: [_make_pokemon()])
        monkeypatch.setattr(app_module, "render_template", lambda *a, **kw: "ok")

        response = client.get("/")
        assert response.status_code == 200

    def test_passes_correct_context_to_template(self, client, monkeypatch):
        sample = [_make_pokemon("mimikyu", atk_iv=1, def_iv=14, hp_iv=15)]
        captured = {}

        def fake_get_pokemon(league, category, n):
            captured["get_pokemon_args"] = (league, category, n)
            return sample

        def fake_render_template(template_name, **context):
            captured["template_name"] = template_name
            captured["context"] = context
            return "rendered"

        monkeypatch.setattr(app_module, "get_pokemon", fake_get_pokemon)
        monkeypatch.setattr(app_module, "render_template", fake_render_template)

        client.get("/?league=ultra&category=attackers&n=25")

        assert captured["get_pokemon_args"] == ("ultra", "attackers", 25)
        assert captured["template_name"] == "index.html"
        assert captured["context"]["pokemon"] == sample
        assert captured["context"]["league"] == "ultra"
        assert captured["context"]["category"] == "attackers"
        assert captured["context"]["n"] == 25
        assert list(captured["context"]["leagues"]) == list(app_module.LEAGUE_CP_CAPS.keys())
        assert captured["context"]["categories"] == app_module.CATEGORIES

    def test_low_and_high_atk_lists_computed_from_pokemon(self, client, monkeypatch):
        low_mon = _make_pokemon("lowmon", atk_iv=0, def_iv=14, hp_iv=15)
        high_mon = _make_pokemon("highmon", atk_iv=12, def_iv=13, hp_iv=14)
        sample = [low_mon, high_mon]
        captured = {}

        monkeypatch.setattr(app_module, "get_pokemon", lambda l, c, n: sample)
        monkeypatch.setattr(
            app_module, "render_template",
            lambda name, **ctx: captured.update(ctx) or "ok",
        )

        client.get("/")

        assert captured["low_atk_list"] == ["lowmon"]
        assert captured["high_atk_list"] == ["highmon"]

    def test_invalid_query_params_are_sanitized_end_to_end(self, client, monkeypatch):
        captured = {}
        monkeypatch.setattr(app_module, "get_pokemon", lambda l, c, n: [])
        monkeypatch.setattr(
            app_module, "render_template",
            lambda name, **ctx: captured.update(ctx) or "ok",
        )

        client.get("/?league=bogus&category=bogus&n=99999")

        assert captured["league"] == "great"
        assert captured["category"] == "overall"
        assert captured["n"] == 500


class TestApiRankingsRoute:
    def test_returns_json_list(self, client, monkeypatch):
        sample = [_make_pokemon("a"), _make_pokemon("b")]
        monkeypatch.setattr(app_module, "get_pokemon", lambda l, c, n: sample)

        response = client.get("/api/rankings")

        assert response.status_code == 200
        assert response.get_json() == sample

    def test_passes_parsed_query_args_to_get_pokemon(self, client, monkeypatch):
        captured = {}

        def fake_get_pokemon(league, category, n):
            captured["args"] = (league, category, n)
            return []

        monkeypatch.setattr(app_module, "get_pokemon", fake_get_pokemon)

        client.get("/api/rankings?league=master&category=closers&n=10")

        assert captured["args"] == ("master", "closers", 10)

    def test_uses_precomputed_cache_via_get_pokemon(self, client, monkeypatch):
        """
        Confirms api_rankings() now goes through get_pokemon() (cache-first,
        same as index()) rather than calling build_list() directly. This was
        previously a live-build-only bypass -- fixed so /api/rankings
        benefits from the precomputed cache like every other route.
        """
        get_pokemon_called = {"value": False}

        def fake_get_pokemon(league, category, n):
            get_pokemon_called["value"] = True
            return []

        monkeypatch.setattr(app_module, "get_pokemon", fake_get_pokemon)

        client.get("/api/rankings")

        assert get_pokemon_called["value"] is True
