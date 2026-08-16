"""
Tests for pvpoke_data.py

The caching tests mock requests.get and redirect CACHE_DIR to pytest's
tmp_path fixture, so they run instantly, never touch the network, and never
pollute the real .pvpoke_cache/ directory. One integration test at the
bottom hits the real PvPoke data files as a smoke test -- run it deliberately
(it's excluded by default via `pytest -m "not integration"`).
"""

import json
import os
import time
from unittest.mock import MagicMock

import pytest

import pvpoke_data


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Redirect the module's CACHE_DIR to a throwaway directory for this test."""
    monkeypatch.setattr(pvpoke_data, "CACHE_DIR", tmp_path)
    return tmp_path


class TestCachedGet:
    def test_fetches_and_writes_cache_on_first_call(self, isolated_cache, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hello": "world"}
        mock_get = MagicMock(return_value=mock_resp)
        monkeypatch.setattr(pvpoke_data.requests, "get", mock_get)

        result = pvpoke_data._cached_get("http://example.test/data.json", "mykey", ttl=3600)

        assert result == {"hello": "world"}
        mock_get.assert_called_once()
        cache_file = isolated_cache / "mykey.json"
        assert cache_file.exists()
        assert json.loads(cache_file.read_text()) == {"hello": "world"}

    def test_returns_cached_value_without_refetching_within_ttl(self, isolated_cache, monkeypatch):
        cache_file = isolated_cache / "mykey.json"
        cache_file.write_text(json.dumps({"cached": True}))

        mock_get = MagicMock(side_effect=AssertionError("should not be called -- cache is fresh"))
        monkeypatch.setattr(pvpoke_data.requests, "get", mock_get)

        result = pvpoke_data._cached_get("http://example.test/data.json", "mykey", ttl=3600)

        assert result == {"cached": True}
        mock_get.assert_not_called()

    def test_refetches_after_ttl_expires(self, isolated_cache, monkeypatch):
        cache_file = isolated_cache / "mykey.json"
        cache_file.write_text(json.dumps({"stale": True}))
        # Backdate the file's mtime so it's outside a 1-second TTL.
        old_time = time.time() - 10
        os.utime(cache_file, (old_time, old_time))

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"fresh": True}
        mock_get = MagicMock(return_value=mock_resp)
        monkeypatch.setattr(pvpoke_data.requests, "get", mock_get)

        result = pvpoke_data._cached_get("http://example.test/data.json", "mykey", ttl=1)

        assert result == {"fresh": True}
        mock_get.assert_called_once()


class TestBuildSpeciesLookup:
    def test_builds_dict_keyed_by_species_id(self):
        gamemaster = {
            "pokemon": [
                {"speciesId": "mimikyu", "baseStats": {"atk": 177, "def": 199, "hp": 146}},
                {"speciesId": "lickilicky", "baseStats": {"atk": 161, "def": 181, "hp": 242}},
            ]
        }
        lookup = pvpoke_data.build_species_lookup(gamemaster)
        assert set(lookup.keys()) == {"mimikyu", "lickilicky"}
        assert lookup["mimikyu"]["baseStats"]["atk"] == 177


class TestLeagueConfig:
    def test_expected_leagues_and_cp_caps(self):
        assert pvpoke_data.LEAGUE_CP_CAPS == {
            "great": 1500,
            "ultra": 2500,
            "master": 10000,
        }


@pytest.mark.integration
class TestRealFetch:
    """Hits PvPoke's actual data files on GitHub. Skip in normal runs with
    `pytest -m "not integration"`; run deliberately to smoke-test against
    the live source (e.g. after PvPoke changes their data format)."""

    def test_fetch_gamemaster_has_expected_shape(self):
        gamemaster = pvpoke_data.fetch_gamemaster()
        assert "pokemon" in gamemaster
        assert len(gamemaster["pokemon"]) > 500  # sanity floor, not an exact count

    def test_fetch_rankings_returns_ranked_list(self):
        rankings = pvpoke_data.fetch_rankings("great", "overall")
        assert isinstance(rankings, list)
        assert len(rankings) > 0
        assert "speciesId" in rankings[0]
