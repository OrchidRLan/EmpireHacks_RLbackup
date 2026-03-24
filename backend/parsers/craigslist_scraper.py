"""
Craigslist Listing Scraper
==========================
Fetches a Craigslist apartment listing page via ZenRows and extracts every
field that maps onto the Apartment schema, then optionally calls the Claude
API to fill any remaining gaps and generate a neighbourhood description.

Architecture
------------
Craigslist listing pages are server-rendered HTML — no RSC stream, no
__NEXT_DATA__ blob.  All data is directly in the DOM:

  1. JSON-LD  — <script type="application/ld+json"> block contains
     the address (streetAddress, addressLocality, addressRegion, postalCode),
     geo (latitude, longitude), name, and description.  Most reliable.

  2. Meta tags — <meta name="geo.position"> for lat/lng (backup),
     <meta property="og:image"> for the first photo.

  3. DOM scraping  — Craigslist's own markup:
       - .postingtitletext  — full listing title
       - .attrgroup span    — attributes: bedrooms, bathrooms, sqft,
                              available date, laundry, parking, etc.
       - #postingbody       — description text
       - .gallery a / img   — photo URLs
       - .mapaddress        — address string when shown
       - .postinginfos      — post date

Claude API enrichment
---------------------
After scraping, remaining empty fields are passed to Claude:
  - available_at (move-in date) normalised to ISO
  - lease_length_months inferred from description
  - pets / laundry / parking when not found in attrgroup
  - summary: 2–3 sentence renter-facing summary
  - neighborhood_description: stored on listing for NeighborInfo

Usage
-----
    from app.parsers.craigslist_scraper import CraigslistScraper

    scraper = CraigslistScraper(
        zenrows_api_key="ZR_KEY",
        anthropic_api_key="ANT_KEY",
    )
    enriched_listing = scraper.enrich(craigslist_listing)
    enriched_batch   = scraper.enrich_batch(listings)

Environment variables
---------------------
    ZENROWS_API_KEY      ZenRows API key
    ANTHROPIC_API_KEY    Anthropic API key (optional; enables Claude enrichment)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ZenRows config
# ---------------------------------------------------------------------------

ZENROWS_BASE_URL = "https://api.zenrows.com/v1/"

# Craigslist is server-rendered HTML; JS rendering is not required and would
# waste credits.  However, Craigslist does block datacenter IPs, so we use
# a standard (non-premium) proxy.  Flip premium_proxy to "true" if you see
# 403/blocked responses in your region.
DEFAULT_ZENROWS_PARAMS: dict[str, Any] = {
    "js_render":    "false",
    "antibot":      "false",
    "premium_proxy": "false",
}

REQUEST_DELAY_SECONDS = 1   # CL is less aggressive than StreetEasy; 1s is fine


# ---------------------------------------------------------------------------
# Known Craigslist attribute labels → normalised field names
# ---------------------------------------------------------------------------

# Craigslist renders attributes as plain text spans inside .attrgroup, e.g.:
#   "3BR / 2Ba", "1400ft²", "available Jan 15", "laundry in bldg",
#   "no parking", "cats are OK - purrr", "dogs are OK - wooof"
_LAUNDRY_PATTERNS = [
    (re.compile(r"w[/\s]*d in unit",       re.I), "Washer/dryer in unit"),
    (re.compile(r"laundry in unit",        re.I), "Laundry in unit"),
    (re.compile(r"laundry in bldg",        re.I), "Laundry in building"),
    (re.compile(r"no laundry",             re.I), None),       # explicit absence
]

_PARKING_PATTERNS = [
    (re.compile(r"garage\s+parking",       re.I), "Garage parking"),
    (re.compile(r"carport",                re.I), "Carport"),
    (re.compile(r"off[- ]?street\s+park",  re.I), "Off-street parking"),
    (re.compile(r"valet\s+parking",        re.I), "Valet parking"),
    (re.compile(r"no parking",             re.I), None),
]

_PETS_ALLOW_RE   = re.compile(r"cats?\s+are\s+ok|dogs?\s+are\s+ok|pets?\s+ok|pets?\s+allowed|pets?\s+welcome",  re.I)
_PETS_NO_RE      = re.compile(r"no\s+pets?|cats?\s+not|dogs?\s+not",                                             re.I)

_AVAIL_RE        = re.compile(r"available\s+(.+)", re.I)
_BEDS_RE         = re.compile(r"(\d+)BR",           re.I)
_BATHS_RE        = re.compile(r"(\d+(?:\.\d+)?)Ba", re.I)
_SQFT_RE         = re.compile(r"([\d,]+)ft",        re.I)


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class CraigslistDetail:
    """All fields extractable from a single Craigslist listing page."""
    # Pricing / lease
    price:                Optional[int]   = None
    available_at:         Optional[str]   = None   # ISO date or human string
    lease_length_months:  Optional[int]   = None

    # Unit
    bedroom_type:         Optional[str]   = None
    bathrooms:            Optional[float] = None   # CL sometimes shows "1.5"
    square_feet:          Optional[int]   = None

    # Location
    neighborhood_name:    Optional[str]   = None
    full_address:         Optional[str]   = None
    latitude:             Optional[float] = None
    longitude:            Optional[float] = None
    zip_code:             Optional[str]   = None

    # Features
    amenities:            list[str]       = field(default_factory=list)
    laundry:              list[str]       = field(default_factory=list)
    parking:              list[str]       = field(default_factory=list)
    pets:                 bool            = False

    # Contact
    host_contact:         Optional[str]   = None

    # Media
    images:               list[str]       = field(default_factory=list)
    image_labels:         list[str]       = field(default_factory=list)

    # Description
    description:          Optional[str]   = None

    # Claude-generated
    claude_summary:       Optional[str]   = None

    # Post metadata
    posted_at:            Optional[str]   = None


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

class CraigslistScraper:
    """
    Enriches a CraigslistListing by scraping the Craigslist page via
    ZenRows and optionally calling the Claude API for gap-filling.
    """

    def __init__(
        self,
        zenrows_api_key:   Optional[str]  = None,
        anthropic_api_key: Optional[str]  = None,
        zenrows_params:    Optional[dict] = None,
        request_delay:     float          = REQUEST_DELAY_SECONDS,
        max_retries:       int            = 3,
    ) -> None:
        self._zr_key  = zenrows_api_key   or os.environ.get("ZENROWS_API_KEY",   "")
        self._ant_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not self._zr_key:
            raise ValueError(
                "ZenRows API key required. "
                "Pass zenrows_api_key= or set ZENROWS_API_KEY env var."
            )
        self._params   = {**DEFAULT_ZENROWS_PARAMS, **(zenrows_params or {})}
        self._delay    = request_delay
        self._retries  = max_retries
        self._last_req: float = 0.0

    # ---- public API --------------------------------------------------------

    def scrape(self, url: str) -> CraigslistDetail:
        """Fetch + parse a Craigslist URL. Returns a CraigslistDetail."""
        html = self._fetch_html(url)
        return self._parse_html(html)

    def enrich(self, listing) -> object:
        """Fetch the listing page, run Claude, merge fields into listing."""
        logger.info("Enriching Craigslist listing %s", listing.craigslist_url)
        try:
            html   = self._fetch_html(listing.craigslist_url)
            detail = self._parse_html(html)
            if self._ant_key:
                self._enrich_with_claude(detail, listing)
            _merge(detail, listing)
        except Exception as exc:
            logger.error(
                "Failed to enrich %s: %s", listing.craigslist_url, exc, exc_info=True
            )
        return listing

    def enrich_batch(self, listings: list) -> list:
        """Enrich a list of CraigslistListings sequentially."""
        for listing in listings:
            self.enrich(listing)
        return listings

    # ---- HTML parsing ------------------------------------------------------

    def _parse_html(self, html: str) -> CraigslistDetail:
        soup   = BeautifulSoup(html, "html.parser")
        detail = CraigslistDetail()
        self._extract_json_ld(soup, detail)     # Layer 1 — most reliable
        self._extract_meta_tags(soup, detail)   # Layer 2 — lat/lng / og:image
        self._extract_dom(soup, detail)         # Layer 3 — attrgroup, body, gallery
        logger.info(
            "CL scrape: price=$%s beds=%s lat=%s lng=%s photos=%d",
            detail.price, detail.bedroom_type,
            detail.latitude, detail.longitude, len(detail.images),
        )
        return detail

    # ---- Layer 1: JSON-LD --------------------------------------------------

    def _extract_json_ld(self, soup: BeautifulSoup, detail: CraigslistDetail) -> None:
        """
        Craigslist injects a JSON-LD <script type="application/ld+json"> block
        containing a Residence or Apartment schema with address + geo fields.

        Example fragment:
        {
          "@type": "Residence",
          "name": "Sundrenched One Bed …",
          "description": "...",
          "geo": {"latitude": 40.68, "longitude": -73.97},
          "address": {
            "streetAddress": "123 Main St",
            "addressLocality": "Brooklyn",
            "addressRegion": "NY",
            "postalCode": "11201"
          }
        }
        """
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, AttributeError):
                continue

            # Handle both a single object and a @graph array
            nodes = data if isinstance(data, list) else [data]
            for node in nodes:
                if not isinstance(node, dict):
                    continue

                # Address
                if detail.full_address is None:
                    addr = node.get("address", {})
                    if isinstance(addr, dict):
                        street = addr.get("streetAddress", "").strip()
                        city   = addr.get("addressLocality", "").strip()
                        state  = addr.get("addressRegion", "").strip()
                        zip_   = addr.get("postalCode", "").strip()
                        if street:
                            detail.full_address = (
                                f"{street}, {city}, {state} {zip_}".strip(", ")
                            )
                            detail.zip_code = zip_ or None

                # Geo
                if detail.latitude is None:
                    geo = node.get("geo", {})
                    if isinstance(geo, dict):
                        detail.latitude  = _to_float(geo.get("latitude"))
                        detail.longitude = _to_float(geo.get("longitude"))

                # Description
                if detail.description is None:
                    desc = node.get("description", "")
                    if desc:
                        detail.description = desc.strip()

    # ---- Layer 2: meta tags ------------------------------------------------

    def _extract_meta_tags(self, soup: BeautifulSoup, detail: CraigslistDetail) -> None:
        # Lat/lng: <meta name="geo.position" content="lat;lng">
        if detail.latitude is None:
            geo_pos = soup.find("meta", attrs={"name": "geo.position"})
            if geo_pos:
                parts = re.split(r"[;,\s]+", (geo_pos.get("content") or "").strip())
                if len(parts) == 2:
                    detail.latitude  = _to_float(parts[0])
                    detail.longitude = _to_float(parts[1])

        # First image from og:image
        if not detail.images:
            og_img = soup.find("meta", attrs={"property": "og:image"})
            if og_img and og_img.get("content"):
                url = og_img["content"]
                if "craigslist" in url or "cl.craigslist" in url:
                    detail.images      = [url]
                    detail.image_labels = ["photo 1"]

    # ---- Layer 3: DOM scraping ---------------------------------------------

    def _extract_dom(self, soup: BeautifulSoup, detail: CraigslistDetail) -> None:
        # ── Price ──────────────────────────────────────────────────────────
        if detail.price is None:
            price_el = soup.find(class_="price")
            if price_el:
                detail.price = _parse_price(price_el.get_text())

        # ── Title (used to confirm we scraped the right page) ───────────────
        # .postingtitletext contains "title / price / housing type"

        # ── Attribute groups (.attrgroup) ───────────────────────────────────
        # First attrgroup: "NbBR / NbBa", "sqftft²"
        # Second attrgroup: "available DATE", "laundry …", "parking …",
        #                   "cats/dogs are OK", etc.
        for ag in soup.find_all(class_="attrgroup"):
            for span in ag.find_all("span"):
                text = span.get_text(strip=True)
                if not text:
                    continue
                self._parse_attrgroup_span(text, detail)

        # ── Address (.mapaddress) ───────────────────────────────────────────
        if detail.full_address is None:
            map_addr = soup.find(class_="mapaddress")
            if map_addr:
                detail.full_address = map_addr.get_text(strip=True)

        # ── Neighbourhood ───────────────────────────────────────────────────
        # Craigslist doesn't reliably surface a neighbourhood field on the
        # page itself; we leave detail.neighborhood_name as None here so
        # _merge() keeps the value already parsed from the email.

        # ── Description (#postingbody) ──────────────────────────────────────
        if detail.description is None:
            body = soup.find(id="postingbody")
            if body:
                # Remove the "QR Code Link to This Post" block
                for qr in body.find_all(class_="print-qrcode-container"):
                    qr.decompose()
                detail.description = body.get_text(separator="\n", strip=True)

        # ── Gallery images ──────────────────────────────────────────────────
        if not detail.images:
            gallery = soup.find(id="thumbs") or soup.find(class_="gallery")
            if gallery:
                imgs: list[str] = []
                for a in gallery.find_all("a", href=True):
                    href = a["href"]
                    # Full-size images: swap thumbnail suffix for full-size
                    full = re.sub(r"_\d+x\d+\.(\w+)$", r".\1", href)
                    if full not in imgs:
                        imgs.append(full)
                if imgs:
                    detail.images      = imgs[:20]
                    detail.image_labels = [f"photo {i+1}" for i in range(len(detail.images))]

        # Fallback: grab any craigslist image URLs from <img> tags
        if not detail.images:
            imgs = []
            for img in soup.find_all("img", src=True):
                src = img["src"]
                if "images.craigslist.org" in src and src not in imgs:
                    full = re.sub(r"_\d+x\d+\.(\w+)$", r".\1", src)
                    imgs.append(full)
            if imgs:
                detail.images      = imgs[:20]
                detail.image_labels = [f"photo {i+1}" for i in range(len(detail.images))]

        # ── Contact / host ──────────────────────────────────────────────────
        if detail.host_contact is None:
            reply_btn = (
                soup.find(class_="reply-button-container")
                or soup.find(id="replylink")
            )
            if reply_btn:
                detail.host_contact = reply_btn.get_text(strip=True) or None

        # ── Post date ───────────────────────────────────────────────────────
        if detail.posted_at is None:
            time_el = soup.find("time", attrs={"class": "date timeago"})
            if time_el and time_el.get("datetime"):
                detail.posted_at = time_el["datetime"]

    def _parse_attrgroup_span(self, text: str, detail: CraigslistDetail) -> None:
        """Interpret a single attrgroup <span> and write into detail."""

        # "3BR / 2Ba" — beds + baths on one span
        br_m = _BEDS_RE.search(text)
        ba_m = _BATHS_RE.search(text)
        if br_m and detail.bedroom_type is None:
            n = int(br_m.group(1))
            detail.bedroom_type = "Studio" if n == 0 else f"{n} Bed"
        if ba_m and detail.bathrooms is None:
            detail.bathrooms = float(ba_m.group(1))

        # Square feet: "1400ft²"
        if detail.square_feet is None:
            sqft_m = _SQFT_RE.search(text)
            if sqft_m:
                detail.square_feet = _to_int(sqft_m.group(1))

        # Available date: "available Jan 15"
        if detail.available_at is None:
            av_m = _AVAIL_RE.match(text)
            if av_m:
                detail.available_at = av_m.group(1).strip()

        # Laundry
        if not detail.laundry:
            for pattern, label in _LAUNDRY_PATTERNS:
                if pattern.search(text):
                    if label:
                        detail.laundry = [label]
                    break

        # Parking
        if not detail.parking:
            for pattern, label in _PARKING_PATTERNS:
                if pattern.search(text):
                    if label:
                        detail.parking = [label]
                    break

        # Pets
        if not detail.pets:
            if _PETS_ALLOW_RE.search(text):
                detail.pets = True

        # Collect all attribute labels into amenities
        if text and text not in detail.amenities:
            detail.amenities.append(text)

    # ---- Claude API enrichment ---------------------------------------------

    def _enrich_with_claude(
        self, detail: CraigslistDetail, listing
    ) -> None:
        """
        Call the Claude API to fill any fields that the scraper could not
        extract, and generate a listing summary + neighbourhood description.
        """
        if not detail.description:
            logger.debug("No description available for Claude enrichment — skipping.")
            return

        gaps: dict[str, str] = {}

        if detail.available_at is None:
            gaps["available_at"] = (
                "ISO date (YYYY-MM-DD) or 'now' if immediately available, else null"
            )
        if detail.lease_length_months is None:
            gaps["lease_length_months"] = "integer months, or null if not stated"
        if not detail.laundry:
            gaps["laundry"] = (
                'list of strings, e.g. ["Laundry in unit"], or []'
            )
        if not detail.parking:
            gaps["parking"] = (
                'list of strings, e.g. ["Street parking only"], or []'
            )
        if not detail.pets:
            gaps["pets"] = "true if pets are explicitly allowed, false otherwise"
        if not detail.host_contact:
            gaps["host_contact"] = (
                "landlord or agent name / company mentioned in the description, or null"
            )

        # Always generate summary and neighbourhood description
        gaps["summary"] = "2-3 sentence renter-facing summary of the apartment"
        gaps["neighborhood_description"] = (
            "1-2 sentence description of the neighbourhood for a renter"
        )

        neighborhood = detail.neighborhood_name or getattr(listing, "neighborhood_name", "")
        prompt = f"""You are a real estate data extraction assistant.
