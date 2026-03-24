from typing import Literal

from pydantic import BaseModel, Field


class RunFilterResponse(BaseModel):
    matches_created: int


class SwipeRequest(BaseModel):
    # `action` is a Literal — Pydantic v2 enforces the allowed values at
    # deserialization time; any other string raises a 422.
    # OWASP A03:2021 Injection — validate all incoming enum-like fields.
    apartment_id: str = Field(..., min_length=1)
    action: Literal["like", "dislike", "love"]


class SwipeResponse(BaseModel):
    matches_rescored: int
