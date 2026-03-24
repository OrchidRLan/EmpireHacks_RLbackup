"""GET /api/v1/listings, GET /api/v1/listings/:id, POST /api/v1/listings/:id/react

A "listing" is an Apartment enriched with its Match data for the current user.
"""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.apartment import Apartment
from app.models.match import Match
from app.models.preferences import SubjectivePreferences
from app.models.user import User
from app.routers.v1.deps import get_current_user
from app.services.matching import recalculate_all_match_scores, run_objective_filter

router = APIRouter(prefix="/listings", tags=["v1-listings"])


# ---------------------------------------------------------------------------
# Out schemas
# ---------------------------------------------------------------------------


class ListingOut(BaseModel):
    id: str
    title: str
    address: str
    neighborhood: str | None
    price: int
    bedrooms: str
    pets: bool
    parking: list[str]
    laundry: list[str]
    images: list[str]
    imageLabels: list[str]
    lat: float | None
    lng: float | None
    availableFrom: str | None
    leaseLength: int | None
    matchScore: float | None
    matchReasoning: str | None
    negotiationStatus: str | None
    commuteMinutes: int | None
    matchId: str | None
    matchType: str  # "perfect" | "flex"
    status: str  # "available" | "pending" | "unavailable"
    hostEmail: str | None
    hostPhone: str | None


class PaginatedListings(BaseModel):
    items: list[ListingOut]
    total: int
    page: int
    pageSize: int


# ---------------------------------------------------------------------------
# Mapping helper: Match.status → NegotiationStatus expected by frontend
# ---------------------------------------------------------------------------

_STATUS_MAP = {
    "not_started": "pending",
    "in_progress": "negotiating",
    "completed": "accepted",
}


def _to_negotiation_status(match_status: str) -> str:
    return _STATUS_MAP.get(match_status, match_status)


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------


def _to_match_type(score: float | None) -> str:
    """Derive matchType from the raw DB score (0.0-1.0): >= 0.22 is 'perfect', else 'flex'.

    Threshold is calibrated to the current scoring model where image labels are sparse
    (max achievable score ~0.30 without AI image analysis). Top-quartile listings are 'perfect'.
    """
    if score is None:
        return "flex"
    return "perfect" if score >= 0.22 else "flex"


def _build_listing(apt: Apartment, match: Match | None) -> ListingOut:
    # match_score is stored as 0.0-1.0; the frontend adapter handles the *100 conversion.
    score = match.match_score if match else None
    return ListingOut(
        id=apt.id,
        title=apt.name,
        address=f"{apt.neighborhood.name}, NYC" if apt.neighborhood else apt.name,
        neighborhood=apt.neighborhood.name if apt.neighborhood else None,
        price=apt.price,
        bedrooms=apt.bedroom_type,
        pets=apt.pets,
        parking=apt.parking or [],
        laundry=apt.laundry or [],
        images=apt.images or [],
        imageLabels=apt.image_labels or [],
        lat=apt.latitude,
        lng=apt.longitude,
        availableFrom=apt.move_in_date.isoformat() if apt.move_in_date else None,
        leaseLength=apt.lease_length_months,
        matchScore=score,
        matchReasoning=match.match_reasoning if match else None,
        negotiationStatus=_to_negotiation_status(match.status) if match else None,
        commuteMinutes=match.commute_minutes if match else None,
        matchId=match.id if match else None,
        matchType=_to_match_type(score),
        status="available",  # Apartment model has no status column; default to available
        hostEmail=apt.host_email,
        hostPhone=apt.host_phone,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedListings)
async def list_listings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    # Filtering
    negotiationStatus: Optional[str] = Query(default=None),
    matchType: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    minPrice: Optional[int] = Query(default=None),
    maxPrice: Optional[int] = Query(default=None),
    minScore: Optional[float] = Query(default=None),
    # Sorting
    sortBy: Optional[str] = Query(default=None),  # "price" | "matchScore" | "commuteMinutes"
    sortOrder: Optional[str] = Query(default="desc"),  # "asc" | "desc"
) -> PaginatedListings:
    uid = current_user.id

    # Build apartment query with optional price filters
    apt_query = select(Apartment).options(selectinload(Apartment.neighborhood))
    if minPrice is not None:
        apt_query = apt_query.where(Apartment.price >= minPrice)
    if maxPrice is not None:
        apt_query = apt_query.where(Apartment.price <= maxPrice)

    # Apply price sort at DB level if requested
    if sortBy == "price":
        if sortOrder == "asc":
            apt_query = apt_query.order_by(Apartment.price.asc())
        else:
            apt_query = apt_query.order_by(Apartment.price.desc())

    apts_result = await db.execute(apt_query)
    all_apts = apts_result.scalars().all()

    # Fetch this user's matches for all apartments in one query
    all_apt_ids = [a.id for a in all_apts]
    matches_result = await db.execute(
        select(Match).where(Match.user_id == uid, Match.apartment_id.in_(all_apt_ids))
    )
    match_by_apt: dict[str, Match] = {m.apartment_id: m for m in matches_result.scalars().all()}

    # Build listing objects
    items_all = [_build_listing(apt, match_by_apt.get(apt.id)) for apt in all_apts]

    # NOTE: Post-fetch in-memory filtering. This works for the hackathon demo
    # dataset but will not scale to large apartment counts. To scale, push
    # negotiationStatus/matchType/minScore filters into the SQL query via JOINs
    # on the Match table.
    if negotiationStatus:
        items_all = [i for i in items_all if i.negotiationStatus == negotiationStatus]
    if matchType:
        items_all = [i for i in items_all if i.matchType == matchType]
    if status:
        items_all = [i for i in items_all if i.status == status]
    if minScore is not None:
        items_all = [i for i in items_all if (i.matchScore or 0) >= minScore]

    # Apply sorting for fields not handled at DB level
    if sortBy == "matchScore":
        reverse = sortOrder != "asc"
        items_all.sort(key=lambda x: x.matchScore or 0, reverse=reverse)
    elif sortBy == "commuteMinutes":
        reverse = sortOrder == "desc"
        items_all.sort(key=lambda x: x.commuteMinutes or 9999, reverse=reverse)

    total = len(items_all)
    offset = (page - 1) * pageSize
    paged = items_all[offset : offset + pageSize]

    return PaginatedListings(items=paged, total=total, page=page, pageSize=pageSize)


