"""POST /api/v1/auth/register, /login, GET /api/v1/auth/me"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.preferences import ObjectivePreferences
from app.models.user import User
from app.routers.v1.deps import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["v1-auth"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    onboardingComplete: bool


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _onboarding_complete(user_id: str, db: AsyncSession) -> bool:
    row = (
        await db.execute(
            select(ObjectivePreferences)
            .where(ObjectivePreferences.user_id == user_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    return row is not None


def _user_out(user: User, onboarding: bool) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email or "",
        onboardingComplete=onboarding,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    existing = (
        await db.execute(select(User).where(User.email == body.email).limit(1))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        name=body.name,
        phone="",
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(token=token, user=_user_out(user, False))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    user = (
        await db.execute(select(User).where(User.email == body.email).limit(1))
    ).scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    onboarding = await _onboarding_complete(user.id, db)
    token = create_access_token(user.id)
    return AuthResponse(token=token, user=_user_out(user, onboarding))


@router.get("/me", response_model=UserOut)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    onboarding = await _onboarding_complete(current_user.id, db)
    return _user_out(current_user, onboarding)
