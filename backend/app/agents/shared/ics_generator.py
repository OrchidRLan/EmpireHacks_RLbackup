import uuid as uuid_lib
from datetime import datetime, timedelta

from icalendar import Calendar, Event


def generate_ics(
    summary: str,
    start_dt: datetime,
    duration_minutes: int = 60,
    organizer_email: str = "",
    attendee_email: str = "",
    description: str = "",
    location: str = "",
) -> bytes:
    """Generate an ICS calendar file as bytes.

    Args:
        summary: Event title (e.g., "Apartment Visit - SoHo Studio #5A").
        start_dt: UTC datetime for the event start.
        duration_minutes: Event duration in minutes (default 60).
        organizer_email: Host/organizer email address.
        attendee_email: Renter/attendee email address.
        description: Event description text.
        location: Physical address or apartment name.

    Returns:
        ICS file content as bytes, suitable for email attachment.
    """
    cal = Calendar()
    cal.add("prodid", "-//Rento//Apartment Search//EN")
    cal.add("version", "2.0")
    cal.add("method", "REQUEST")

    event = Event()
    event.add("summary", summary)
    event.add("dtstart", start_dt)
    event.add("dtend", start_dt + timedelta(minutes=duration_minutes))
    event.add("dtstamp", datetime.utcnow())
    event["uid"] = str(uuid_lib.uuid4()) + "@rento.app"

    if description:
        event.add("description", description)
    if location:
        event.add("location", location)
    if organizer_email:
        event.add("organizer", f"mailto:{organizer_email}")
    if attendee_email:
        event.add("attendee", f"mailto:{attendee_email}")

    cal.add_component(event)
    return cal.to_ical()
