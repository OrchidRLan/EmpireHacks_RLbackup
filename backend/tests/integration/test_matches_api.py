"""Integration tests for match-related endpoints.

Endpoints covered:
  POST /users/{id}/run-filter
  POST /users/{id}/swipe
  GET  /users/{id}/matches/relevant

``run_objective_filter`` uses a PostgreSQL-specific ``pg_insert``.  Rather
than patching the insert dialect (fragile), the run-filter tests patch the
entire service function so the HTTP layer is tested in isolation.  Swipe and
relevant-matches tests seed Match rows directly, so they exercise the full
stack against the real SQLite DB.
"""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from tests.integration.conftest import (
    seed_apartment,
    seed_match,
    seed_objective_prefs,
    seed_subjective_prefs,
    seed_user,
)


# ── POST /users/{id}/run-filter ───────────────────────────────────────────────

class TestRunFilter:
    async def test_run_filter_unknown_user_returns_404(self, test_client):
        resp = await test_client.post("/users/nonexistent-uuid/run-filter")
        assert resp.status_code == 404

    async def test_run_filter_no_prefs_returns_400(self, test_client, db_session):
        """Service raises ValueError when no ObjectivePreferences exist."""
        user = await seed_user(db_session)

        # Patch the service so we exercise only the HTTP error-handling logic
        with patch(
            "app.routers.matches.run_objective_filter",
            new_callable=AsyncMock,
            side_effect=ValueError(
                f"No ObjectivePreferences found for user {user.id}"
            ),
        ):
            resp = await test_client.post(f"/users/{user.id}/run-filter")

        assert resp.status_code == 400
        assert "ObjectivePreferences" in resp.json()["detail"]

    async def test_run_filter_returns_zero_when_no_apartments_match(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)

        with patch(
            "app.routers.matches.run_objective_filter",
            new_callable=AsyncMock,
            return_value=0,
        ):
            resp = await test_client.post(f"/users/{user.id}/run-filter")

        assert resp.status_code == 200
        assert resp.json() == {"matches_created": 0}

    async def test_run_filter_returns_count_from_service(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)

        with patch(
            "app.routers.matches.run_objective_filter",
            new_callable=AsyncMock,
            return_value=3,
        ):
            resp = await test_client.post(f"/users/{user.id}/run-filter")

        assert resp.status_code == 200
        assert resp.json() == {"matches_created": 3}

    async def test_run_filter_response_has_correct_shape(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)

        with patch(
            "app.routers.matches.run_objective_filter",
            new_callable=AsyncMock,
            return_value=7,
        ):
            resp = await test_client.post(f"/users/{user.id}/run-filter")

        body = resp.json()
        assert set(body.keys()) == {"matches_created"}
        assert isinstance(body["matches_created"], int)


# ── POST /users/{id}/swipe ────────────────────────────────────────────────────

class TestSwipe:
    async def test_swipe_like_returns_200(self, test_client, db_session):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session, image_labels=["modern", "bright"])
        await seed_subjective_prefs(
            db_session, user.id, image_labels=["cozy"]
        )
        await seed_objective_prefs(db_session, user.id)
        await seed_match(db_session, user.id, apt.id)

        resp = await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": apt.id, "action": "like"},
        )
        assert resp.status_code == 200

    async def test_swipe_like_response_contains_matches_rescored(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session, image_labels=["modern"])
        await seed_subjective_prefs(db_session, user.id, image_labels=[])
        await seed_objective_prefs(db_session, user.id)
        await seed_match(db_session, user.id, apt.id)

        resp = await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": apt.id, "action": "like"},
        )
        body = resp.json()
        assert "matches_rescored" in body
        assert body["matches_rescored"] == 1

    async def test_swipe_dislike_returns_200(self, test_client, db_session):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session, image_labels=["cramped"])
        await seed_subjective_prefs(
            db_session, user.id, image_labels=["modern", "cramped"]
        )
        await seed_objective_prefs(db_session, user.id)
        await seed_match(db_session, user.id, apt.id)

        resp = await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": apt.id, "action": "dislike"},
        )
        assert resp.status_code == 200

    async def test_swipe_love_returns_200(self, test_client, db_session):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session, image_labels=["luxury"])
        await seed_subjective_prefs(db_session, user.id, image_labels=[])
        await seed_objective_prefs(db_session, user.id)
        await seed_match(db_session, user.id, apt.id)

        resp = await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": apt.id, "action": "love"},
        )
        assert resp.status_code == 200

    async def test_swipe_missing_subjective_prefs_returns_404(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        # No SubjectivePreferences seeded — process_swipe raises ValueError

        resp = await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": apt.id, "action": "like"},
        )
        assert resp.status_code == 404

    async def test_swipe_unknown_apartment_returns_404(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        await seed_subjective_prefs(db_session, user.id)

        resp = await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": "nonexistent-apt-id", "action": "like"},
        )
        assert resp.status_code == 404

    async def test_swipe_invalid_action_returns_422(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)

        resp = await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": apt.id, "action": "super-like"},
        )
        assert resp.status_code == 422

    async def test_swipe_like_updates_image_labels_in_db(
        self, test_client, db_session
    ):
        """A like swipe should append apt labels to the user's image_labels."""
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session, image_labels=["spacious", "bright"])
        subj = await seed_subjective_prefs(
            db_session, user.id, image_labels=[]
        )
        await seed_objective_prefs(db_session, user.id)
        await seed_match(db_session, user.id, apt.id)

        await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": apt.id, "action": "like"},
        )

        await db_session.refresh(subj)
        assert "spacious" in subj.image_labels
        assert "bright" in subj.image_labels

    async def test_swipe_dislike_removes_image_labels_from_db(
        self, test_client, db_session
    ):
        """A dislike swipe should remove apt labels from the user's image_labels."""
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session, image_labels=["cramped"])
        subj = await seed_subjective_prefs(
            db_session, user.id, image_labels=["modern", "cramped"]
        )
        await seed_objective_prefs(db_session, user.id)
        await seed_match(db_session, user.id, apt.id)

        await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": apt.id, "action": "dislike"},
        )

        await db_session.refresh(subj)
        assert "cramped" not in subj.image_labels
        assert "modern" in subj.image_labels

    async def test_swipe_rescores_match_score(
        self, test_client, db_session
    ):
        """Verify that match.match_score is updated after a swipe."""
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session, image_labels=["modern"])
        await seed_subjective_prefs(
            db_session, user.id, image_labels=[], priority_focus="features"
        )
        await seed_objective_prefs(
            db_session, user.id, min_budget=1500, max_budget=2500
        )
        match = await seed_match(db_session, user.id, apt.id, match_score=None)

        await test_client.post(
            f"/users/{user.id}/swipe",
            json={"apartment_id": apt.id, "action": "like"},
        )

        await db_session.refresh(match)
        # After a like, the score should have been computed (not None)
        assert match.match_score is not None


