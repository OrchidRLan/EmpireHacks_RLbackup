"""
Tests for streeteasy_scraper.py — uses the real scraped HTML (se_debug2.html).
No network or API key needed for the unit tests.

Run modes:
  python test_scraper.py              # all unit tests against real HTML
  python test_scraper.py --live       # live ZenRows + Claude (needs keys)
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from streeteasy_scraper import (
    ListingScraper, ListingDetail, _merge,
    _rooms_to_bedroom_type, _to_float, _to_int, _parse_price_text,
    AMENITY_LABELS,
)
from streeteasy_email import ParsedListing

REAL_HTML_PATH = "/mnt/user-data/uploads/se_debug2.html"


def _load_real_html() -> str:
    with open(REAL_HTML_PATH) as f:
        return f.read()

def _make_scraper() -> ListingScraper:
    return ListingScraper(zenrows_api_key="DUMMY_KEY_FOR_TESTING")

def _make_listing() -> ParsedListing:
    return ParsedListing(
        streeteasy_id="4995742",
        streeteasy_url="https://streeteasy.com/rental/4995742",
        name="45-15 43rd Avenue #4A",
        bedroom_type="1 Bed",
        price=2300,
        neighborhood_name="Sunnyside",
    )


class TestHelpers(unittest.TestCase):
    def test_to_float(self):
        self.assertEqual(_to_float("40.7441"), 40.7441)
        self.assertIsNone(_to_float(None))
        self.assertIsNone(_to_float("n/a"))

    def test_to_int(self):
        self.assertEqual(_to_int("2,300"), 2300)
        self.assertEqual(_to_int("1.5"), 1)
        self.assertIsNone(_to_int(None))

    def test_parse_price_text(self):
        self.assertEqual(_parse_price_text("$2,300/mo"), 2300)
        self.assertIsNone(_parse_price_text("no price"))

    def test_rooms_to_bedroom_type(self):
        self.assertEqual(_rooms_to_bedroom_type(0), "Studio")
        self.assertEqual(_rooms_to_bedroom_type(1), "1 Bed")
        self.assertEqual(_rooms_to_bedroom_type("studio"), "Studio")
        self.assertIsNone(_rooms_to_bedroom_type(None))

    def test_amenity_labels(self):
        for code in ["FIOS_AVAILABLE", "LIVE_IN_SUPER", "ELEVATOR", "LAUNDRY_IN_BUILDING"]:
            self.assertIn(code, AMENITY_LABELS)


class TestRealHTMLParsing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(REAL_HTML_PATH):
            raise unittest.SkipTest(f"Not found: {REAL_HTML_PATH}")
        cls.detail = _make_scraper()._parse_html(_load_real_html())

    # Pricing
    def test_price(self):                 self.assertEqual(self.detail.price, 2300)
    def test_available_at(self):          self.assertEqual(self.detail.available_at, "2026-03-21")
    def test_lease_null(self):            self.assertIsNone(self.detail.lease_length_months)
    def test_days_on_market(self):        self.assertEqual(self.detail.days_on_market, 0)
    def test_on_market_at(self):          self.assertEqual(self.detail.on_market_at, "2026-03-21")

    # Unit
    def test_bedroom_type(self):          self.assertEqual(self.detail.bedroom_type, "1 Bed")
    def test_bathrooms(self):             self.assertEqual(self.detail.bathrooms, 1)
    def test_half_bathrooms(self):        self.assertEqual(self.detail.half_bathrooms, 0)
    def test_room_count(self):            self.assertEqual(self.detail.room_count, 2)
    def test_building_type(self):         self.assertEqual(self.detail.building_type, "Rental unit")

    # Location
    def test_latitude(self):              self.assertAlmostEqual(self.detail.latitude, 40.745174, places=4)
    def test_longitude(self):             self.assertAlmostEqual(self.detail.longitude, -73.91862, places=4)
    def test_neighborhood(self):          self.assertEqual(self.detail.neighborhood_name, "Sunnyside")
    def test_zip_code(self):              self.assertEqual(self.detail.zip_code, "11104")
    def test_full_address(self):          self.assertIn("43rd Avenue", self.detail.full_address)

    # Amenities
    def test_amenity_codes(self):
        self.assertIn("FIOS_AVAILABLE", self.detail.amenity_codes)
        self.assertIn("LIVE_IN_SUPER",  self.detail.amenity_codes)
    def test_amenities_labels(self):
        self.assertIn("Fios available", self.detail.amenities)
        self.assertIn("Live-in super",  self.detail.amenities)
    def test_no_parking(self):            self.assertEqual(self.detail.parking, [])
    def test_no_doorman(self):            self.assertEqual(self.detail.doorman_types, [])
    def test_pets_false(self):            self.assertFalse(self.detail.pets)
    def test_no_laundry_code(self):       self.assertEqual(self.detail.laundry, [])

    # Agent
    def test_host_has_agent(self):        self.assertIn("Leonidas Goumakos", self.detail.host_contact)
    def test_host_has_brokerage(self):    self.assertIn("Voro New York", self.detail.host_contact)
    def test_agent_phone(self):           self.assertEqual(self.detail.agent_phone, "+19179923143")

    # Photos
    def test_has_photos(self):            self.assertGreater(len(self.detail.images), 0)
    def test_photo_count(self):           self.assertEqual(len(self.detail.images), 5)
    def test_photos_are_webp(self):
        for img in self.detail.images:
            self.assertIn("zillowstatic.com", img)
            self.assertTrue(img.endswith(".webp"))
    def test_labels_match_images(self):   self.assertEqual(len(self.detail.images), len(self.detail.image_labels))

    # Description
    def test_description_present(self):   self.assertGreater(len(self.detail.description or ""), 20)
    def test_description_content(self):   self.assertIn("walk up", (self.detail.description or "").lower())

    # Status
    def test_status_active(self):         self.assertEqual(self.detail.listing_status, "ACTIVE")

    # Building
    def test_building_units(self):        self.assertEqual(self.detail.building_units, 16)
    def test_building_stories(self):      self.assertEqual(self.detail.building_stories, 4)
    def test_building_year_built(self):   self.assertEqual(self.detail.building_year_built, 1926)


class TestMerge(unittest.TestCase):
    def test_fills_empty_fields(self):
        listing = _make_listing()
        detail  = ListingDetail(
            latitude=40.7441, longitude=-73.9239,
            amenities=["Dishwasher"], pets=True, available_at="2026-04-01",
            images=["https://example.com/a.jpg"],
        )
        _merge(detail, listing)
        self.assertAlmostEqual(listing.latitude, 40.7441)
        self.assertTrue(listing.pets)
        self.assertEqual(listing.move_in_date, "2026-04-01")

    def test_does_not_overwrite(self):
        listing = _make_listing()
        listing.price = 2300
        _merge(ListingDetail(price=9999), listing)
        self.assertEqual(listing.price, 2300)


class TestEnrichWithRealHTML(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(REAL_HTML_PATH):
            raise unittest.SkipTest(f"Not found: {REAL_HTML_PATH}")
        cls.html = _load_real_html()

    def test_enrich_populates_listing(self):
        scraper = _make_scraper()
        listing = _make_listing()
        with patch.object(scraper, "_fetch_html", return_value=self.html):
            scraper.enrich(listing)
        self.assertAlmostEqual(listing.latitude,  40.745174, places=3)
        self.assertAlmostEqual(listing.longitude, -73.91862, places=3)
        self.assertEqual(listing.move_in_date, "2026-03-21")
        self.assertEqual(len(listing.images), 5)
        self.assertIn("Leonidas Goumakos", listing.host_contact)
        self.assertIn("Fios available", listing.amenities)

    def test_enrich_survives_error(self):
        scraper = _make_scraper()
        listing = _make_listing()
        with patch.object(scraper, "_fetch_html", side_effect=RuntimeError("down")):
            scraper.enrich(listing)
        self.assertEqual(listing.price, 2300)


def run_live_test() -> None:
    from dataclasses import asdict
    api_key = os.environ.get("ZENROWS_API_KEY", "")
    ant_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ZENROWS_API_KEY not set — skipping."); return
    scraper = ListingScraper(zenrows_api_key=api_key, anthropic_api_key=ant_key or None)
    listing = _make_listing()
    print(f"\nLIVE: {listing.streeteasy_url} | Claude: {'ON' if ant_key else 'OFF'}")
    scraper.enrich(listing)
    print("\n" + "=" * 60)
    for k, v in asdict(listing).items():
        if v not in (None, "", [], False, 0):
            print(f"  {k:25s}: {v}")
    nd = getattr(listing, "_claude_neighborhood_description", None)
    if nd:
        print(f"\n  neighborhood_description: {nd}")


if __name__ == "__main__":
    if "--live" in sys.argv:
        sys.argv.remove("--live")
        run_live_test()
    else:
        unittest.main(verbosity=2)