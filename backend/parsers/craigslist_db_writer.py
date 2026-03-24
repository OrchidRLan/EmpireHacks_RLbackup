"""
Craigslist DB Writer
====================
Async version — uses your app's AsyncSession (asyncpg) directly.

Deduplication strategy (in order):
  1. craigslist_id  — 10-digit post ID extracted from the listing URL.
                      Most reliable; Craigslist reuses IDs across re-posts
                      only when the seller explicitly deletes and re-posts.
  2. (name, price)  — fallback for any row that pre-dates the craigslist_id
                      column, or where scraping failed to retrieve the URL.

Usage
-----
    from app.parsers.craigslist_writer import CraigslistWriter

    async with async_session_factory() as session:
        writer = CraigslistWriter(session)
        created, skipped = await writer.upsert_listings(listings)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Apartment, NeighborInfo

if TYPE_CHECKING:
    from app.parsers.craigslist_email import CraigslistListing

logger = logging.getLogger(__name__)


class CraigslistWriter:
    """
    Persists CraigslistListing instances to the Apartment table.

    The Apartment model is shared between StreetEasy and Craigslist rows.
    Craigslist rows are identified by the `craigslist_id` column (which must
    exist on the model — add a migration if needed):

        craigslist_id  VARCHAR  UNIQUE  NULL
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_listings(
        self, listings: list[CraigslistListing]
    ) -> tuple[int, int]:
        """Upsert a list of CraigslistListings. Returns (created, skipped)."""
        created = 0
        skipped = 0

        for listing in listings:
            try:
                neighbor = await self._get_or_create_neighbor(listing)

                # ── Primary dedup: craigslist_id ──────────────────────────
                existing = None
                if listing.craigslist_id:
                    result = await self._session.execute(
                        select(Apartment).filter_by(
                            craigslist_id=listing.craigslist_id
                        )
                    )
                    existing = result.scalar_one_or_none()

                # ── Fallback dedup: (name, price) ─────────────────────────
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
                        "Skipping duplicate: %s @ $%d (craigslist_id=%s)",
                        listing.name, listing.price, listing.craigslist_id,
                    )
                    skipped += 1
                    continue

                move_in = _parse_date(listing.move_in_date)

                host_phone, host_email = _split_contact(listing.host_contact)

                apt = Apartment(
                    craigslist_id      = listing.craigslist_id,
                    name               = listing.name,
                    bedroom_type       = listing.bedroom_type,
                    price              = listing.price,
                    neighbor_id        = neighbor.id if neighbor else None,
                    host_phone         = host_phone,
                    host_email         = host_email,
                    latitude           = listing.latitude,
                    longitude          = listing.longitude,
                    move_in_date       = move_in,
                    lease_length_months = listing.lease_length_months,
                    laundry            = _to_pg_array(listing.laundry),
                    parking            = _to_pg_array(listing.parking),
                    amenities          = _to_pg_array(listing.amenities),
                    pets               = listing.pets or False,
                    images             = listing.images or [],
                    image_labels       = listing.image_labels or [],
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
        logger.info("DB commit (CL): created=%d skipped=%d", created, skipped)
        return created, skipped

    async def _get_or_create_neighbor(
        self, listing: CraigslistListing
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

        description = (
            getattr(listing, "_claude_neighborhood_description", None)
            or f"{name} neighborhood in NYC. Description to be enriched by AI agent."
        )

        logger.info("Creating NeighborInfo stub (CL): %s", name)
        neighbor = NeighborInfo(name=name, description=description)
        self._session.add(neighbor)
        await self._session.flush()
        return neighbor


# ---------------------------------------------------------------------------
# Helpers (mirror of streeteasy_db_writer.py helpers — kept local to avoid circular imports)
# ---------------------------------------------------------------------------

def _split_contact(value: str | None) -> tuple[str | None, str | None]:
    """Split a raw contact string into (phone, email)."""
    if not value:
        return None, None
    import re as _re
    email_match = _re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", value)
    phone_match = _re.search(r"[\+\d][\d\s\-().]{6,}", value)
    email = email_match.group(0) if email_match else None
    phone = phone_match.group(0).strip() if phone_match else None
    return phone, email


def _to_pg_array(values) -> list:
    return list(values) if values else []


def _parse_date(value: str | None):
    if not value:
        return None
    from datetime import date
    if isinstance(value, date):
        return value
    import re
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(value))
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    logger.debug("Could not parse move_in_date %r — storing None", value)
    return None