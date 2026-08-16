"""
Tests for iv_calculator.py

Mimikyu and Lickilicky values are verified against PvPoke's own published
rankings (cross-checked manually when this app was first built) -- these are
the strongest regression guard in the suite, since a change to the CPM table
or the stat-product formula that broke correctness would show up here first.
"""

import math

import pytest

from iv_calculator import best_iv_for_cap, _calc_cp, CPM


class TestBestIvForCap:
    def test_mimikyu_great_league(self):
        """Mimikyu (base 177/199/146) @ CP1500 -> known-correct: IV 1/14/15."""
        result = best_iv_for_cap(177, 199, 146, 1500)
        assert result["atk"] == 1
        assert result["def"] == 14
        assert result["hp"] == 15
        assert result["cp"] <= 1500

    def test_lickilicky_great_league(self):
        """Lickilicky (base 161/181/242) @ CP1500 -> known-correct: IV 0/15/10."""
        result = best_iv_for_cap(161, 181, 242, 1500)
        assert result["atk"] == 0
        assert result["def"] == 15
        assert result["hp"] == 10
        assert result["cp"] <= 1500

    def test_result_never_exceeds_cp_cap(self):
        """The whole point of the function -- returned CP must respect the cap."""
        for base_atk, base_def, base_hp in [(177, 199, 146), (161, 181, 242), (100, 100, 100)]:
            for cp_cap in (500, 1500, 2500):
                result = best_iv_for_cap(base_atk, base_def, base_hp, cp_cap)
                assert result["cp"] <= cp_cap

    def test_ivs_within_valid_range(self):
        """IVs are always 0-15 per stat."""
        result = best_iv_for_cap(177, 199, 146, 1500)
        for stat in ("atk", "def", "hp"):
            assert 0 <= result[stat] <= 15

    def test_returns_none_when_even_zero_iv_level_one_exceeds_cap(self):
        """A Pokemon whose base stats alone exceed the cap at the lowest
        possible level/IVs has no valid spread -- function should return None
        rather than raising."""
        result = best_iv_for_cap(500, 500, 500, 10)
        assert result is None

    def test_is_memoized(self):
        """best_iv_for_cap is decorated with lru_cache -- repeat calls with
        identical args should be cache hits, not recomputed."""
        best_iv_for_cap.cache_clear()
        best_iv_for_cap(177, 199, 146, 1500)
        best_iv_for_cap(177, 199, 146, 1500)
        info = best_iv_for_cap.cache_info()
        assert info.hits == 1
        assert info.misses == 1


class TestCalcCp:
    def test_known_cp_value(self):
        """Sanity check the raw CP formula against Mimikyu's known result:
        base 177/199/146 + IV 1/14/15 at level 25.5 -> CP 1499."""
        cpm = CPM[25.5]
        cp = _calc_cp(177 + 1, 199 + 14, 146 + 15, cpm)
        assert cp == 1499

    def test_cp_increases_with_level(self):
        """CP should be monotonically non-decreasing as CPM (level) increases,
        for fixed stats."""
        stats = (150, 150, 150)
        cps = [_calc_cp(*stats, CPM[lvl]) for lvl in sorted(CPM.keys())]
        assert cps == sorted(cps)


class TestCpmTable:
    def test_cpm_bounds(self):
        """CPM values should be strictly increasing from level 1 to 51,
        and stay within (0, 1)."""
        levels = sorted(CPM.keys())
        assert levels[0] == 1
        assert levels[-1] == 51
        for lvl in levels:
            assert 0 < CPM[lvl] < 1
        cpm_values = [CPM[lvl] for lvl in levels]
        assert cpm_values == sorted(cpm_values)
