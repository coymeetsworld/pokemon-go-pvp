"""
Tests for build_pokemon_list.py

build_list() itself hits the network (via pvpoke_data) and is covered
separately as an integration test -- these tests focus on the pure logic:
name cleaning and the low/high attack bucket filters, using hand-built
fixture data so they run instantly with no network dependency.
"""

import pytest

from build_pokemon_list import clean_search_name, build_low_atk_list, build_high_atk_list


class TestCleanSearchName:
    @pytest.mark.parametrize("raw,expected", [
        ("Mimikyu (Busted)", "mimikyu"),
        ("Altaria", "altaria"),
        ("Altaria (Shadow)", "altaria"),
        ("Lickilicky", "lickilicky"),
        ("Ninetales (Alolan)", "ninetales"),
        ("Giratina (Origin)", "giratina"),
        ("Mr. Mime", "mr. mime"),  # multi-word names with no parenthetical stay intact
    ])
    def test_strips_form_suffix_and_lowercases(self, raw, expected):
        assert clean_search_name(raw) == expected


def _make_pokemon(name, atk_iv, def_iv, hp_iv):
    """Minimal fixture matching the fields build_low_atk_list/build_high_atk_list
    actually read -- doesn't need every field build_list() produces."""
    return {
        "name": name,
        "search_name": name.lower(),
        "ideal_atk_iv": atk_iv,
        "ideal_def_iv": def_iv,
        "ideal_hp_iv": hp_iv,
    }


class TestBuildLowAtkList:
    def test_includes_low_atk_high_bulk(self):
        pokemon = [_make_pokemon("mimikyu", 1, 14, 15)]
        assert build_low_atk_list(pokemon) == ["mimikyu"]

    def test_excludes_when_atk_too_high(self):
        pokemon = [_make_pokemon("high-atk-mon", 6, 14, 15)]
        assert build_low_atk_list(pokemon) == []

    def test_excludes_when_def_below_floor(self):
        pokemon = [_make_pokemon("low-def-mon", 0, 9, 15)]
        assert build_low_atk_list(pokemon) == []

    def test_excludes_when_hp_below_floor(self):
        pokemon = [_make_pokemon("low-hp-mon", 0, 15, 9)]
        assert build_low_atk_list(pokemon) == []

    def test_atk_boundary_inclusive(self):
        """atk IV 5 is the top of the 'low' range (range(0,6) == 0..5) -- must be included."""
        pokemon = [_make_pokemon("boundary-mon", 5, 10, 10)]
        assert build_low_atk_list(pokemon) == ["boundary-mon"]

    def test_def_hp_boundary_inclusive(self):
        """def/hp IV exactly 10 is the floor -- must be included, not excluded."""
        pokemon = [_make_pokemon("boundary-mon", 0, 10, 10)]
        assert build_low_atk_list(pokemon) == ["boundary-mon"]

    def test_multiple_pokemon_filtered_correctly(self):
        pokemon = [
            _make_pokemon("keep-me", 2, 12, 13),
            _make_pokemon("drop-me-atk", 8, 12, 13),
            _make_pokemon("drop-me-def", 2, 5, 13),
        ]
        assert build_low_atk_list(pokemon) == ["keep-me"]


class TestBuildHighAtkList:
    def test_includes_high_everything(self):
        pokemon = [_make_pokemon("tank", 12, 13, 14)]
        assert build_high_atk_list(pokemon) == ["tank"]

    def test_excludes_when_atk_below_floor(self):
        pokemon = [_make_pokemon("not-tanky-enough", 9, 13, 14)]
        assert build_high_atk_list(pokemon) == []

    def test_atk_boundary_inclusive(self):
        pokemon = [_make_pokemon("boundary-mon", 10, 10, 10)]
        assert build_high_atk_list(pokemon) == ["boundary-mon"]

    def test_low_and_high_lists_are_mutually_exclusive_for_typical_data(self):
        """A mon in the low bucket (atk 0-5) can never also be in the high
        bucket (atk >=10) -- guards against an overlap bug if thresholds
        are ever edited inconsistently."""
        pokemon = [_make_pokemon("low-atk-mon", 3, 12, 13)]
        assert build_low_atk_list(pokemon) == ["low-atk-mon"]
        assert build_high_atk_list(pokemon) == []
