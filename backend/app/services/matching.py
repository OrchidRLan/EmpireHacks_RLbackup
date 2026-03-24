from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.apartment import Apartment
from app.models.match import Match
from app.models.preferences import ObjectivePreferences, SubjectivePreferences
from app.services.commute import calculate_commute_minutes


# ── Objective filter ──────────────────────────────────────────────────────────

def passes_objective_filter(apartment: Apartment, prefs: ObjectivePreferences) -> bool:
    """Return True if apartment satisfies ALL hard objective criteria.

    Rules:
    - bedroom_type: must equal prefs.bedroom_type
    - price: prefs.min_budget <= price <= prefs.max_budget
    - neighbor_id: if prefs.selected_areas non-empty, apt.neighbor_id must be in it
    - move_in_date: apartment must be available on or before prefs.move_in_date (skipped if either is None)
    - lease_length_months: apartment lease must be >= prefs.lease_length_months (skipped if either is None)
    - laundry: if prefs.laundry non-empty, intersection with apt.laundry must be non-empty
    - parking: same intersection logic
    - pets: if prefs.pets is True, apt.pets must be True
    """
    if apartment.bedroom_type != prefs.bedroom_type:
        return False
    if not (prefs.min_budget <= apartment.price <= prefs.max_budget):
        return False
    if prefs.selected_areas and apartment.neighbor_id not in prefs.selected_areas:
        return False
    if apartment.move_in_date and prefs.move_in_date:
        if apartment.move_in_date > prefs.move_in_date:
            return False
    if apartment.lease_length_months and prefs.lease_length_months:
        if apartment.lease_length_months < prefs.lease_length_months:
            return False
    if prefs.laundry and not set(apartment.laundry or []) & set(prefs.laundry):
        return False
    if prefs.parking and not set(apartment.parking or []) & set(prefs.parking):
        return False
    if prefs.pets and not apartment.pets:
        return False
    return True


async def run_objective_filter(user_id: str, db: AsyncSession) -> int:
    """Apply objective filter to all apartments, bulk-insert Match rows.

    Idempotent: uses INSERT ... ON CONFLICT DO NOTHING on (user_id, apartment_id).
    Computes commute_minutes inline when work coordinates + method are set.
    Returns count of newly inserted Match rows.
    Raises ValueError if user has no ObjectivePreferences.
    """
    prefs_result = await db.execute(
        select(ObjectivePreferences).where(ObjectivePreferences.user_id == user_id).limit(1)
    )
    prefs = prefs_result.scalar_one_or_none()
    if not prefs:
        raise ValueError(f"No ObjectivePreferences found for user {user_id}")

    apts_result = await db.execute(select(Apartment))
    apartments = apts_result.scalars().all()

    rows_to_insert = []
    for apt in apartments:
        if not passes_objective_filter(apt, prefs):
            continue
        commute_minutes = None
        if all([prefs.work_latitude, prefs.work_longitude, prefs.commute_method,
                apt.latitude, apt.longitude]):
            commute_minutes = calculate_commute_minutes(
                apt.latitude, apt.longitude,
                prefs.work_latitude, prefs.work_longitude,
                prefs.commute_method,
            )
        rows_to_insert.append({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "apartment_id": apt.id,
            "status": "not_started",
            "commute_minutes": commute_minutes,
            "match_score": None,
            "match_reasoning": None,
            "created_at": datetime.utcnow(),
        })

    if not rows_to_insert:
        return 0

    stmt = pg_insert(Match).values(rows_to_insert)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_match_user_apartment")
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount


# ── Swipe / label update ──────────────────────────────────────────────────────

def apply_swipe_to_labels(
    current_labels: list[str],
    apartment_labels: list[str],
    action: Literal["like", "dislike", "love"],
) -> list[str]:
    """Pure function — never mutates inputs. Returns new label list.

    - like:    union (add absent labels once)
    - dislike: difference (remove overlapping labels)
    - love:    double-add (add each label once if absent, then add again -> double weight)
    """
    if action == "like":
        current_set = set(current_labels)
        return current_labels + [l for l in apartment_labels if l not in current_set]
    elif action == "dislike":
        remove_set = set(apartment_labels)
        return [l for l in current_labels if l not in remove_set]
    elif action == "love":
        current_set = set(current_labels)
        additions = [l for l in apartment_labels if l not in current_set]
        return current_labels + additions + apartment_labels
    else:
        raise ValueError(f"Unknown action: {action!r}. Must be 'like', 'dislike', or 'love'.")


