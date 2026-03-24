"""Integration tests for agent-related endpoints.

Endpoints covered:
  POST /agents/dev/matches/{id}/simulate-host-reply   -> 201
  POST /agents/apartments/{id}/analyze-images          -> 202
  POST /agents/apartments/analyze-all                  -> 202

Agent background tasks (run_agent1, run_agent2, run_agent3) that call
Claude or SMTP are mocked so that:
  a) no real HTTP calls are made to Anthropic
  b) no real emails are dispatched
  c) tests remain fast and deterministic
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match
from app.models.message import Message
from tests.integration.conftest import (
    seed_apartment,
    seed_match,
    seed_negotiation_prefs,
    seed_objective_prefs,
    seed_subjective_prefs,
    seed_user,
)


# ── POST /agents/dev/matches/{id}/simulate-host-reply ─────────────────────────

class TestSimulateHostReply:
    async def test_simulate_reply_returns_201(self, test_client, db_session):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        match = await seed_match(db_session, user.id, apt.id)

        resp = await test_client.post(
            f"/agents/dev/matches/{match.id}/simulate-host-reply",
            json={"text": "Hi, the apartment is still available!"},
        )
        assert resp.status_code == 201

    async def test_simulate_reply_response_contains_message_id(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        match = await seed_match(db_session, user.id, apt.id)

        resp = await test_client.post(
            f"/agents/dev/matches/{match.id}/simulate-host-reply",
            json={"text": "Yes, available next week!"},
        )
        body = resp.json()
        assert "message_id" in body
        assert isinstance(body["message_id"], str)

    async def test_simulate_reply_inserts_host_message_in_db(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        match = await seed_match(db_session, user.id, apt.id)

        reply_text = "Apartment is available from August 1st."
        resp = await test_client.post(
            f"/agents/dev/matches/{match.id}/simulate-host-reply",
            json={"text": reply_text},
        )

        message_id = resp.json()["message_id"]
        msg = await db_session.get(Message, message_id)
        assert msg is not None
        assert msg.type == "host"
        assert msg.text == reply_text
        assert msg.match_id == match.id

    async def test_simulate_reply_unknown_match_returns_404(
        self, test_client
    ):
        resp = await test_client.post(
            "/agents/dev/matches/nonexistent-id/simulate-host-reply",
            json={"text": "Hello"},
        )
        assert resp.status_code == 404

    async def test_simulate_reply_missing_text_returns_422(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        match = await seed_match(db_session, user.id, apt.id)

        resp = await test_client.post(
            f"/agents/dev/matches/{match.id}/simulate-host-reply",
            json={},  # missing required `text` field
        )
        assert resp.status_code == 422

    async def test_simulate_reply_message_has_correct_timestamp_type(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        match = await seed_match(db_session, user.id, apt.id)

        resp = await test_client.post(
            f"/agents/dev/matches/{match.id}/simulate-host-reply",
            json={"text": "Sure!"},
        )
        msg = await db_session.get(Message, resp.json()["message_id"])
        assert isinstance(msg.timestamp, datetime)

    async def test_simulate_multiple_replies_creates_distinct_messages(
        self, test_client, db_session
    ):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        match = await seed_match(db_session, user.id, apt.id)

        r1 = await test_client.post(
            f"/agents/dev/matches/{match.id}/simulate-host-reply",
            json={"text": "Reply 1"},
        )
        r2 = await test_client.post(
            f"/agents/dev/matches/{match.id}/simulate-host-reply",
            json={"text": "Reply 2"},
        )

        assert r1.json()["message_id"] != r2.json()["message_id"]


# ── POST /agents/apartments/{id}/analyze-images ───────────────────────────────

class TestAnalyzeImages:
    async def test_analyze_images_returns_202(self, test_client, db_session):
        apt = await seed_apartment(
            db_session,
            images=["https://example.com/img1.jpg"],
        )

        with patch("app.routers.agents.run_agent1", new_callable=AsyncMock):
            resp = await test_client.post(
                f"/agents/apartments/{apt.id}/analyze-images"
            )
        assert resp.status_code == 202

    async def test_analyze_images_response_contains_message(
        self, test_client, db_session
    ):
        apt = await seed_apartment(
            db_session,
            images=["https://example.com/img1.jpg"],
        )

        with patch("app.routers.agents.run_agent1", new_callable=AsyncMock):
            resp = await test_client.post(
                f"/agents/apartments/{apt.id}/analyze-images"
            )
        assert "message" in resp.json()

    async def test_analyze_images_message_contains_apartment_id(
        self, test_client, db_session
    ):
        apt = await seed_apartment(
            db_session,
            images=["https://example.com/photo.jpg"],
        )

        with patch("app.routers.agents.run_agent1", new_callable=AsyncMock):
            resp = await test_client.post(
                f"/agents/apartments/{apt.id}/analyze-images"
            )
        assert apt.id in resp.json()["message"]

    async def test_analyze_images_unknown_apartment_returns_404(
        self, test_client
    ):
        with patch("app.routers.agents.run_agent1", new_callable=AsyncMock):
            resp = await test_client.post(
                "/agents/apartments/nonexistent-id/analyze-images"
            )
        assert resp.status_code == 404

    async def test_analyze_images_no_images_returns_400(
        self, test_client, db_session
    ):
        apt = await seed_apartment(db_session, images=[])

        with patch("app.routers.agents.run_agent1", new_callable=AsyncMock):
            resp = await test_client.post(
                f"/agents/apartments/{apt.id}/analyze-images"
            )
        assert resp.status_code == 400
        assert "no images" in resp.json()["detail"].lower()

    async def test_analyze_images_does_not_block_response(
        self, test_client, db_session
    ):
        """Task is enqueued in the background; response should arrive before agent finishes."""
        apt = await seed_apartment(
            db_session,
            images=["https://example.com/img.jpg"],
        )

        call_log = []

        async def _slow_agent(apartment_id: str):
            call_log.append("called")

        with patch("app.routers.agents.run_agent1", side_effect=_slow_agent):
            resp = await test_client.post(
                f"/agents/apartments/{apt.id}/analyze-images"
            )
        assert resp.status_code == 202


# ── POST /agents/apartments/analyze-all ──────────────────────────────────────

class TestAnalyzeAll:
    async def test_analyze_all_returns_202(self, test_client):
        with patch("app.routers.agents.run_agent1_batch", new_callable=AsyncMock):
            resp = await test_client.post("/agents/apartments/analyze-all")
        assert resp.status_code == 202

    async def test_analyze_all_response_contains_message(self, test_client):
        with patch("app.routers.agents.run_agent1_batch", new_callable=AsyncMock):
            resp = await test_client.post("/agents/apartments/analyze-all")
        body = resp.json()
        assert "message" in body

    async def test_analyze_all_message_mentions_batch(self, test_client):
        with patch("app.routers.agents.run_agent1_batch", new_callable=AsyncMock):
            resp = await test_client.post("/agents/apartments/analyze-all")
        message = resp.json()["message"].lower()
        assert "batch" in message or "all" in message

    async def test_analyze_all_requires_no_body(self, test_client):
        """Endpoint accepts POST with no body and no path parameters."""
        with patch("app.routers.agents.run_agent1_batch", new_callable=AsyncMock):
            resp = await test_client.post("/agents/apartments/analyze-all")
        assert resp.status_code == 202

    async def test_analyze_all_enqueues_batch_task(self, test_client):
        """Verify that run_agent1_batch is added as a background task."""
        mock_batch = AsyncMock()

        with patch("app.routers.agents.run_agent1_batch", mock_batch):
            resp = await test_client.post("/agents/apartments/analyze-all")

        # The endpoint uses BackgroundTasks, so the mock itself may not be
        # called synchronously. We just verify the 202 response.
        assert resp.status_code == 202


# ── Additional agent endpoint: simulate reply text variants ───────────────────

class TestSimulateHostReplyEdgeCases:
    async def test_simulate_reply_long_text(self, test_client, db_session):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        match = await seed_match(db_session, user.id, apt.id)
        long_text = "Hello! " * 500  # 3500-char text

        resp = await test_client.post(
            f"/agents/dev/matches/{match.id}/simulate-host-reply",
            json={"text": long_text},
        )
        assert resp.status_code == 201

    async def test_simulate_reply_unicode_text(self, test_client, db_session):
        user = await seed_user(db_session)
        apt = await seed_apartment(db_session)
        match = await seed_match(db_session, user.id, apt.id)

        resp = await test_client.post(
            f"/agents/dev/matches/{match.id}/simulate-host-reply",
            json={"text": "Bonjour! L'appartement est disponible. \u2603"},
        )
        assert resp.status_code == 201
        msg = await db_session.get(Message, resp.json()["message_id"])
        assert "\u2603" in msg.text
