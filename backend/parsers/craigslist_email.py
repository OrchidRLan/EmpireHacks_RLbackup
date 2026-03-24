"""
Craigslist Email Parser
=======================
Parses Craigslist saved-search alert emails fetched via the Gmail API
and converts them into CraigslistListing records ready for scraping
and upsert into the database.

Email format (from alerts@alerts.craigslist.org):
    Each listing block is separated by a line of "=" characters and contains:

        $<price> - <Nbr>br - [<sqft>ft2 -] <title>
        https://newyork.craigslist.org/<area>/apa/d/<slug>/<post_id>.html
        (<neighborhood>)             ← optional; not always present

    The URL is repeated twice per block (we take the first occurrence).
    Bedroom count comes from the "Nbr>br" token; "Studio" listings omit it
    entirely (shown as blank between the price and the title).

Usage
-----
    from app.parsers.craigslist_email import CraigslistEmailParser

    parser = CraigslistEmailParser()

    # From a raw Gmail message dict (as returned by Gmail API)
    listings = parser.parse_gmail_message(gmail_message)

    # From a raw .eml file (for testing / offline use)
    listings = parser.parse_eml_file("path/to/message.eml")

Each call returns a list of CraigslistListing dataclass instances.
The listing's `name` field is the *title* from the email at this stage —
the real street address is populated later by CraigslistScraper.enrich().
"""

from __future__ import annotations

