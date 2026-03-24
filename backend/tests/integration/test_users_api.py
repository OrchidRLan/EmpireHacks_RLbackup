"""Integration tests for the /users REST endpoints.

Exercises POST /users, GET /users/{id}, PATCH /users/{id},
and DELETE /users/{id} against the real FastAPI app wired to an
in-memory SQLite database via the test_client fixture.
"""

import pytest
from httpx import AsyncClient


# ── Fixtures / helpers ────────────────────────────────────────────────────────

USER_PAYLOAD = {"name": "Alice Tester", "phone": "+15550001111"}


async def _create_user(client: AsyncClient, payload: dict | None = None) -> dict:
    """POST /users and return the JSON response body."""
    resp = await client.post("/users/", json=payload or USER_PAYLOAD)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── POST /users ───────────────────────────────────────────────────────────────

class TestCreateUser:
    async def test_creates_user_returns_201(self, test_client):
        resp = await test_client.post("/users/", json=USER_PAYLOAD)
        assert resp.status_code == 201

    async def test_response_contains_id(self, test_client):
        data = await _create_user(test_client)
        assert "id" in data
        assert isinstance(data["id"], str)
        assert len(data["id"]) > 0

    async def test_response_mirrors_input_fields(self, test_client):
        data = await _create_user(test_client)
        assert data["name"] == USER_PAYLOAD["name"]
        assert data["phone"] == USER_PAYLOAD["phone"]

    async def test_response_contains_created_at(self, test_client):
        data = await _create_user(test_client)
        assert "created_at" in data

    async def test_missing_name_returns_422(self, test_client):
        resp = await test_client.post("/users/", json={"phone": "+15550001111"})
        assert resp.status_code == 422

    async def test_missing_phone_returns_422(self, test_client):
        resp = await test_client.post("/users/", json={"name": "Alice"})
        assert resp.status_code == 422

    async def test_empty_body_returns_422(self, test_client):
        resp = await test_client.post("/users/", json={})
        assert resp.status_code == 422

    async def test_two_users_get_different_ids(self, test_client):
        u1 = await _create_user(test_client, {"name": "Alice", "phone": "111"})
        u2 = await _create_user(test_client, {"name": "Bob", "phone": "222"})
        assert u1["id"] != u2["id"]


# ── GET /users/{user_id} ──────────────────────────────────────────────────────

class TestGetUser:
    async def test_returns_existing_user(self, test_client):
        created = await _create_user(test_client)
        resp = await test_client.get(f"/users/{created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]
        assert data["name"] == created["name"]
        assert data["phone"] == created["phone"]

    async def test_unknown_id_returns_404(self, test_client):
        resp = await test_client.get("/users/nonexistent-uuid")
        assert resp.status_code == 404

    async def test_404_response_has_detail(self, test_client):
        resp = await test_client.get("/users/nonexistent-uuid")
        assert "detail" in resp.json()


# ── GET /users/ (list) ────────────────────────────────────────────────────────

class TestListUsers:
    async def test_list_returns_200(self, test_client):
        resp = await test_client.get("/users/")
        assert resp.status_code == 200

    async def test_list_is_array(self, test_client):
        resp = await test_client.get("/users/")
        assert isinstance(resp.json(), list)

    async def test_created_user_appears_in_list(self, test_client):
        created = await _create_user(test_client)
        resp = await test_client.get("/users/")
        ids = [u["id"] for u in resp.json()]
        assert created["id"] in ids


# ── PATCH /users/{user_id} ────────────────────────────────────────────────────

class TestUpdateUser:
    async def test_update_name(self, test_client):
        created = await _create_user(test_client)
        resp = await test_client.patch(
            f"/users/{created['id']}", json={"name": "Bob Updated"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Bob Updated"

    async def test_update_phone(self, test_client):
        created = await _create_user(test_client)
        resp = await test_client.patch(
            f"/users/{created['id']}", json={"phone": "+19999999999"}
        )
        assert resp.status_code == 200
        assert resp.json()["phone"] == "+19999999999"

    async def test_update_unknown_id_returns_404(self, test_client):
        resp = await test_client.patch("/users/bad-id", json={"name": "X"})
        assert resp.status_code == 404


# ── DELETE /users/{user_id} ───────────────────────────────────────────────────

class TestDeleteUser:
    async def test_delete_existing_user_returns_204(self, test_client):
        created = await _create_user(test_client)
        resp = await test_client.delete(f"/users/{created['id']}")
        assert resp.status_code == 204

    async def test_deleted_user_no_longer_fetchable(self, test_client):
        created = await _create_user(test_client)
        await test_client.delete(f"/users/{created['id']}")
        resp = await test_client.get(f"/users/{created['id']}")
        assert resp.status_code == 404

    async def test_delete_unknown_id_returns_404(self, test_client):
        resp = await test_client.delete("/users/nonexistent-id")
        assert resp.status_code == 404

    async def test_delete_removes_user_from_list(self, test_client):
        created = await _create_user(test_client)
        await test_client.delete(f"/users/{created['id']}")
        resp = await test_client.get("/users/")
        ids = [u["id"] for u in resp.json()]
        assert created["id"] not in ids
