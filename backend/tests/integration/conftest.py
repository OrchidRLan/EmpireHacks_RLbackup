"""Integration-level conftest.py.

Provides helpers and patches shared across integration tests:
  - _sqlite_insert: a SQLite-compatible replacement for pg_insert that handles
    ON CONFLICT DO NOTHING using the standard SQLAlchemy insert dialect.
  - Apartment/User/Preferences factory helpers for quickly seeding test data.
"""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import insert as sa_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.apartment import Apartment, NeighborInfo
from app.models.match import Match
from app.models.preferences import (
    NegotiationPreferences,
    ObjectivePreferences,
    SubjectivePreferences,
)
from app.models.user import User


# ── Data factories ────────────────────────────────────────────────────────────

def make_user_data(**overrides) -> dict:
    uid = str(uuid.uuid4())
    return {"id": uid, "name": "Test User", "phone": "+15550001234", **overrides}


def make_apartment_data(**overrides) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "name": "Test Apt",
        "bedroom_type": "1BR",
        "price": 2000,
        "neighbor_id": None,
        "latitude": 40.7128,
        "longitude": -74.006,
        "move_in_date": None,
        "lease_length_months": None,
        "laundry": [],
        "parking": [],
        "pets": False,
        "host_phone": None,
        "host_email": None,
        "images": [],
        "image_labels": ["modern", "bright"],
        "created_at": datetime.utcnow(),
        **overrides,
    }


def make_objective_prefs_data(user_id: str, **overrides) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "bedroom_type": "1BR",
        "selected_areas": [],
        "min_budget": 1500,
        "max_budget": 2500,
        "move_in_date": date(2025, 9, 1),
        "move_out_date": None,
        "lease_length_months": None,
        "laundry": [],
        "parking": [],
        "pets": False,
        "work_latitude": None,
        "work_longitude": None,
        "commute_method": None,
        "max_commute_minutes": None,
        **overrides,
    }


def make_subjective_prefs_data(user_id: str, **overrides) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "priority_focus": "features",
        "image_labels": ["modern"],
        "neighborhood_labels": [],
        **overrides,
    }


def make_negotiation_prefs_data(user_id: str, **overrides) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "enable_automation": True,
        "negotiable_items": [],
        "goals": [],
        "max_rent": None,
        "max_deposit": None,
        "latest_move_in_date": None,
        "min_lease_months": None,
        "max_lease_months": None,
        "negotiation_style": None,
        **overrides,
    }


# ── Database seed helpers ─────────────────────────────────────────────────────

async def seed_user(db: AsyncSession, **overrides) -> User:
    data = make_user_data(**overrides)
    user = User(**data)
    db.add(user)
    await db.flush()
    return user


async def seed_apartment(db: AsyncSession, **overrides) -> Apartment:
    data = make_apartment_data(**overrides)
    apt = Apartment(**data)
    db.add(apt)
    await db.flush()
    return apt


async def seed_objective_prefs(
    db: AsyncSession, user_id: str, **overrides
) -> ObjectivePreferences:
    data = make_objective_prefs_data(user_id, **overrides)
    obj = ObjectivePreferences(**data)
    db.add(obj)
    await db.flush()
    return obj


async def seed_subjective_prefs(
    db: AsyncSession, user_id: str, **overrides
) -> SubjectivePreferences:
    data = make_subjective_prefs_data(user_id, **overrides)
    subj = SubjectivePreferences(**data)
    db.add(subj)
    await db.flush()
    return subj


async def seed_negotiation_prefs(
    db: AsyncSession, user_id: str, **overrides
) -> NegotiationPreferences:
    data = make_negotiation_prefs_data(user_id, **overrides)
    neg = NegotiationPreferences(**data)
    db.add(neg)
    await db.flush()
    return neg


async def seed_match(
    db: AsyncSession,
    user_id: str,
    apartment_id: str,
    **overrides,
) -> Match:
    match = Match(
        id=str(uuid.uuid4()),
        user_id=user_id,
        apartment_id=apartment_id,
        status="not_started",
        match_score=overrides.pop("match_score", 0.75),
        commute_minutes=overrides.pop("commute_minutes", None),
        match_reasoning=overrides.pop("match_reasoning", None),
        created_at=datetime.utcnow(),
        **overrides,
    )
    db.add(match)
    await db.flush()
    return match
