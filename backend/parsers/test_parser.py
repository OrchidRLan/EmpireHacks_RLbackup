"""
Quick smoke-test for the StreetEasy email parser.
Run: python test_parser.py
"""

import sys
import os

# Allow running from the package directory directly.
sys.path.insert(0, os.path.dirname(__file__))

from streeteasy_email import StreetEasyEmailParser

EML_PATH = "test.eml"


def test_parse_sample_eml():
    parser = StreetEasyEmailParser()
    listings = parser.parse_eml_file(EML_PATH)

    print(f"\n{'='*55}")
    print(f"  Parsed {len(listings)} listing(s)")
    print(f"{'='*55}")
    assert len(listings) == 2, f"Expected 2 listings, got {len(listings)}"

    for i, l in enumerate(listings, 1):
        print(f"\n[{i}] {l.name}")
        print(f"    Neighborhood : {l.neighborhood_name}")
        print(f"    Bedroom type : {l.bedroom_type}")
        print(f"    Price        : ${l.price:,}/mo")
        print(f"    Bathrooms    : {l.bathrooms}")
        print(f"    Host contact : {l.host_contact}")
        print(f"    SE ID        : {l.streeteasy_id}")
        print(f"    URL          : {l.streeteasy_url}")
        print(f"    Email date   : {l.email_date}")
        print(f"    Subject      : {l.email_subject}")

    # Specific assertions based on the sample email
    apt1 = next(l for l in listings if l.streeteasy_id == "4995742")
    assert apt1.name == "45-15 43rd Avenue #4A"
    assert apt1.price == 2300
    assert apt1.bedroom_type == "1 Bed"
    assert apt1.neighborhood_name == "Sunnyside"
    assert apt1.bathrooms == 1
    assert "Voro New York" in apt1.host_contact

    apt2 = next(l for l in listings if l.streeteasy_id == "4995738")
    assert apt2.name == "39-51 50th Street #1B"
    assert apt2.price == 1700
    assert apt2.bedroom_type == "Studio"
    assert apt2.neighborhood_name == "Sunnyside"
    assert "Keller Williams" in apt2.host_contact

    print("\n✅  All assertions passed.\n")


if __name__ == "__main__":
    test_parse_sample_eml()