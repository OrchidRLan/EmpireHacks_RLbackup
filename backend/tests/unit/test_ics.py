"""Unit tests for app/agents/shared/ics_generator.py.

Verifies that generate_ics produces valid ICS bytes containing the
expected VCALENDAR structure, VEVENT component, summary, and DTSTART.
"""

from datetime import datetime, timedelta, timezone

import pytest
from icalendar import Calendar

from app.agents.shared.ics_generator import generate_ics


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_ics(data: bytes) -> Calendar:
    """Parse raw ICS bytes and return an icalendar.Calendar object."""
    return Calendar.from_ical(data)


def get_events(cal: Calendar) -> list:
    """Extract all VEVENT components from a calendar."""
    from icalendar import Event
    return [c for c in cal.walk() if isinstance(c, Event)]


# ── Basic structure ───────────────────────────────────────────────────────────

class TestGenerateIcsStructure:
    def test_returns_bytes(self):
        result = generate_ics("Test Event", datetime(2025, 6, 15, 10, 0))
        assert isinstance(result, bytes)

    def test_non_empty_output(self):
        result = generate_ics("Test Event", datetime(2025, 6, 15, 10, 0))
        assert len(result) > 0

    def test_contains_vcalendar_marker(self):
        result = generate_ics("Test Event", datetime(2025, 6, 15, 10, 0))
        assert b"BEGIN:VCALENDAR" in result
        assert b"END:VCALENDAR" in result

    def test_contains_vevent_marker(self):
        result = generate_ics("Test Event", datetime(2025, 6, 15, 10, 0))
        assert b"BEGIN:VEVENT" in result
        assert b"END:VEVENT" in result

    def test_parseable_by_icalendar_library(self):
        data = generate_ics("My Apartment Visit", datetime(2025, 6, 15, 14, 0))
        cal = parse_ics(data)
        # If Calendar.from_ical succeeds without raising, it is valid
        assert cal is not None


# ── Summary field ─────────────────────────────────────────────────────────────

class TestGenerateIcsSummary:
    def test_summary_present_in_raw_bytes(self):
        data = generate_ics("Apartment Visit - SoHo Studio #5A", datetime(2025, 6, 15, 10, 0))
        assert b"Apartment Visit" in data

    def test_summary_present_in_parsed_event(self):
        summary_text = "My Unique Visit Summary"
        data = generate_ics(summary_text, datetime(2025, 6, 15, 10, 0))
        cal = parse_ics(data)
        events = get_events(cal)
        assert len(events) == 1
        assert str(events[0]["summary"]) == summary_text

    def test_special_characters_in_summary(self):
        summary_text = "Visit: 5A (2BR) — $2,500/mo"
        data = generate_ics(summary_text, datetime(2025, 6, 15, 10, 0))
        assert isinstance(data, bytes)
        # Should not raise; summary should survive round-trip
        cal = parse_ics(data)
        events = get_events(cal)
        assert len(events) == 1


# ── DTSTART field ─────────────────────────────────────────────────────────────

class TestGenerateIcsDtstart:
    def test_dtstart_present_in_raw_bytes(self):
        data = generate_ics("Visit", datetime(2025, 6, 15, 10, 0))
        assert b"DTSTART" in data

    def test_dtstart_matches_input_datetime(self):
        start = datetime(2025, 7, 4, 14, 30)
        data = generate_ics("Visit", start)
        cal = parse_ics(data)
        events = get_events(cal)
        assert len(events) == 1
        event_start = events[0]["dtstart"].dt
        # icalendar may return a datetime with or without tzinfo
        if hasattr(event_start, "replace"):
            # Strip tz for comparison
            event_start_naive = event_start.replace(tzinfo=None)
            assert event_start_naive == start

    def test_dtend_is_duration_after_dtstart(self):
        start = datetime(2025, 7, 4, 14, 0)
        duration = 90
        data = generate_ics("Visit", start, duration_minutes=duration)
        cal = parse_ics(data)
        events = get_events(cal)
        event = events[0]
        dtstart = event["dtstart"].dt
        dtend = event["dtend"].dt

        # Normalize tzinfo away for arithmetic
        def naive(dt):
            return dt.replace(tzinfo=None) if hasattr(dt, "replace") else dt

        assert naive(dtend) - naive(dtstart) == timedelta(minutes=duration)


# ── Optional fields ───────────────────────────────────────────────────────────

class TestGenerateIcsOptionalFields:
    def test_description_included_when_provided(self):
        data = generate_ics(
            "Visit",
            datetime(2025, 6, 15, 10, 0),
            description="Bring your ID and rental history",
        )
        assert b"DESCRIPTION" in data
        assert b"Bring your ID" in data

    def test_description_omitted_when_empty(self):
        data = generate_ics("Visit", datetime(2025, 6, 15, 10, 0), description="")
        # DESCRIPTION line should not appear
        assert b"DESCRIPTION" not in data

    def test_location_included_when_provided(self):
        data = generate_ics(
            "Visit",
            datetime(2025, 6, 15, 10, 0),
            location="123 Broadway, New York, NY",
        )
        assert b"LOCATION" in data
        assert b"123 Broadway" in data

    def test_organizer_email_included(self):
        data = generate_ics(
            "Visit",
            datetime(2025, 6, 15, 10, 0),
            organizer_email="host@example.com",
        )
        assert b"ORGANIZER" in data
        assert b"host@example.com" in data

    def test_attendee_email_included(self):
        data = generate_ics(
            "Visit",
            datetime(2025, 6, 15, 10, 0),
            attendee_email="renter@example.com",
        )
        assert b"ATTENDEE" in data
        assert b"renter@example.com" in data

    def test_uid_is_unique_across_calls(self):
        data1 = generate_ics("Visit", datetime(2025, 6, 15, 10, 0))
        data2 = generate_ics("Visit", datetime(2025, 6, 15, 10, 0))
        cal1, cal2 = parse_ics(data1), parse_ics(data2)
        uid1 = str(get_events(cal1)[0]["uid"])
        uid2 = str(get_events(cal2)[0]["uid"])
        assert uid1 != uid2

    def test_uid_contains_rento_domain(self):
        data = generate_ics("Visit", datetime(2025, 6, 15, 10, 0))
        assert b"rento.app" in data

    def test_method_is_request(self):
        data = generate_ics("Visit", datetime(2025, 6, 15, 10, 0))
        assert b"METHOD:REQUEST" in data

    def test_default_duration_is_60_minutes(self):
        start = datetime(2025, 7, 4, 10, 0)
        data = generate_ics("Visit", start)
        cal = parse_ics(data)
        event = get_events(cal)[0]

        def naive(dt):
            return dt.replace(tzinfo=None) if hasattr(dt, "replace") else dt

        diff = naive(event["dtend"].dt) - naive(event["dtstart"].dt)
        assert diff == timedelta(minutes=60)