import base64
import email
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from email import policy
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class CraigslistListing:
    """
    Flat representation of one apartment listing extracted from a
    Craigslist alert email.  Maps onto the same Apartment / NeighborInfo
    schema as ParsedListing; the scraper fills in the richer fields later.
    """
    # Core identity
    craigslist_id: str          # 10-digit post ID from the listing URL
    craigslist_url: str         # canonical listing URL (without query params)

    # Apartment fields
    name: str                   # listing title from email; replaced by real
                                # address after scraping (kept as fallback)
    bedroom_type: str           # "Studio", "1 Bed", "2 Bed", …
    price: int                  # monthly rent in USD

    # Neighbourhood (parsed from the parenthetical line, may be empty)
    neighborhood_name: str      # e.g. "Clinton Hill"; empty string if absent

    # Optional fields parsed from the email subject line
    square_feet: Optional[int] = None

    # Optional fields populated by the scraper
    bathrooms: Optional[int] = None
    host_contact: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    move_in_date: Optional[str] = None
    lease_length_months: Optional[int] = None
    laundry: list[str] = field(default_factory=list)
    parking: list[str] = field(default_factory=list)
    amenities: list[str] = field(default_factory=list)
    pets: bool = False
    images: list[str] = field(default_factory=list)
    image_labels: list[str] = field(default_factory=list)
    description: Optional[str] = None

    # Email envelope metadata
    email_subject: str = ""
    email_date: Optional[datetime] = None
    email_message_id: str = ""

    # Internal: Claude-generated neighbourhood description (set by scraper,
    # consumed by ListingWriter to populate NeighborInfo.description)
    _claude_neighborhood_description: Optional[str] = field(
        default=None, repr=False
    )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class CraigslistEmailParser:
    """
    Parses Craigslist saved-search alert emails sent by
    alerts@alerts.craigslist.org.

    Email plain-text structure
    --------------------------
    Listings are separated by a horizontal rule of "=" characters (60 of them,
    encoded as =3D in quoted-printable, decoded by the email library to "=").
    Each block looks like:

        $3,050 - 1br -  Sundrenched One Bed in Clinton Hill
        https://newyork.craigslist.org/brk/apa/d/brooklyn-sundrenched.../7922802952.html
        (Clinton Hill)


        https://newyork.craigslist.org/brk/apa/d/brooklyn-sundrenched.../7922802952.html

    Notes:
    - The URL appears twice; we take the first occurrence.
    - "br" count token may be absent for studios (shows as "-  Title").
    - sqft token ("925ft2") is optional and appears before the title.
    - The neighbourhood line in parentheses is optional.
    - Emoji / non-ASCII in titles are decoded by the email library.
    """

    SENDER_DOMAINS = {"craigslist.org", "alerts.craigslist.org"}

    # Separator between listing blocks: 60 "=" characters
    _SEPARATOR_RE = re.compile(r"={50,}", re.MULTILINE)

    # Header line:  $price - [Nbr>br] - [sqftft2 -] title
    # Groups: (price_str, br_count_or_None, sqft_or_None, title)
    _HEADER_RE = re.compile(
        r"^\$?([\d,]+)\s*-\s*"          # price
        r"(?:(\d+)br\s*-\s*)?"          # optional "Nbr>br -"
        r"(?:([\d,]+)ft2\s*-\s*)?"      # optional "sqftft2 -"
        r"\s*(.+)$",                    # title (rest of line, may start with spaces)
        re.IGNORECASE,
    )

    # Craigslist listing URL — captures the 10-digit post ID
    _URL_RE = re.compile(
        r"https?://\w+\.craigslist\.org/[^/]+/[^/]+/d/[^/]+/(\d{7,12})\.html",
        re.IGNORECASE,
    )

    # Neighbourhood — a parenthetical on its own line: "(Clinton Hill)"
    _NEIGHBORHOOD_RE = re.compile(r"^\((.+)\)\s*$")

    # ---------------------------------------------------------------------------

    def parse_gmail_message(self, gmail_message: dict) -> list[CraigslistListing]:
        """
        Parse a message dict as returned by the Gmail API
        (users.messages.get with format='raw').
        """
        raw_bytes = base64.urlsafe_b64decode(
            gmail_message.get("raw", "") + "=="
        )
        gmail_id = gmail_message.get("id", "")
        return self._parse_bytes(raw_bytes, gmail_id=gmail_id)

    def parse_eml_file(self, path: str) -> list[CraigslistListing]:
        """Parse a .eml file from disk (useful for local testing)."""
        with open(path, "rb") as fh:
            raw_bytes = fh.read()
        return self._parse_bytes(raw_bytes)

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _parse_bytes(
        self, raw_bytes: bytes, gmail_id: str = ""
    ) -> list[CraigslistListing]:
        msg = email.message_from_bytes(raw_bytes, policy=policy.default)

        if not self._is_craigslist_email(msg):
            logger.debug("Skipping non-Craigslist email (id=%s)", gmail_id)
            return []

        subject    = str(msg.get("subject", ""))
        date       = _parse_date(msg.get("date"))
        message_id = str(msg.get("message-id", gmail_id))

        plain_text = self._get_plain_text(msg)
        if not plain_text:
            logger.warning("No plain-text part in Craigslist message id=%s", message_id)
            return []

        listings = self._extract_listings(plain_text)

        for listing in listings:
            listing.email_subject   = subject
            listing.email_date      = date
            listing.email_message_id = message_id

        logger.info("Parsed %d listing(s) from Craigslist email '%s'", len(listings), subject)
        return listings

    # ---- Validation ----

    def _is_craigslist_email(self, msg: email.message.Message) -> bool:
        sender   = str(msg.get("from",     ""))
        reply_to = str(msg.get("reply-to", ""))
        return any(
            domain in sender or domain in reply_to
            for domain in self.SENDER_DOMAINS
        )

    # ---- Body extraction ----

    def _get_plain_text(self, msg: email.message.Message) -> str:
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_content()
        # HTML fallback
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                soup = BeautifulSoup(part.get_content(), "html.parser")
                return soup.get_text(separator="\n")
        return ""

    # ---- Listing extraction ----

    def _extract_listings(self, plain_text: str) -> list[CraigslistListing]:
        """
        Split the email body on the '===…===' separator and parse each block.
        The first element before the first separator is the email header / preamble
        and is discarded.
        """
        blocks = self._SEPARATOR_RE.split(plain_text)
        if len(blocks) < 2:
            logger.debug("No listing separators found in Craigslist plain text.")
            return []

        listings: list[CraigslistListing] = []
        for raw_block in blocks[1:]:   # skip preamble
            try:
                listing = self._parse_block(raw_block)
                if listing:
                    listings.append(listing)
            except Exception as exc:   # noqa: BLE001
                logger.warning("Failed to parse Craigslist block: %s", exc, exc_info=True)

        return listings

    def _parse_block(self, block: str) -> Optional[CraigslistListing]:
        """
        Parse one listing block (text after a separator line).

        Expected lines (after stripping):
            Line 0: "$price - [Nbr>br -] [sqftft2 -] title"
            Line 1: listing URL  (first occurrence)
            Line 2: "(neighborhood)"  — optional
            ...     (URL repeated, blank lines — ignored)
        """
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            return None

        # ---- Header line (price / beds / title) ----
        header_match = self._HEADER_RE.match(lines[0])
        if not header_match:
            logger.debug("No price/title header found in block starting: %r", lines[0][:80])
            return None

        price_str, br_count, sqft_str, raw_title = header_match.groups()

        price = int(price_str.replace(",", ""))
        title = _clean_title(raw_title)

        if br_count is not None:
            bedroom_type = f"{br_count} Bed"
        else:
            # No br token → Studio (Craigslist omits it for studios)
            bedroom_type = "Studio"

        square_feet: Optional[int] = None
        if sqft_str:
            try:
                square_feet = int(sqft_str.replace(",", ""))
            except ValueError:
                pass

        # ---- URL (first occurrence wins) ----
        craigslist_url: Optional[str] = None
        craigslist_id:  Optional[str] = None
        for line in lines[1:]:
            url_match = self._URL_RE.search(line)
            if url_match:
                craigslist_id  = url_match.group(1)
                # Strip any query-string from the URL for a canonical form.
                craigslist_url = url_match.group(0).split("?")[0]
                break

        if not craigslist_id:
            logger.debug("No Craigslist post URL found in block: %r", lines)
            return None

        # ---- Neighbourhood (optional parenthetical line) ----
        neighborhood = ""
        for line in lines[1:]:
            nb_match = self._NEIGHBORHOOD_RE.match(line)
            if nb_match:
                neighborhood = nb_match.group(1).strip().title()
                break

        return CraigslistListing(
            craigslist_id   = craigslist_id,
            craigslist_url  = craigslist_url,
            name            = title,        # real address filled in by scraper
            bedroom_type    = bedroom_type,
            price           = price,
            neighborhood_name = neighborhood,
            square_feet     = square_feet,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_title(raw: str) -> str:
    """
    Strip leading/trailing whitespace and collapse internal whitespace runs
    that result from decoded emoji sequences, e.g. "☀️ One Bed 🥂 In The…"
    becomes "☀️ One Bed 🥂 In The…".
    """
    return re.sub(r"\s{2,}", " ", raw).strip()


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except Exception:
        return None