Given this Craigslist listing, extract or infer the requested fields.
Respond ONLY with a valid JSON object. No markdown, no code fences, no explanation.

LISTING:
- Address: {detail.full_address or listing.name}
- Neighborhood: {neighborhood}
- Price: ${detail.price or listing.price}/mo
- Beds: {detail.bedroom_type or listing.bedroom_type}
- Baths: {detail.bathrooms}
- Sq ft: {detail.square_feet or getattr(listing, 'square_feet', None)}
- Amenities parsed: {detail.amenities}
- Available: {detail.available_at or 'not stated'}
- Description: {detail.description}

EXTRACT THESE FIELDS (return exactly these keys):
{json.dumps(gaps, indent=2)}
"""

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         self._ant_key,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "messages":   [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            resp.raise_for_status()

            text = "".join(
                b.get("text", "")
                for b in resp.json().get("content", [])
                if b.get("type") == "text"
            )
            text = re.sub(r"^```(?:json)?\s*", "", text.strip())
            text = re.sub(r"\s*```$", "", text)
            inferred = json.loads(text)
            logger.info("Claude (CL) filled: %s", list(inferred.keys()))

            def _apply(key: str, attr: str, cast=None) -> None:
                val = inferred.get(key)
                if val is None or val == "null":
                    return
                if cast:
                    try:
                        val = cast(val)
                    except (TypeError, ValueError):
                        return
                setattr(detail, attr, val)

            _apply("available_at",        "available_at")
            _apply("lease_length_months", "lease_length_months", int)
            _apply("summary",             "claude_summary")

            if "laundry" in inferred and not detail.laundry:
                if isinstance(inferred["laundry"], list):
                    detail.laundry = inferred["laundry"]

            if "parking" in inferred and not detail.parking:
                if isinstance(inferred["parking"], list):
                    detail.parking = inferred["parking"]

            if "pets" in inferred and not detail.pets:
                if isinstance(inferred["pets"], bool):
                    detail.pets = inferred["pets"]

            if "host_contact" in inferred and not detail.host_contact:
                val = inferred["host_contact"]
                if val and val != "null":
                    detail.host_contact = val

            if "neighborhood_description" in inferred:
                listing._claude_neighborhood_description = (
                    inferred["neighborhood_description"]
                )

        except requests.HTTPError as exc:
            logger.warning("Claude API HTTP error (CL): %s", exc)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Claude response parse error (CL): %s", exc)
        except Exception as exc:
            logger.warning("Claude enrichment failed (CL): %s", exc, exc_info=True)

    # ---- ZenRows HTTP -------------------------------------------------------

    def _fetch_html(self, url: str) -> str:
        elapsed = time.monotonic() - self._last_req
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)

        params    = {"apikey": self._zr_key, "url": url, **self._params}
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._retries + 1):
            try:
                resp = requests.get(ZENROWS_BASE_URL, params=params, timeout=60)
                self._last_req = time.monotonic()
                if resp.status_code == 200:
                    return resp.text
                zr_msg = resp.headers.get("Zr-Error", resp.text[:200])
                logger.warning(
                    "ZenRows HTTP %d attempt %d/%d (CL): %s",
                    resp.status_code, attempt, self._retries, zr_msg,
                )
                if resp.status_code in (401, 402):
                    raise RuntimeError(f"ZenRows auth/credits error: {zr_msg}")
                time.sleep(2 ** attempt)
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "Request error %d/%d (CL): %s", attempt, self._retries, exc
                )
                time.sleep(2 ** attempt)

        raise RuntimeError(
            f"Failed to fetch {url} after {self._retries} attempts"
        ) from last_exc


# ---------------------------------------------------------------------------
# Merge CraigslistDetail -> CraigslistListing
# ---------------------------------------------------------------------------

def _merge(detail: CraigslistDetail, listing) -> None:
    """
    Copy non-empty fields from a scraped CraigslistDetail into the listing.
    Does not overwrite fields that already have a non-empty value, so email-
    parsed values (price, bedroom_type) are preserved if the scraper fails.

    Special case for `name`: if the scraper found a real street address, it
    replaces the email title that was stored in listing.name.
    """
    # Replace the email title with the real address if we found one.
    if detail.full_address:
        listing.name = detail.full_address

    scalar_map = {
        "price":               "price",
        "bedroom_type":        "bedroom_type",
        "bathrooms":           "bathrooms",
        "square_feet":         "square_feet",
        "latitude":            "latitude",
        "longitude":           "longitude",
        "neighborhood_name":   "neighborhood_name",
        "available_at":        "move_in_date",
        "lease_length_months": "lease_length_months",
        "host_contact":        "host_contact",
        "description":         "description",
    }
    for src, dst in scalar_map.items():
        src_val = getattr(detail, src, None)
        dst_val = getattr(listing, dst, None)
        if dst_val in (None, "", 0, False) and src_val not in (None, "", 0, False):
            setattr(listing, dst, src_val)

    # Lists: only copy if listing's list is empty
    for src, dst in [
        ("amenities",    "amenities"),
        ("laundry",      "laundry"),
        ("parking",      "parking"),
        ("images",       "images"),
        ("image_labels", "image_labels"),
    ]:
        if not getattr(listing, dst, []):
            val = getattr(detail, src, [])
            if val:
                setattr(listing, dst, val)

    # Pets: once True, stays True
    if detail.pets and not listing.pets:
        listing.pets = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_int(val: Any) -> Optional[int]:
    try:
        return int(float(str(val).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _parse_price(text: str) -> Optional[int]:
    m = re.search(r"\$([\d,]+)", text)
    return _to_int(m.group(1)) if m else None