# ── GET /users/{id}/matches/relevant ─────────────────────────────────────────

class TestRelevantMatches:
    async def test_relevant_returns_200(self, test_client, db_session):
        user = await seed_user(db_session)
        resp = await test_client.get(
            f"/users/{user.id}/matches/relevant", params={"min_score": 0.0}
        )
        assert resp.status_code == 200

    async def test_relevant_is_array(self, test_client, db_session):
        user = await seed_user(db_session)
        resp = await test_client.get(
            f"/users/{user.id}/matches/relevant", params={"min_score": 0.0}
        )
        assert isinstance(resp.json(), list)

    async def test_no_matches_returns_empty_list(self, test_client, db_session):
        user = await seed_user(db_session)
        resp = await test_client.get(
            f"/users/{user.id}/matches/relevant", params={"min_score": 0.0}
        )
        assert resp.json() == []

    async def test_relevant_returns_matches_at_or_above_threshold(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt1 = await seed_apartment(db_session)
        apt2 = await seed_apartment(db_session)
        apt3 = await seed_apartment(db_session)

        await seed_match(db_session, user.id, apt1.id, match_score=0.9)
        await seed_match(db_session, user.id, apt2.id, match_score=0.5)
        await seed_match(db_session, user.id, apt3.id, match_score=0.1)

        resp = await test_client.get(
            f"/users/{user.id}/matches/relevant", params={"min_score": 0.6}
        )
        assert resp.status_code == 200
        scores = [m["match_score"] for m in resp.json()]
        assert all(s >= 0.6 for s in scores)
        assert len(scores) == 1

    async def test_relevant_excludes_matches_below_threshold(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        await seed_match(db_session, user.id, apt.id, match_score=0.3)

        resp = await test_client.get(
            f"/users/{user.id}/matches/relevant", params={"min_score": 0.8}
        )
        assert resp.json() == []

    async def test_relevant_matches_sorted_descending_by_score(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt1 = await seed_apartment(db_session)
        apt2 = await seed_apartment(db_session)
        apt3 = await seed_apartment(db_session)

        await seed_match(db_session, user.id, apt1.id, match_score=0.6)
        await seed_match(db_session, user.id, apt2.id, match_score=0.95)
        await seed_match(db_session, user.id, apt3.id, match_score=0.75)

        resp = await test_client.get(
            f"/users/{user.id}/matches/relevant", params={"min_score": 0.0}
        )
        scores = [m["match_score"] for m in resp.json()]
        assert scores == sorted(scores, reverse=True)

    async def test_default_min_score_filters_low_scores(
        self, test_client, db_session
    ):
        """Default min_score query param is 0.8; scores below that must be absent."""
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        await seed_match(db_session, user.id, apt.id, match_score=0.5)

        resp = await test_client.get(f"/users/{user.id}/matches/relevant")
        assert resp.json() == []

    async def test_min_score_zero_returns_all_user_matches(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt1 = await seed_apartment(db_session)
        apt2 = await seed_apartment(db_session)
        await seed_match(db_session, user.id, apt1.id, match_score=0.1)
        await seed_match(db_session, user.id, apt2.id, match_score=0.99)

        resp = await test_client.get(
            f"/users/{user.id}/matches/relevant", params={"min_score": 0.0}
        )
        assert len(resp.json()) == 2

    async def test_relevant_returns_match_fields(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        await seed_match(db_session, user.id, apt.id, match_score=0.9)

        resp = await test_client.get(
            f"/users/{user.id}/matches/relevant", params={"min_score": 0.0}
        )
        match_data = resp.json()[0]
        for field in ("id", "user_id", "apartment_id", "status", "match_score"):
            assert field in match_data
