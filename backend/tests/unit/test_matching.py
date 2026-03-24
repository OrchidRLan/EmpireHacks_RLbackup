"""Unit tests for app/services/matching.py.

Every test is pure-function — no database, no I/O.
We build lightweight stub objects that expose only the attributes
the functions under test actually read, keeping tests fast and focused.
"""

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.matching import (
    apply_swipe_to_labels,
    compute_match_score,
    jaccard_similarity,
    normalize_commute_score,
    normalize_price_score,
    passes_objective_filter,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_apt(**overrides: Any) -> SimpleNamespace:
    """Return a minimal Apartment-like stub."""
    defaults = dict(
        bedroom_type="1BR",
        price=2000,
        neighbor_id="area-1",
        move_in_date=None,
        lease_length_months=None,
        laundry=[],
        parking=[],
        pets=False,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_prefs(**overrides: Any) -> SimpleNamespace:
    """Return a minimal ObjectivePreferences-like stub."""
    defaults = dict(
        bedroom_type="1BR",
        min_budget=1500,
        max_budget=2500,
        selected_areas=[],
        move_in_date=None,
        lease_length_months=None,
        laundry=[],
        parking=[],
        pets=False,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ── passes_objective_filter ───────────────────────────────────────────────────

class TestPassesObjectiveFilter:
    def test_all_defaults_pass(self):
        """An apartment with no constraints passes a relaxed prefs."""
        assert passes_objective_filter(make_apt(), make_prefs()) is True

    def test_wrong_bedroom_type_fails(self):
        apt = make_apt(bedroom_type="2BR")
        prefs = make_prefs(bedroom_type="1BR")
        assert passes_objective_filter(apt, prefs) is False

    def test_price_below_minimum_fails(self):
        apt = make_apt(price=1000)
        prefs = make_prefs(min_budget=1500, max_budget=2500)
        assert passes_objective_filter(apt, prefs) is False

    def test_price_above_maximum_fails(self):
        apt = make_apt(price=3000)
        prefs = make_prefs(min_budget=1500, max_budget=2500)
        assert passes_objective_filter(apt, prefs) is False

    def test_price_at_boundaries_passes(self):
        prefs = make_prefs(min_budget=1500, max_budget=2500)
        assert passes_objective_filter(make_apt(price=1500), prefs) is True
        assert passes_objective_filter(make_apt(price=2500), prefs) is True

    def test_selected_areas_filters_wrong_neighborhood(self):
        apt = make_apt(neighbor_id="soho")
        prefs = make_prefs(selected_areas=["williamsburg", "bushwick"])
        assert passes_objective_filter(apt, prefs) is False

    def test_selected_areas_empty_allows_any_neighborhood(self):
        apt = make_apt(neighbor_id="soho")
        prefs = make_prefs(selected_areas=[])
        assert passes_objective_filter(apt, prefs) is True

    def test_selected_areas_matching_neighborhood_passes(self):
        apt = make_apt(neighbor_id="soho")
        prefs = make_prefs(selected_areas=["soho", "tribeca"])
        assert passes_objective_filter(apt, prefs) is True

    def test_move_in_date_too_late_fails(self):
        apt = make_apt(move_in_date=date(2025, 9, 1))
        prefs = make_prefs(move_in_date=date(2025, 6, 1))
        assert passes_objective_filter(apt, prefs) is False

    def test_move_in_date_before_pref_passes(self):
        apt = make_apt(move_in_date=date(2025, 4, 1))
        prefs = make_prefs(move_in_date=date(2025, 6, 1))
        assert passes_objective_filter(apt, prefs) is True

    def test_apt_move_in_date_none_always_passes_date_check(self):
        apt = make_apt(move_in_date=None)
        prefs = make_prefs(move_in_date=date(2025, 6, 1))
        assert passes_objective_filter(apt, prefs) is True

    def test_mismatched_lease_length_fails(self):
        apt = make_apt(lease_length_months=12)
        prefs = make_prefs(lease_length_months=6)
        assert passes_objective_filter(apt, prefs) is False

    def test_matching_lease_length_passes(self):
        apt = make_apt(lease_length_months=12)
        prefs = make_prefs(lease_length_months=12)
        assert passes_objective_filter(apt, prefs) is True

    def test_lease_length_none_on_either_side_skips_check(self):
        # apt has no lease restriction
        apt = make_apt(lease_length_months=None)
        prefs = make_prefs(lease_length_months=12)
        assert passes_objective_filter(apt, prefs) is True

    def test_laundry_no_intersection_fails(self):
        apt = make_apt(laundry=["in-unit"])
        prefs = make_prefs(laundry=["laundromat"])
        assert passes_objective_filter(apt, prefs) is False

    def test_laundry_intersection_passes(self):
        apt = make_apt(laundry=["in-unit", "shared"])
        prefs = make_prefs(laundry=["in-unit"])
        assert passes_objective_filter(apt, prefs) is True

    def test_laundry_prefs_empty_skips_check(self):
        apt = make_apt(laundry=[])
        prefs = make_prefs(laundry=[])
        assert passes_objective_filter(apt, prefs) is True

    def test_parking_no_intersection_fails(self):
        apt = make_apt(parking=["garage"])
        prefs = make_prefs(parking=["street"])
        assert passes_objective_filter(apt, prefs) is False

    def test_parking_intersection_passes(self):
        apt = make_apt(parking=["street", "garage"])
        prefs = make_prefs(parking=["street"])
        assert passes_objective_filter(apt, prefs) is True

    def test_pets_required_but_not_allowed_fails(self):
        apt = make_apt(pets=False)
        prefs = make_prefs(pets=True)
        assert passes_objective_filter(apt, prefs) is False

    def test_pets_required_and_allowed_passes(self):
        apt = make_apt(pets=True)
        prefs = make_prefs(pets=True)
        assert passes_objective_filter(apt, prefs) is True

    def test_pets_not_required_no_check(self):
        apt = make_apt(pets=False)
        prefs = make_prefs(pets=False)
        assert passes_objective_filter(apt, prefs) is True


# ── apply_swipe_to_labels ─────────────────────────────────────────────────────

class TestApplySwipeToLabels:
    def test_like_adds_absent_labels(self):
        result = apply_swipe_to_labels(["bright"], ["modern", "bright"], "like")
        assert result == ["bright", "modern"]

    def test_like_does_not_duplicate_existing(self):
        result = apply_swipe_to_labels(["modern"], ["modern"], "like")
        assert result == ["modern"]

    def test_like_on_empty_current(self):
        result = apply_swipe_to_labels([], ["spacious", "light"], "like")
        assert result == ["spacious", "light"]

    def test_like_with_empty_apartment_labels(self):
        result = apply_swipe_to_labels(["modern"], [], "like")
        assert result == ["modern"]

    def test_dislike_removes_overlapping_labels(self):
        result = apply_swipe_to_labels(["modern", "cramped"], ["cramped"], "dislike")
        assert result == ["modern"]

    def test_dislike_removes_all_overlapping(self):
        result = apply_swipe_to_labels(["a", "b", "c"], ["a", "c"], "dislike")
        assert result == ["b"]

    def test_dislike_no_overlap_keeps_all(self):
        result = apply_swipe_to_labels(["modern"], ["outdated"], "dislike")
        assert result == ["modern"]

    def test_dislike_empty_current_stays_empty(self):
        result = apply_swipe_to_labels([], ["cramped"], "dislike")
        assert result == []

    def test_love_doubles_weight_of_new_labels(self):
        # love: union first, then append all apartment labels again
        result = apply_swipe_to_labels(["bright"], ["modern", "spacious"], "love")
        # existing: ["bright"]
        # additions (absent): ["modern", "spacious"]
        # result: ["bright"] + ["modern", "spacious"] + ["modern", "spacious"]
        assert result == ["bright", "modern", "spacious", "modern", "spacious"]

    def test_love_already_present_labels_are_still_appended(self):
        result = apply_swipe_to_labels(["modern"], ["modern"], "love")
        # additions (absent) = []
        # result = ["modern"] + [] + ["modern"]
        assert result == ["modern", "modern"]

    def test_love_empty_current_adds_labels_twice(self):
        result = apply_swipe_to_labels([], ["a", "b"], "love")
        assert result == ["a", "b", "a", "b"]

    def test_unknown_action_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown action"):
            apply_swipe_to_labels([], [], "super-like")

    def test_inputs_are_not_mutated(self):
        current = ["a"]
        apartment = ["b"]
        apply_swipe_to_labels(current, apartment, "like")
        apply_swipe_to_labels(current, apartment, "dislike")
        apply_swipe_to_labels(current, apartment, "love")
        assert current == ["a"]
        assert apartment == ["b"]


# ── jaccard_similarity ────────────────────────────────────────────────────────

class TestJaccardSimilarity:
    def test_identical_lists_return_one(self):
        assert jaccard_similarity(["a", "b"], ["a", "b"]) == 1.0

    def test_disjoint_lists_return_zero(self):
        assert jaccard_similarity(["a"], ["b"]) == 0.0

    def test_partial_overlap(self):
        # intersection={a}, union={a,b,c}  -> 1/3
        result = jaccard_similarity(["a", "b"], ["a", "c"])
        assert abs(result - 1 / 3) < 1e-9

    def test_both_empty_returns_zero(self):
        assert jaccard_similarity([], []) == 0.0

    def test_one_empty_returns_zero(self):
        assert jaccard_similarity(["a"], []) == 0.0
        assert jaccard_similarity([], ["a"]) == 0.0

    def test_duplicates_are_treated_as_sets(self):
        # set(["a","a"]) = {"a"}
        assert jaccard_similarity(["a", "a"], ["a"]) == 1.0


# ── normalize_price_score ─────────────────────────────────────────────────────

class TestNormalizePriceScore:
    def test_at_minimum_returns_one(self):
        assert normalize_price_score(1500, 1500, 2500) == 1.0

    def test_at_maximum_returns_zero(self):
        assert normalize_price_score(2500, 1500, 2500) == 0.0

    def test_midpoint(self):
        assert normalize_price_score(2000, 1500, 2500) == pytest.approx(0.5)

    def test_below_minimum_clamped_to_one(self):
        assert normalize_price_score(1000, 1500, 2500) == 1.0

    def test_above_maximum_clamped_to_zero(self):
        assert normalize_price_score(3000, 1500, 2500) == 0.0

    def test_equal_min_max_returns_half(self):
        assert normalize_price_score(2000, 2000, 2000) == 0.5


# ── normalize_commute_score ───────────────────────────────────────────────────

class TestNormalizeCommuteScore:
    def test_zero_minutes_returns_one(self):
        assert normalize_commute_score(0, 60) == 1.0

    def test_at_max_returns_zero(self):
        assert normalize_commute_score(60, 60) == 0.0

    def test_half_max_returns_half(self):
        assert normalize_commute_score(30, 60) == pytest.approx(0.5)

    def test_commute_none_returns_half(self):
        assert normalize_commute_score(None, 60) == 0.5

    def test_max_commute_none_returns_half(self):
        assert normalize_commute_score(30, None) == 0.5

    def test_both_none_returns_half(self):
        assert normalize_commute_score(None, None) == 0.5

    def test_over_max_clamped_to_zero(self):
        assert normalize_commute_score(120, 60) == 0.0

    def test_max_commute_zero_returns_half(self):
        # max_commute_minutes=0 is falsy — function returns 0.5
        assert normalize_commute_score(10, 0) == 0.5


# ── compute_match_score ───────────────────────────────────────────────────────

class TestComputeMatchScore:
    def test_features_focus_weights(self):
        # weights: label=0.6, price=0.2, commute=0.2
        score = compute_match_score(1.0, 1.0, 1.0, "features")
        assert score == pytest.approx(1.0)

    def test_price_focus_weights(self):
        # weights: label=0.2, price=0.6, commute=0.2
        score = compute_match_score(0.0, 1.0, 0.0, "price")
        assert score == pytest.approx(0.6)

    def test_location_focus_weights(self):
        # weights: label=0.2, price=0.2, commute=0.6
        score = compute_match_score(0.0, 0.0, 1.0, "location")
        assert score == pytest.approx(0.6)

    def test_none_priority_defaults_to_features(self):
        score_none = compute_match_score(0.5, 0.5, 0.5, None)
        score_features = compute_match_score(0.5, 0.5, 0.5, "features")
        assert score_none == score_features

    def test_unknown_priority_defaults_to_features(self):
        score_unknown = compute_match_score(0.5, 0.5, 0.5, "banana")
        score_features = compute_match_score(0.5, 0.5, 0.5, "features")
        assert score_unknown == score_features

    def test_all_zeros_returns_zero(self):
        assert compute_match_score(0.0, 0.0, 0.0, "features") == 0.0

    def test_result_is_rounded_to_four_decimals(self):
        score = compute_match_score(1 / 3, 1 / 3, 1 / 3, "features")
        # raw = 1/3 -> rounded to 4 decimal places
        assert score == round(1 / 3, 4)

    def test_weighted_average_correctness_features(self):
        # label=0.8, price=0.5, commute=0.2, focus=features (0.6,0.2,0.2)
        expected = round(0.6 * 0.8 + 0.2 * 0.5 + 0.2 * 0.2, 4)
        assert compute_match_score(0.8, 0.5, 0.2, "features") == pytest.approx(expected)

    def test_weighted_average_correctness_price(self):
        expected = round(0.2 * 0.8 + 0.6 * 0.5 + 0.2 * 0.2, 4)
        assert compute_match_score(0.8, 0.5, 0.2, "price") == pytest.approx(expected)

    def test_weighted_average_correctness_location(self):
        expected = round(0.2 * 0.8 + 0.2 * 0.5 + 0.6 * 0.2, 4)
        assert compute_match_score(0.8, 0.5, 0.2, "location") == pytest.approx(expected)