# ---------------------------------------------------------------------------
# Run filter / scoring  (must be registered BEFORE /{listing_id} to avoid
# FastAPI matching "run-filter" as a listing_id with GET-only 405 response)
# ---------------------------------------------------------------------------


class FilterResponse(BaseModel):
    matched: int
    message: str


class ScoringResponse(BaseModel):
    scored: int
    message: str


@router.post("/run-filter", response_model=FilterResponse)
async def run_filter(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> FilterResponse:
    """Run the objective filter for the current user and create Match rows.

    Idempotent — safe to call repeatedly. Returns the count of newly inserted
    Match rows. Returns 0 without raising if the user has no ObjectivePreferences
    yet (new user flow).
    """
    try:
        matched = await run_objective_filter(current_user.id, db)

        # Ensure SubjectivePreferences exists so scoring can run (uses price/commute weights)
        existing_subj = (
            await db.execute(
                select(SubjectivePreferences).where(SubjectivePreferences.user_id == current_user.id).limit(1)
            )
        ).scalar_one_or_none()
        if not existing_subj:
            db.add(SubjectivePreferences(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                image_labels=[],
                neighborhood_labels=[],
            ))
            await db.commit()

        # Auto-run scoring so listings immediately show match percentages
        try:
            await recalculate_all_match_scores(current_user.id, db)
        except Exception:  # noqa: BLE001
            pass  # Scoring failure is non-fatal

        return FilterResponse(matched=matched, message=f"Filter complete: {matched} new match(es) created.")
    except ValueError:
        # User has no ObjectivePreferences — treat as zero matches rather than an error.
        return FilterResponse(matched=0, message="No preferences found; skipping filter.")
    except Exception as exc:  # noqa: BLE001
        return FilterResponse(matched=0, message=f"Filter failed: {exc}")


@router.post("/run-scoring", response_model=ScoringResponse)
async def run_scoring(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ScoringResponse:
    """Recalculate match scores for all Match rows belonging to the current user.

    Returns the count of scored matches. Returns 0 without raising if the user
    has no SubjectivePreferences or ObjectivePreferences yet.
    """
    try:
        scored = await recalculate_all_match_scores(current_user.id, db)
        return ScoringResponse(scored=scored, message=f"Scoring complete: {scored} match(es) scored.")
    except ValueError as exc:
        return ScoringResponse(scored=0, message=f"Scoring skipped: {exc}")
    except Exception as exc:  # noqa: BLE001
        return ScoringResponse(scored=0, message=f"Scoring failed: {exc}")


# ---------------------------------------------------------------------------
# Single listing
# ---------------------------------------------------------------------------


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(
    listing_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ListingOut:
    apt_result = await db.execute(
        select(Apartment)
        .options(selectinload(Apartment.neighborhood))
        .where(Apartment.id == listing_id)
    )
    apt = apt_result.scalar_one_or_none()
    if not apt:
        raise HTTPException(status_code=404, detail="Listing not found")

    match = (
        await db.execute(
            select(Match).where(
                Match.user_id == current_user.id, Match.apartment_id == listing_id
            ).limit(1)
        )
    ).scalar_one_or_none()

    return _build_listing(apt, match)


# ---------------------------------------------------------------------------
# React (like / dislike → creates or updates a Match row)
# ---------------------------------------------------------------------------


class ReactRequest(BaseModel):
    action: str  # "like" | "dislike"


class ReactResponse(BaseModel):
    matchId: str | None
    action: str


@router.post("/{listing_id}/react", response_model=ReactResponse)
async def react_to_listing(
    listing_id: str,
    body: ReactRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ReactResponse:
    apt = await db.get(Apartment, listing_id)
    if not apt:
        raise HTTPException(status_code=404, detail="Listing not found")

    match = (
        await db.execute(
            select(Match).where(
                Match.user_id == current_user.id, Match.apartment_id == listing_id
            ).limit(1)
        )
    ).scalar_one_or_none()

    if body.action == "like":
        if match is None:
            match = Match(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                apartment_id=listing_id,
                status="not_started",
            )
            db.add(match)
            await db.commit()
            await db.refresh(match)
        return ReactResponse(matchId=match.id, action="like")

    elif body.action == "dislike":
        if match is not None:
            await db.delete(match)
            await db.commit()
        return ReactResponse(matchId=None, action="dislike")

    else:
        raise HTTPException(status_code=400, detail="action must be 'like' or 'dislike'")
