"""
StreetEasy Email Parser
=======================
Parses StreetEasy saved-search alert emails fetched via the Gmail API
and converts them into Apartment (+ NeighborInfo) records ready for
upsert into the database.

Supports two email templates:
  - Search alert emails  ("N Results for Queens")
      Plain-text marker: "Rental Unit in <Neighborhood>"  (mixed case)
  - Recommendation emails ("Homes You May Have Missed", "Homes for You: …")
      Plain-text marker: "RENTAL IN <NEIGHBORHOOD>"  (all-caps) or
                         "COOP IN <NEIGHBORHOOD>"    (all-caps)

Usage
-----
    from parser import StreetEasyEmailParser

    parser = StreetEasyEmailParser()

    # From a raw Gmail message dict (as returned by Gmail API)
    listings = parser.parse_gmail_message(gmail_message)

    # From a raw .eml file (for testing / offline use)
    listings = parser.parse_eml_file("path/to/message.eml")

Each call returns a list of ParsedListing dataclass instances.
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
class ParsedListing:
    """
    Flat representation of one apartment listing extracted from a
    StreetEasy alert email.  Maps directly onto the Apartment model;
    neighborhood_name is used to look-up / create NeighborInfo rows.
    """
    # Core identity
    streeteasy_id: str                   # numeric ID from the listing URL
    streeteasy_url: str

    # Apartment fields
    name: str                            # full address string, e.g. "45-15 43rd Avenue #4A"
    bedroom_type: str                    # "Studio", "1 Bed", "2 Bed", …
    price: int                           # monthly base rent in USD

    # Neighbourhood
    neighborhood_name: str               # plain string; caller resolves/creates NeighborInfo

    # Optional fields (populated when available in the email)
    bathrooms: Optional[int] = None
    host_contact: Optional[str] = None   # brokerage name + address

    # Metadata extracted from the email envelope
    email_subject: str = ""
    email_date: Optional[datetime] = None
    email_message_id: str = ""

    # Fields that are not in the email but required by the schema —
    # the caller / AI agent must fill these in later.
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


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class StreetEasyEmailParser:
    """
    Parses StreetEasy emails from noreply@email.streeteasy.com.

    Two plain-text block formats are handled:

    Alert emails (search saved-search results):
        Rental Unit in <Neighborhood>      ← mixed-case marker
        <Address>
        $<price> base rent
        ...

    Recommendation emails ("Homes You May Have Missed", "Homes for You"):
        RENTAL IN <NEIGHBORHOOD>           ← all-caps marker (also "COOP IN …")
        <Address>
        <tracking-url>
        $<price> base rent
        ...
    """

    # Sender domains used to validate that this is actually a StreetEasy email.
    SENDER_DOMAINS = {"streeteasy.com", "email.streeteasy.com"}

    # ---- Listing-block split patterns ----

    # Alert emails: "Rental Unit in <Neighborhood>"
    _ALERT_SPLIT_RE = re.compile(r"Rental Unit in ", re.MULTILINE)

    # "Homes for You" emails: "Rental in <Neighborhood>" (mixed-case, no "Unit")
    _HOMES_FOR_YOU_SPLIT_RE = re.compile(r"Rental in ", re.MULTILINE)

    # "Homes You May Have Missed" emails: all-caps "RENTAL IN …" / "COOP IN …" etc.
    _RECO_SPLIT_RE = re.compile(
        r"(?:RENTAL|COOP|CONDO|CO-OP|TOWNHOUSE|HOUSE)\s+IN\s+",
        re.MULTILINE,
    )

    # ---- Field regexes ----
    _BEDS_RE = re.compile(r"(\d+)\s*Bed|Studio", re.IGNORECASE)
    _BATHS_RE = re.compile(r"(\d+)\s*Bath", re.IGNORECASE)
    _RENTAL_URL_RE = re.compile(r"https://streeteasy\.com/rental/(\d+)")
    _PRICE_RE = re.compile(r"\$([\d,]+)\s+base rent", re.IGNORECASE)

    # ---------------------------------------------------------------------------

    def parse_gmail_message(self, gmail_message: dict) -> list[ParsedListing]:
        """
        Parse a message dict as returned by the Gmail API
        (users.messages.get with format='raw').
        """
        raw_bytes = base64.urlsafe_b64decode(
            gmail_message.get("raw", "") + "=="  # padding is idempotent
        )
        gmail_id = gmail_message.get("id", "")
        return self._parse_bytes(raw_bytes, gmail_id=gmail_id)

    def parse_eml_file(self, path: str) -> list[ParsedListing]:
        """Parse a .eml file from disk (useful for local testing)."""
        with open(path, "rb") as fh:
            raw_bytes = fh.read()
        return self._parse_bytes(raw_bytes)

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _parse_bytes(
        self, raw_bytes: bytes, gmail_id: str = ""
    ) -> list[ParsedListing]:
        msg = email.message_from_bytes(raw_bytes, policy=policy.default)

        if not self._is_streeteasy_email(msg):
            logger.debug("Skipping non-StreetEasy email (id=%s)", gmail_id)
            return []

        subject = str(msg.get("subject", ""))
        date = self._parse_date(msg.get("date"))
        message_id = str(msg.get("message-id", gmail_id))

        plain_text = self._get_plain_text(msg)
        if not plain_text:
            logger.warning("No plain-text part found in message id=%s", message_id)
            return []

        listings = self._extract_listings(plain_text)

        # Attach email metadata to every listing.
        for listing in listings:
            listing.email_subject = subject
            listing.email_date = date
            listing.email_message_id = message_id

        logger.info(
            "Parsed %d listing(s) from email '%s'", len(listings), subject
        )
        return listings

    # ---- Validation ----

    def _is_streeteasy_email(self, msg: email.message.Message) -> bool:
        """Return True for any email originating from a StreetEasy domain."""
        sender = str(msg.get("from", ""))
        reply_to = str(msg.get("reply-to", ""))
        return any(
            domain in sender or domain in reply_to
            for domain in self.SENDER_DOMAINS
        )

    # ---- Email body extraction ----

    def _get_plain_text(self, msg: email.message.Message) -> str:
        """Return the decoded plain-text body, preferring text/plain."""
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_content()
        # Fallback: strip HTML tags if no plain-text part exists.
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                soup = BeautifulSoup(part.get_content(), "html.parser")
                return soup.get_text(separator="\n")
        return ""

    # ---- Listing extraction ----

    def _extract_listings(self, plain_text: str) -> list[ParsedListing]:
        """
        Try each known template in order, returning the first non-empty result.

        Template detection order:
          1. Alert emails            — "Rental Unit in <Neighborhood>"
          2. Homes for You           — "Rental in <Neighborhood>"
          3. Homes You May Have Missed — "RENTAL IN / COOP IN <NEIGHBORHOOD>"
        """
        for split_re in (
            self._ALERT_SPLIT_RE,
            self._HOMES_FOR_YOU_SPLIT_RE,
            self._RECO_SPLIT_RE,
        ):
            blocks = split_re.split(plain_text)
            if len(blocks) >= 2:
                listings = self._parse_blocks(blocks[1:], neighborhood_line=0)
                if listings:
                    return listings

        logger.debug("No recognisable listing markers found in plain text.")
        return []

    def _parse_blocks(
        self, raw_blocks: list[str], neighborhood_line: int
    ) -> list[ParsedListing]:
        listings: list[ParsedListing] = []
        for raw_block in raw_blocks:
            try:
                listing = self._parse_listing_block(raw_block, neighborhood_line)
                if listing:
                    listings.append(listing)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to parse listing block: %s", exc, exc_info=True)
        return listings

    def _parse_listing_block(
        self, block: str, neighborhood_line: int = 0
    ) -> Optional[ParsedListing]:
        """
        Parse a single listing block that starts immediately after the
        split marker has been stripped.

        Alert format (after "Rental Unit in "):
            Sunnyside
            45-15 43rd Avenue #4A
             $2,300 base rent
             1 Bed  /  Studio
             1 Bath
             Brokerage Name (address)
            <https://streeteasy.com/rental/4995742>

        Recommendation format (after "RENTAL IN " / "COOP IN "):
            Elmhurst                            ← neighborhood (title-cased)
            41-26 73rd Street #B31A
            <https://streeteasy.com/rental/…>  ← tracking URL (skip)
            $2,100 base rent
             Studio
             1 Bath
             Brokerage Name (address)
            <https://streeteasy.com/rental/4991459>
        """
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if len(lines) < 3:
            return None

        # Line 0: neighborhood (may be all-caps in reco emails — title-case it).
        # Guard against stale DB values like "Forest Hills neighborhood in NYC.
        # Description to be enriched by AI agent." bleeding back in — take only
        # the portion before "neighborhood" or the first sentence-ending period.
        raw_neighborhood = lines[0].split("neighborhood")[0].split(".")[0].strip()
        neighborhood = raw_neighborhood.title()

        # Line 1: address
        address = lines[1]

        # Remaining lines: scan for price, beds, baths, brokerage, URL.
        price: Optional[int] = None
        bedroom_type = "Unknown"
        bathrooms: Optional[int] = None
        host_contact: Optional[str] = None
        streeteasy_url: Optional[str] = None
        streeteasy_id: Optional[str] = None

        for line in lines[2:]:
            # Price
            if price is None:
                price_match = self._PRICE_RE.search(line)
                if price_match:
                    price = int(price_match.group(1).replace(",", ""))
                    continue

            # Beds
            bed_match = self._BEDS_RE.search(line)
            if bed_match and bedroom_type == "Unknown":
                bedroom_type = "Studio" if "studio" in line.lower() else f"{bed_match.group(1)} Bed"
                continue

            # Baths
            bath_match = self._BATHS_RE.search(line)
            if bath_match and bathrooms is None:
                bathrooms = int(bath_match.group(1))
                continue

            # Listing URL  — <https://streeteasy.com/rental/4995742[?…]>
            url_match = self._RENTAL_URL_RE.search(line)
            if url_match and streeteasy_id is None:
                streeteasy_url = f"https://streeteasy.com/rental/{url_match.group(1)}"
                streeteasy_id = url_match.group(1)
                continue

            # Brokerage / agent contact — "Agency Name (address)".
            # Strip leading "Listing by " prefix if present.
            if re.search(r"\(.*\)", line) and host_contact is None:
                host_contact = re.sub(r"^Listing by\s+", "", line, flags=re.IGNORECASE)

        if not streeteasy_id:
            logger.debug("No StreetEasy listing URL found in block: %s", lines)
            return None

        if price is None:
            logger.debug("No price found in block: %s", lines)
            return None

        return ParsedListing(
            streeteasy_id=streeteasy_id,
            streeteasy_url=streeteasy_url,
            name=address,
            bedroom_type=bedroom_type,
            price=price,
            neighborhood_name=neighborhood,
            bathrooms=bathrooms,
            host_contact=host_contact,
        )

    # ---- Date parsing ----

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return None