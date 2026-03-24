"""
DB Writer
=========
Async version — uses your app's AsyncSession (asyncpg) directly.

Usage
-----
    from app.parsers.db_writer import ListingWriter

    async with async_session_factory() as session:
        writer = ListingWriter(session)
        created, skipped = await writer.upsert_listings(listings)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Apartment, NeighborInfo

if TYPE_CHECKING:
    from parsers.streeteasy_email import ParsedListing

logger = logging.getLogger(__name__)


class ListingWriter:
    """
    Persists ParsedListing instances to the database using AsyncSession.

    Duplicate detection is on streeteasy_id (unique per listing).
    Falls back to (name, price) for any row that pre-dates the streeteasy_id
    column being added.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_listings(
        self, listings: list[ParsedListing]
    ) -> tuple[int, int]:
        """Upsert a list of ParsedListings. Returns (created, skipped)."""
        created = 0
        skipped = 0

        for listing in listings:
            try:
                neighbor = await self._get_or_create_neighbor(listing)

                # Primary duplicate check: streeteasy_id (canonical, stable).
                existing = None
                if listing.streeteasy_id:
                    result = await self._session.execute(
                        select(Apartment).filter_by(
                            streeteasy_id=listing.streeteasy_id,
                        )
                    )
                    existing = result.scalar_one_or_none()

                # Fallback: (name, price) for rows without a streeteasy_id.
                if existing is None:
                    result = await self._session.execute(
                        select(Apartment).filter_by(
                            name=listing.name,
                            price=listing.price,
                        )
                    )
                    existing = result.scalar_one_or_none()

                if existing:
                    logger.debug(
                        "Skipping duplicate: %s @ $%d (streeteasy_id=%s)",
                        listing.name,
                        listing.price,
                        listing.streeteasy_id,
                    )
                    skipped += 1
                    continue

                # Parse move_in_date string → date object if needed.
                move_in = _parse_date(listing.move_in_date)

                host_phone, host_email = _split_contact(listing.host_contact)

                apt = Apartment(
                    streeteasy_id=listing.streeteasy_id,
                    name=listing.name,
                    bedroom_type=listing.bedroom_type,
                    price=listing.price,
                    neighbor_id=neighbor.id if neighbor else None,
                    host_phone=host_phone,
                    host_email=host_email,
                    latitude=listing.latitude,
                    longitude=listing.longitude,
                    move_in_date=move_in,
                    lease_length_months=listing.lease_length_months,
                    laundry=_to_pg_array(listing.laundry),
                    parking=_to_pg_array(listing.parking),
                    amenities=_to_pg_array(listing.amenities),
                    pets=listing.pets            or False,
                    images=listing.images        or [],
                    image_labels=listing.image_labels or [],
                )
                self._session.add(apt)
                created += 1
                logger.info(
                    "Queued: %s (%s) $%d — %s",
                    listing.name,
                    listing.bedroom_type,
                    listing.price,
                    listing.neighborhood_name,
                )

            except Exception as exc:
                logger.error(
                    "Failed to upsert '%s': %s", listing.name, exc, exc_info=True
                )

        await self._session.commit()
        logger.info("DB commit: created=%d skipped=%d", created, skipped)
        return created, skipped

    async def _get_or_create_neighbor(
        self, listing: ParsedListing
    ) -> NeighborInfo | None:
        name = listing.neighborhood_name
        if not name:
            return None

        result = await self._session.execute(
            select(NeighborInfo).filter_by(name=name)
        )
        neighbor = result.scalar_one_or_none()
        if neighbor:
            return neighbor

        # Use Claude-generated description if available, else a stub.
        # NOTE: the stub is stored in NeighborInfo.description only — never
        # in .name — so it won't contaminate future neighborhood lookups.
        description = (
            getattr(listing, "_claude_neighborhood_description", None)
            or f"{name} neighborhood in NYC. Description to be enriched by AI agent."
        )

        logger.info("Creating NeighborInfo stub: %s", name)
        neighbor = NeighborInfo(name=name, description=description)
        self._session.add(neighbor)
        await self._session.flush()  # get the generated ID before commit
        return neighbor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_contact(value: str | None) -> tuple[str | None, str | None]:
    """
    Split a raw host_contact string into (phone, email).
    The scraper provides strings like "Brokerage Name (address)" or
    a phone number like "+1 212-555-1234". Email addresses are rare
    in StreetEasy data but handled here for completeness.
    """
    if not value:
        return None, None
    import re as _re
    email_match = _re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", value)
    phone_match = _re.search(r"[\+\d][\d\s\-().]{6,}", value)
    email = email_match.group(0) if email_match else None
    phone = phone_match.group(0).strip() if phone_match else None
    return phone, email


def _to_pg_array(values) -> list:
    """
    Return a clean list for SQLAlchemy → asyncpg → PostgreSQL array binding.

    asyncpg maps Python list[str] to a TEXT[] column natively, but it only
    adds double-quotes around elements that contain spaces, commas, braces, or
    backslashes.  Passing the list directly (rather than a hand-built
    '{...}' string literal) ensures correct quoting every time.
    """
    return list(values) if values else []


def _parse_date(value: str | None):
    """
    Convert a move_in_date string to a datetime.date.
    Accepts ISO format (2026-03-21) or returns None for anything else.
    """
    if not value:
        return None
    from datetime import date
    # Already a date object.
    if isinstance(value, date):
        return value
    import re
    # ISO date: "2026-03-21"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(value))
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # Anything else (e.g. "Available now", "now") → None;
    # Claude should have normalised it already but be defensive.
    logger.debug("Could not parse move_in_date %r as ISO date — storing None", value)
    return None