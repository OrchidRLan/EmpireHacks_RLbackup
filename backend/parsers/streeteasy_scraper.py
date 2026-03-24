"""
StreetEasy Listing Scraper
==========================
Fetches a StreetEasy rental listing page via ZenRows and extracts every
field that maps onto the Apartment schema.

Architecture
------------
StreetEasy is built on Next.js App Router with React Server Components.
The page does NOT contain a classic __NEXT_DATA__ blob.  Instead, all
data is streamed in as a series of:

    self.__next_f.push([1, "<escaped-json-fragment>"])

calls.  When decoded and concatenated these fragments contain the full
React component tree, including every listing field as inline JSON.

Extraction strategy (three layers, tried in order):

  1. RSC Stream  — decode all __next_f fragments, extract listing fields
     with targeted regexes. Most reliable and richest source.

  2. Meta tags  — <meta name="ICBM"> for lat/lng (always present),
     <meta name="description"> for the full description,
     <meta property="og:image"> for the first photo.

  3. DOM fallback  — data-testid attributes on rendered elements.
     Used for any field layers 1-2 did not populate.

Claude API enrichment
---------------------
After scraping, any fields that remain empty are passed to the Claude API
which infers them from the listing description and available context:
lease_length_months, pets, laundry, parking, move_in_date normalisation,
and generates a concise listing summary + neighborhood description.

Usage
-----
    from listing_scraper import ListingScraper

    scraper = ListingScraper(
        zenrows_api_key="ZR_KEY",
        anthropic_api_key="ANT_KEY",  # or via ANTHROPIC_API_KEY env var
    )
    enriched_listing = scraper.enrich(parsed_listing)

Environment variables
---------------------
    ZENROWS_API_KEY      ZenRows API key
    ANTHROPIC_API_KEY    Anthropic API key (Claude enrichment)
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

# js_render + antibot: required — StreetEasy is a React SPA behind Cloudflare.
# wait=3000: gives the RSC stream time to fully hydrate before snapshot.
# premium_proxy: residential IP, required for StreetEasy geo-checks.
DEFAULT_ZENROWS_PARAMS: dict[str, Any] = {
    "js_render": "true",
    "antibot": "false",
    "wait": 3000,
    "premium_proxy": "false",
}

REQUEST_DELAY_SECONDS = 2

# ---------------------------------------------------------------------------
# Amenity code -> human label mapping
# StreetEasy stores amenities as uppercase enum codes in the RSC stream.
# ---------------------------------------------------------------------------

AMENITY_LABELS: dict[str, str] = {
    "FIOS_AVAILABLE":         "Fios available",
    "LIVE_IN_SUPER":          "Live-in super",
    "FULL_TIME_DOORMAN":      "Full-time doorman",
    "PART_TIME_DOORMAN":      "Part-time doorman",
    "VIRTUAL_DOORMAN":        "Virtual doorman",
    "ELEVATOR":               "Elevator",
    "GYM":                    "Gym",
    "ROOF_DECK":              "Roof deck",
    "OUTDOOR_SPACE":          "Outdoor space",
    "GARAGE_PARKING":         "Garage parking",
    "OUTDOOR_PARKING":        "Outdoor parking",
    "VALET_PARKING":          "Valet parking",
    "STORAGE":                "Storage",
    "BIKE_ROOM":              "Bike room",
    "LAUNDRY_IN_BUILDING":    "Laundry in building",
    "WASHER_DRYER_IN_UNIT":   "Washer/dryer in unit",
    "DISHWASHER":             "Dishwasher",
    "CONCIERGE":              "Concierge",
    "POOL":                   "Pool",
    "CHILDREN_PLAYROOM":      "Children's playroom",
    "PETS_ALLOWED":           "Pets allowed",
    "NO_PETS":                "No pets",
    "CATS_ALLOWED":           "Cats allowed",
    "DOGS_ALLOWED":           "Dogs allowed",
    "SMOKE_FREE":             "Smoke-free",
    "WHEELCHAIR_ACCESS":      "Wheelchair access",
    "GREEN_BUILDING":         "Green building",
    "COLD_STORAGE":           "Cold storage",
    "PACKAGE_ROOM":           "Package room",
    "MEDIA_ROOM":             "Media room",
    "FURNISHED":              "Furnished",
}

LAUNDRY_CODES  = {"LAUNDRY_IN_BUILDING", "WASHER_DRYER_IN_UNIT"}
PARKING_CODES  = {"GARAGE_PARKING", "OUTDOOR_PARKING", "VALET_PARKING"}
PETS_CODES     = {"PETS_ALLOWED", "CATS_ALLOWED", "DOGS_ALLOWED"}


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class ListingDetail:
    """All fields extractable from a single StreetEasy listing page."""
    # Pricing / lease
    price:                Optional[int]   = None
    available_at:         Optional[str]   = None   # ISO date or human string
    lease_length_months:  Optional[int]   = None
    months_free:          Optional[int]   = None
    security_deposit:     Optional[int]   = None
    move_in_fees:         list[dict]      = field(default_factory=list)

    # Unit
    bedroom_type:         Optional[str]   = None
    bathrooms:            Optional[int]   = None
    half_bathrooms:       Optional[int]   = None
    room_count:           Optional[int]   = None
    square_feet:          Optional[int]   = None
    building_type:        Optional[str]   = None

    # Location
    neighborhood_name:    Optional[str]   = None
    full_address:         Optional[str]   = None
    latitude:             Optional[float] = None
    longitude:            Optional[float] = None
    zip_code:             Optional[str]   = None

    # Features
    amenity_codes:        list[str]       = field(default_factory=list)
    amenities:            list[str]       = field(default_factory=list)
    laundry:              list[str]       = field(default_factory=list)
    parking:              list[str]       = field(default_factory=list)
    doorman_types:        list[str]       = field(default_factory=list)
    pets:                 bool            = False

    # Agent / brokerage
    host_contact:         Optional[str]   = None
    agent_name:           Optional[str]   = None
    agent_phone:          Optional[str]   = None

    # Media
    images:               list[str]       = field(default_factory=list)
    image_labels:         list[str]       = field(default_factory=list)

    # Description
    description:          Optional[str]   = None

    # Building
    building_units:       Optional[int]   = None
    building_stories:     Optional[int]   = None
    building_year_built:  Optional[int]   = None

    # Status
    listing_status:       Optional[str]   = None
    days_on_market:       Optional[int]   = None
    on_market_at:         Optional[str]   = None

    # Claude-generated
    claude_summary:       Optional[str]   = None


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

class ListingScraper:
    """
    Enriches a ParsedListing by scraping the StreetEasy listing page via
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

    def scrape(self, url: str) -> ListingDetail:
        """Fetch + parse a StreetEasy URL. Returns a ListingDetail."""
        html = self._fetch_html(url)
        return self._parse_html(html)

    def enrich(self, listing) -> object:
        """Fetch the listing page, run Claude, merge fields into listing."""
        logger.info("Enriching %s", listing.streeteasy_url)
        try:
            html   = self._fetch_html(listing.streeteasy_url)
            detail = self._parse_html(html)
            if self._ant_key:
                self._enrich_with_claude(detail, listing)
            _merge(detail, listing)
        except Exception as exc:
            logger.error("Failed to enrich %s: %s", listing.streeteasy_url, exc, exc_info=True)
        return listing

    def enrich_batch(self, listings: list) -> list:
        """Enrich a list of ParsedListings sequentially."""
        for listing in listings:
            self.enrich(listing)
        return listings

    # ---- HTML parsing ------------------------------------------------------

    def _parse_html(self, html: str) -> ListingDetail:
        soup   = BeautifulSoup(html, "html.parser")
        detail = ListingDetail()
        self._extract_rsc_stream(html, detail)    # Layer 1
        self._extract_meta_tags(soup, detail)     # Layer 2
        self._extract_dom(soup, detail)           # Layer 3
        self._classify_amenities(detail)
        logger.info(
            "price=$%s beds=%s lat=%s lng=%s amenities=%s photos=%d",
            detail.price, detail.bedroom_type, detail.latitude,
            detail.longitude, detail.amenity_codes, len(detail.images),
        )
        return detail

    # ---- Layer 1: RSC stream -----------------------------------------------

    def _extract_rsc_stream(self, html: str, detail: ListingDetail) -> None:
        """
        Decode all self.__next_f.push([1, "..."]) fragments, concatenate,
        then pull listing fields with targeted regexes.

        StreetEasy App Router pages contain no __NEXT_DATA__ script; all
        server data is delivered through the RSC wire protocol instead.
        """
        soup      = BeautifulSoup(html, "html.parser")
        fragments = []
        for script in soup.find_all("script"):
            content = script.string or ""
            m = re.match(
                r'self\.__next_f\.push\(\[1,"(.*)"\]\)\s*$',
                content.strip(), re.DOTALL,
            )
            if m:
                raw = m.group(1)
                decoded = (
                    raw.replace('\\"',  '"')
                       .replace('\\\\', '\\')
                       .replace('\\n',  '\n')
                       .replace('\\t',  '\t')
                       .replace('\\r',  '\r')
                )
                fragments.append(decoded)

        if not fragments:
            logger.debug("No __next_f RSC fragments found.")
            return

        full = "\n".join(fragments)

        # Price — confirmed listing price (not similar-listing price)
        if detail.price is None:
            m = re.search(r'"price":(\d+),"changedAt"', full)
            if m:
                detail.price = int(m.group(1))

        # Available date
        if detail.available_at is None:
            m = re.search(r'"availableAt":"(\d{4}-\d{2}-\d{2})"', full)
            if m:
                detail.available_at = m.group(1)

        # Lease / pricing fields
        if detail.lease_length_months is None:
            m = re.search(r'"leaseTermMonths":(\d+)', full)
            if m:
                detail.lease_length_months = int(m.group(1))

        if detail.months_free is None:
            m = re.search(r'"monthsFree":(\d+)', full)
            if m:
                detail.months_free = int(m.group(1))

        if detail.security_deposit is None:
            m = re.search(r'"securityDeposit":(\d+)', full)
            if m:
                detail.security_deposit = int(m.group(1))

        # Beds / baths / rooms
        if detail.bedroom_type is None:
            m = re.search(r'"bedroomCount":(\d+)', full)
            if m:
                detail.bedroom_type = _rooms_to_bedroom_type(int(m.group(1)))

        if detail.bathrooms is None:
            m = re.search(r'"fullBathroomCount":(\d+)', full)
            if m:
                detail.bathrooms = int(m.group(1))

        if detail.half_bathrooms is None:
            m = re.search(r'"halfBathroomCount":(\d+)', full)
            if m:
                detail.half_bathrooms = int(m.group(1))

        if detail.room_count is None:
            m = re.search(r'"roomCount":(\d+)', full)
            if m:
                detail.room_count = int(m.group(1))

        if detail.square_feet is None:
            m = re.search(r'"livingAreaSize":(\d+)', full)
            if m:
                detail.square_feet = int(m.group(1))

        if detail.building_type is None:
            m = re.search(r'"buildingType":"([^"]+)"', full)
            if m:
                detail.building_type = m.group(1)

        # Address — canonical block present on listing pages
        if detail.full_address is None:
            m = re.search(
                r'"address":\{"state":"[^"]*","street":"([^"]+)",'
                r'"city":"([^"]+)","zipCode":"([^"]+)","displayUnit":"([^"]+)"\}',
                full,
            )
            if m:
                detail.full_address = (
                    f"{m.group(1)} {m.group(4)}, {m.group(2).title()}, NY {m.group(3)}"
                )
                detail.zip_code = m.group(3)

        # Neighborhood from breadcrumbs.
        # StreetEasy renders two breadcrumb blocks; the full one has 4 entries:
        # Rentals > Queens > Sunnyside > "45-15 43rd Avenue #4A"
        # We use the first block with >= 3 names and take names[-2].
        if detail.neighborhood_name is None:
            bc_blocks = re.findall(r'"breadcrumbs":\[.*?\]', full, re.DOTALL)
            for bc in bc_blocks:
                names = re.findall(r'"name":"([^"]+)"', bc)
                if len(names) >= 3:
                    detail.neighborhood_name = names[-2]
                    break

        # Amenity codes
        if not detail.amenity_codes:
            am_m = re.search(
                r'"amenities":\{"list":\[([^\]]*)\],'
                r'"doormanTypes":\[([^\]]*)\],'
                r'"parkingTypes":\[([^\]]*)\]',
                full,
            )
            if am_m:
                def _parse_codes(s: str) -> list[str]:
                    # Codes are quoted uppercase strings: "FIOS_AVAILABLE","LIVE_IN_SUPER"
                    return re.findall(r'"([A-Z_]+)"', s)

                detail.amenity_codes  = _parse_codes(am_m.group(1))
                detail.doorman_types  = _parse_codes(am_m.group(2))
                parking_codes         = _parse_codes(am_m.group(3))
                if parking_codes:
                    detail.parking = [
                        AMENITY_LABELS.get(c, c.replace("_", " ").title())
                        for c in parking_codes
                    ]

        # Agent / brokerage
        if detail.host_contact is None:
            agent_m = re.search(
                r'"name":"([^"]+)","phone":"(\+[\d]+)",'
                r'"licenseType":"([^"]+)","sourceGroupLabel":"([^"]+)"',
                full,
            )
            if agent_m:
                detail.agent_name   = agent_m.group(1)
                detail.agent_phone  = agent_m.group(2)
                detail.host_contact = (
                    f"{agent_m.group(4)} — {agent_m.group(1)} ({agent_m.group(3)})"
                )

        if detail.host_contact is None:
            sg_m = re.search(r'"sourceGroupLabel":"([^"]+)"', full)
            if sg_m:
                detail.host_contact = sg_m.group(1)

        # Photos — extract listing's own photo keys from propertyHistory,
        # then build full-resolution URLs.
        if not detail.images:
            ph_m = re.search(
                r'"propertyHistory":\[.*?"photos":\[([^\]]+)\]',
                full, re.DOTALL,
            )
            if ph_m:
                keys = re.findall(r'"key":"([a-f0-9a-z]{32})"', ph_m.group(1))
                if keys:
                    BASE = "https://photos.zillowstatic.com/fp/"
                    detail.images      = [f"{BASE}{k}-full.webp" for k in keys]
                    detail.image_labels = [f"photo {i+1}" for i in range(len(keys))]

        # Fallback: grab all unique full-size webp URLs from the entire stream
        if not detail.images:
            urls = list(dict.fromkeys(
                re.findall(
                    r'https://photos\.zillowstatic\.com/fp/[a-f0-9]+-full\.webp',
                    full,
                )
            ))
            if urls:
                detail.images      = urls[:10]   # cap to avoid similar-listing photos
                detail.image_labels = [f"photo {i+1}" for i in range(len(detail.images))]

        # Status / days on market
        if detail.listing_status is None:
            m = re.search(r'"status":"(ACTIVE|INACTIVE|DRAFT|RENTED)"', full)
            if m:
                detail.listing_status = m.group(1)

        if detail.days_on_market is None:
            m = re.search(r'"daysOnMarket":(\d+)', full)
            if m:
                detail.days_on_market = int(m.group(1))

        if detail.on_market_at is None:
            m = re.search(r'"onMarketAt":"(\d{4}-\d{2}-\d{2})"', full)
            if m:
                detail.on_market_at = m.group(1)

        # Full description — anchor on the listing data object.
        # The deeplink banner also has a "description" field ("Want a closer look?")
        # that appears earlier in the stream, so we anchor our search on fields
        # that are unique to the main listing object: availableAt + interestingChangeAt.
        if detail.description is None:
            desc_m = re.search(
                r'"availableAt":"[^"]+","interestingChangeAt":"[^"]+",'
                r'"description":"((?:[^"\\]|\\.|\n)*?)",'
                r'"propertyDetails"',
                full, re.DOTALL,
            )
            if desc_m:
                detail.description = (
                    desc_m.group(1)
                          .replace("\\n", "\n")
                          .replace("\\r", "")
                          .strip()
                )

        # Move-in fees
        if not detail.move_in_fees:
            fees_m = re.search(
                r'"moveInFees":\[(\{.*?\}(?:,\{.*?\})*)\]',
                full, re.DOTALL,
            )
            if fees_m:
                try:
                    fees = json.loads(f"[{fees_m.group(1)}]")
                    detail.move_in_fees = [
                        {
                            "label":       f.get("typeLabel", ""),
                            "requirement": f.get("requirement", ""),
                            "amount":      f.get("calculation", {}).get("feeQuantifier"),
                        }
                        for f in fees if isinstance(f, dict)
                    ]
                except json.JSONDecodeError:
                    pass

    # ---- Layer 2: meta tags ------------------------------------------------

    def _extract_meta_tags(self, soup: BeautifulSoup, detail: ListingDetail) -> None:
        # Lat/lng from ICBM meta tag: "40.745174; -73.91862"
        if detail.latitude is None:
            icbm = soup.find("meta", attrs={"name": "ICBM"})
            if icbm:
                parts = [p.strip() for p in (icbm.get("content") or "").split(";")]
                if len(parts) == 2:
                    detail.latitude  = _to_float(parts[0])
                    detail.longitude = _to_float(parts[1])

        # Lat/lng fallback: Google Maps URL embedded in stream scripts
        if detail.latitude is None:
            for script in soup.find_all("script"):
                text = script.string or ""
                m = re.search(r"center=([\d.]+)%2C(-[\d.]+)", text)
                if m:
                    detail.latitude  = float(m.group(1))
                    detail.longitude = float(m.group(2))
                    break

        # Full description (meta has the non-truncated version)
        if detail.description is None:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                content = meta_desc.get("content") or ""
                # Strip "45-15 43rd Avenue, Sunnyside, Ny, 11104: " prefix
                desc = re.sub(r"^[^:]+:\s*", "", content)
                desc = re.sub(r"\.\.\.$", "", desc).strip()
                if desc:
                    detail.description = desc

        # First photo from og:image
        if not detail.images:
            og_img = soup.find("meta", attrs={"property": "og:image"})
            if og_img and og_img.get("content"):
                detail.images      = [og_img["content"]]
                detail.image_labels = ["photo 1"]

    # ---- Layer 3: DOM fallback (data-testid) --------------------------------

    def _extract_dom(self, soup: BeautifulSoup, detail: ListingDetail) -> None:
        def _text(testid: str) -> str:
            el = soup.find(attrs={"data-testid": testid})
            return el.get_text(strip=True) if el else ""

        # Price
        if detail.price is None:
            detail.price = _parse_price_text(_text("priceInfo"))

        # Address
        if detail.full_address is None:
            t = _text("address")
            if t:
                detail.full_address = t

        # Beds / baths from propertyDetails: "- ft²  2 rooms  1 bed  1 bath"
        if detail.bedroom_type is None or detail.bathrooms is None:
            prop = _text("propertyDetails")
            if detail.bedroom_type is None:
                m = re.search(r"(\d+)\s*bed|studio", prop, re.IGNORECASE)
                if m:
                    detail.bedroom_type = (
                        "Studio" if "studio" in m.group(0).lower()
                        else f"{m.group(1)} Bed"
                    )
            if detail.bathrooms is None:
                m = re.search(r"(\d+)\s*bath", prop, re.IGNORECASE)
                if m:
                    detail.bathrooms = int(m.group(1))

        # Neighborhood from buildingSummaryList: "Rental unit  Sunnyside"
        if detail.neighborhood_name is None:
            bld = _text("buildingSummaryList")
            parts = [p.strip() for p in re.split(r"\s{2,}|\n", bld) if p.strip()]
            if len(parts) >= 2:
                detail.neighborhood_name = parts[-1]

        # Available date
        if detail.available_at is None:
            avail = _text("rentalListingSpec-available")
            avail = avail.replace("Available", "").strip()
            if avail and avail.lower() != "now":
                detail.available_at = avail  # Claude will normalise to ISO

        # Agent contact (fallback)
        if detail.host_contact is None:
            t = _text("listing-by")
            if t:
                detail.host_contact = t.replace("Listing by ", "").strip()

        # Description from about-section
        if detail.description is None:
            about = _text("about-section")
            if about:
                detail.description = re.sub(r"^About\s*", "", about, flags=re.IGNORECASE).strip()

        # Amenities from rendered building-amenities-section.
        # Only used when RSC stream yielded no amenity codes AND amenities list is empty.
        # The DOM section mixes real amenity labels with "No info on …" placeholders
        # and section headers, so we filter aggressively.
        if not detail.amenity_codes and not detail.amenities:
            bld_am = soup.find(attrs={"data-testid": "building-amenities-section"})
            if bld_am:
                # Target only the individual amenity items (rendered as <li> or <p>)
                # within the named subsections, not the section headers themselves.
                SKIP = {
                    "services and facilities", "wellness and recreation",
                    "shared outdoor space", "building amenities",
                    "policies",
                }
                items = bld_am.find_all(["li", "p"])
                labels = []
                for item in items:
                    text = item.get_text(strip=True)
                    if (
                        text
                        and len(text) > 2
                        and text.lower() not in SKIP
                        and not text.lower().startswith("no info on")
                        and not text.lower().startswith("sorry,")
                    ):
                        labels.append(text)
                if labels:
                    detail.amenities = labels

        # Building stats from building-description-icons: "16 units  4 stories  1926 built"
        bld_icons = soup.find(attrs={"data-testid": "building-description-icons"})
        if bld_icons:
            text = bld_icons.get_text(strip=True)
            if detail.building_units is None:
                m = re.search(r"(\d+)\s*units?", text, re.IGNORECASE)
                if m:
                    detail.building_units = int(m.group(1))
            if detail.building_stories is None:
                m = re.search(r"(\d+)\s*stor", text, re.IGNORECASE)
                if m:
                    detail.building_stories = int(m.group(1))
            if detail.building_year_built is None:
                m = re.search(r"(\d{4})\s*built", text, re.IGNORECASE)
                if m:
                    detail.building_year_built = int(m.group(1))

        # Days on market from spec
        if detail.days_on_market is None:
            dom_text = _text("rentalListingSpec-daysOnMarket")
            m = re.search(r"(\d+)\s*day", dom_text, re.IGNORECASE)
            if m:
                detail.days_on_market = int(m.group(1))
            elif "today" in dom_text.lower():
                detail.days_on_market = 0

    # ---- Amenity classification --------------------------------------------

    def _classify_amenities(self, detail: ListingDetail) -> None:
        """Convert raw amenity codes into labelled lists, laundry, parking, pets."""
        if not detail.amenity_codes:
            return

        labels: list[str] = []
        for code in detail.amenity_codes:
            label = AMENITY_LABELS.get(code, code.replace("_", " ").title())
            labels.append(label)
            if code in LAUNDRY_CODES and not detail.laundry:
                detail.laundry = [label]
            if code in PARKING_CODES and not detail.parking:
                detail.parking = [label]
            if code in PETS_CODES:
                detail.pets = True

        for code in detail.doorman_types:
            label = AMENITY_LABELS.get(code, code.replace("_", " ").title())
            labels.append(label)

        if labels and not detail.amenities:
            detail.amenities = labels

    # ---- Claude API enrichment ---------------------------------------------

    def _enrich_with_claude(self, detail: ListingDetail, listing) -> None:
        """
        Call the Claude API to fill any gaps remaining after scraping.

        Handled fields:
          - available_at normalised to ISO date
          - lease_length_months inferred from description
          - pets / laundry / parking inferred from description
          - claude_summary: a concise renter-facing summary
          - neighborhood_description: stored on the listing for NeighborInfo
        """
        if not detail.description:
            logger.debug("No description available for Claude — skipping.")
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
                'list of strings describing laundry, e.g. ["In-unit laundry"], or []'
            )
        if not detail.parking:
            gaps["parking"] = (
                'list of strings describing parking, e.g. ["Street parking"], or []'
            )
        if not detail.pets:
            gaps["pets"] = "true if pets are allowed, false otherwise"

        # Always generate summary and neighborhood description
        gaps["summary"] = "2-3 sentence renter-facing summary of the apartment"
        gaps["neighborhood_description"] = (
            "1-2 sentence description of the neighborhood for a renter"
        )

        prompt = f"""You are a real estate data extraction assistant.
Given this StreetEasy listing, extract or infer the requested fields.
Respond ONLY with a valid JSON object. No markdown, no code fences, no explanation.

LISTING:
- Address: {listing.name}
- Neighborhood: {detail.neighborhood_name or listing.neighborhood_name}
- Price: ${detail.price or listing.price}/mo
- Beds: {detail.bedroom_type or listing.bedroom_type}
- Baths: {detail.bathrooms}
- Building type: {detail.building_type}
- Building: {detail.building_units} units, {detail.building_stories} stories, built {detail.building_year_built}
- Status: {detail.listing_status}
- Available: {detail.available_at or 'not stated'}
- Amenity codes: {detail.amenity_codes}
- Amenities (rendered): {detail.amenities}
- Days on market: {detail.days_on_market}
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
            logger.info("Claude filled: %s", list(inferred.keys()))

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

            # Store neighborhood description on the listing object for db_writer
            if "neighborhood_description" in inferred:
                listing._claude_neighborhood_description = (
                    inferred["neighborhood_description"]
                )

        except requests.HTTPError as exc:
            logger.warning("Claude API HTTP error: %s", exc)
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Claude response parse error: %s", exc)
        except Exception as exc:
            logger.warning("Claude enrichment failed: %s", exc, exc_info=True)

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
                    "ZenRows HTTP %d attempt %d/%d: %s",
                    resp.status_code, attempt, self._retries, zr_msg,
                )
                if resp.status_code in (401, 402):
                    raise RuntimeError(f"ZenRows auth/credits error: {zr_msg}")
                time.sleep(2 ** attempt)
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning("Request error %d/%d: %s", attempt, self._retries, exc)
                time.sleep(2 ** attempt)

        raise RuntimeError(
            f"Failed to fetch {url} after {self._retries} attempts"
        ) from last_exc


# ---------------------------------------------------------------------------
# Merge ListingDetail -> ParsedListing
# ---------------------------------------------------------------------------

def _merge(detail: ListingDetail, listing) -> None:
    """Copy non-empty fields from detail into listing without overwriting."""
    mapping = {
        "price":               "price",
        "bedroom_type":        "bedroom_type",
        "latitude":            "latitude",
        "longitude":           "longitude",
        "neighborhood_name":   "neighborhood_name",
        "available_at":        "move_in_date",
        "lease_length_months": "lease_length_months",
        "amenities":           "amenities",
        "laundry":             "laundry",
        "parking":             "parking",
        "pets":                "pets",
        "host_contact":        "host_contact",
        "images":              "images",
        "image_labels":        "image_labels",
    }
    for src, dst in mapping.items():
        src_val = getattr(detail, src, None)
        dst_val = getattr(listing, dst, None)
        if dst_val in (None, "", [], False, 0) and src_val not in (None, "", [], False):
            setattr(listing, dst, src_val)


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


def _parse_price_text(text: str) -> Optional[int]:
    m = re.search(r"\$([\d,]+)", text)
    return _to_int(m.group(1)) if m else None


def _rooms_to_bedroom_type(rooms: Any) -> Optional[str]:
    if rooms is None:
        return None
    try:
        n = int(rooms)
        return "Studio" if n == 0 else f"{n} Bed"
    except (TypeError, ValueError):
        s = str(rooms).lower()
        return "Studio" if "studio" in s else str(rooms)