# ── Scoring ───────────────────────────────────────────────────────────────────

def jaccard_similarity(a: list[str], b: list[str]) -> float:
    """Jaccard coefficient on sets. Returns 0.0 if both are empty."""
    set_a, set_b = set(a), set(b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def normalize_price_score(price: int, min_budget: int, max_budget: int) -> float:
    """Score 1.0 at min_budget, 0.0 at max_budget, clamped to [0, 1]."""
    if min_budget >= max_budget:
        return 0.5
    raw = 1.0 - (price - min_budget) / (max_budget - min_budget)
    return max(0.0, min(1.0, raw))


def normalize_commute_score(
    commute_minutes: int | None,
    max_commute_minutes: int | None,
) -> float:
    """Score 1.0 at 0 min commute, 0.0 at max_commute_minutes. Returns 0.5 if either None."""
    if commute_minutes is None or not max_commute_minutes:
        return 0.5
    raw = 1.0 - commute_minutes / max_commute_minutes
    return max(0.0, min(1.0, raw))


PRIORITY_WEIGHTS: dict[str, tuple[float, float, float]] = {
    # (label_weight, price_weight, commute_weight)
    "features": (0.6, 0.2, 0.2),
    "price":    (0.2, 0.6, 0.2),
    "location": (0.2, 0.2, 0.6),
}


def compute_match_score(
    label_score: float,
    price_score: float,
    commute_score: float,
    priority_focus: str | None,
) -> float:
    """Weighted average of three component scores using priority_focus weights."""
    w1, w2, w3 = PRIORITY_WEIGHTS.get(priority_focus or "features", PRIORITY_WEIGHTS["features"])
    return round(w1 * label_score + w2 * price_score + w3 * commute_score, 4)


async def recalculate_all_match_scores(user_id: str, db: AsyncSession) -> int:
    """Recompute match_score for every Match row of a user. Returns count updated."""
    subj_result = await db.execute(
        select(SubjectivePreferences).where(SubjectivePreferences.user_id == user_id).limit(1)
    )
    subj = subj_result.scalar_one_or_none()
    if not subj:
        raise ValueError(f"No SubjectivePreferences found for user {user_id}")

    obj_result = await db.execute(
        select(ObjectivePreferences).where(ObjectivePreferences.user_id == user_id).limit(1)
    )
    obj = obj_result.scalar_one_or_none()
    if not obj:
        raise ValueError(f"No ObjectivePreferences found for user {user_id}")

    matches_result = await db.execute(
        select(Match)
        .where(Match.user_id == user_id)
        .options(selectinload(Match.apartment))
    )
    matches = matches_result.scalars().all()

    for match in matches:
        apt = match.apartment
        if not apt:
            continue
        label_score = jaccard_similarity(subj.image_labels or [], apt.image_labels or [])
        price_score = normalize_price_score(apt.price, obj.min_budget, obj.max_budget)
        commute_score = normalize_commute_score(match.commute_minutes, obj.max_commute_minutes)
        match.match_score = compute_match_score(
            label_score, price_score, commute_score, subj.priority_focus
        )

    await db.commit()
    return len(matches)


async def process_swipe(
    user_id: str,
    apartment_id: str,
    action: Literal["like", "dislike", "love"],
    db: AsyncSession,
) -> int:
    """Update user label profile based on swipe, then rescore all matches.

    Returns count of rescored matches.
    Raises ValueError if SubjectivePreferences missing.
    Raises ValueError if apartment not found.
    """
    subj_result = await db.execute(
        select(SubjectivePreferences).where(SubjectivePreferences.user_id == user_id).limit(1)
    )
    subj = subj_result.scalar_one_or_none()
    if not subj:
        raise ValueError(f"No SubjectivePreferences found for user {user_id}")

    apt = await db.get(Apartment, apartment_id)
    if not apt:
        raise ValueError(f"Apartment {apartment_id} not found")

    subj.image_labels = apply_swipe_to_labels(
        subj.image_labels or [], apt.image_labels or [], action
    )
    await db.flush()
    return await recalculate_all_match_scores(user_id, db)
