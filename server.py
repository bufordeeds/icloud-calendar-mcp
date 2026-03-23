"""iCloud Calendar MCP Server — CalDAV interface for Apple Calendar."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import caldav
import dotenv
from dateutil import parser as dateutil_parser
from icalendar import Calendar, Event, vText
from mcp.server.fastmcp import FastMCP

dotenv.load_dotenv()

CALDAV_URL = "https://caldav.icloud.com"

mcp = FastMCP("icloud-calendar")


def _get_client() -> caldav.DAVClient:
    """Create a short-lived CalDAV client from env credentials."""
    email = os.environ.get("ICLOUD_EMAIL")
    password = os.environ.get("ICLOUD_APP_PASSWORD")
    if not email or not password:
        raise ValueError(
            "ICLOUD_EMAIL and ICLOUD_APP_PASSWORD must be set in environment or .env"
        )
    return caldav.DAVClient(url=CALDAV_URL, username=email, password=password)


def _get_principal() -> caldav.Principal:
    """Connect and return the CalDAV principal."""
    client = _get_client()
    return client.principal()


def _parse_dt(value) -> Optional[str]:
    """Convert a vDate/vDatetime/datetime to ISO 8601 string."""
    if value is None:
        return None
    dt = value.dt if hasattr(value, "dt") else value
    if isinstance(dt, datetime):
        return dt.isoformat()
    # date object (all-day event)
    return dt.isoformat()


def _extract_event_data(component) -> dict:
    """Extract relevant fields from a VEVENT component."""
    return {
        "uid": str(component.get("uid", "")),
        "summary": str(component.get("summary", "")),
        "dtstart": _parse_dt(component.get("dtstart")),
        "dtend": _parse_dt(component.get("dtend")),
        "description": str(component.get("description", "")),
        "location": str(component.get("location", "")),
        "status": str(component.get("status", "")),
        "organizer": str(component.get("organizer", "")),
    }


def _find_calendar_by_name_or_path(
    principal: caldav.Principal, calendar_id: str
) -> caldav.Calendar:
    """Find a calendar by name or path."""
    calendars = principal.calendars()
    for cal in calendars:
        if cal.name == calendar_id or str(cal.url) == calendar_id:
            return cal
    # Try partial path match
    for cal in calendars:
        if calendar_id in str(cal.url):
            return cal
    raise ValueError(f"Calendar not found: {calendar_id}")


def _find_event_by_uid(
    principal: caldav.Principal, uid: str, calendar_id: Optional[str] = None
) -> tuple[caldav.Calendar, caldav.Event]:
    """Find an event by UID, optionally scoped to a specific calendar."""
    if calendar_id:
        calendars = [_find_calendar_by_name_or_path(principal, calendar_id)]
    else:
        calendars = principal.calendars()

    for cal in calendars:
        try:
            event = cal.event_by_uid(uid)
            return cal, event
        except Exception:
            continue
    raise ValueError(f"Event with UID '{uid}' not found")


# --- Tools ---


@mcp.tool()
def list_calendars() -> list[dict]:
    """List all iCloud calendars with their name, URL path, and color if available."""
    principal = _get_principal()
    calendars = principal.calendars()
    results = []
    for cal in calendars:
        info = {
            "name": cal.name,
            "url": str(cal.url),
        }
        # Try to get color from properties
        try:
            props = cal.get_properties(
                [caldav.dav.DisplayName(), caldav.elements.ical.CalendarColor()]
            )
            for key, val in props.items():
                if "calendar-color" in str(key).lower():
                    info["color"] = str(val)
        except Exception:
            pass
        results.append(info)
    return results


@mcp.tool()
def list_events(
    calendar_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list[dict]:
    """List events from a calendar within a date range.

    Args:
        calendar_id: Calendar name or URL path.
        start: Start date in ISO 8601 format. Defaults to today.
        end: End date in ISO 8601 format. Defaults to 7 days from start.
    """
    principal = _get_principal()
    cal = _find_calendar_by_name_or_path(principal, calendar_id)

    now = datetime.now(timezone.utc)
    start_dt = dateutil_parser.isoparse(start) if start else now
    end_dt = dateutil_parser.isoparse(end) if end else start_dt + timedelta(days=7)

    # Ensure timezone awareness
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    events = cal.search(start=start_dt, end=end_dt, event=True, expand=True)
    results = []
    for event in events:
        ical = Calendar.from_ical(event.data)
        for component in ical.walk():
            if component.name == "VEVENT":
                results.append(_extract_event_data(component))
    return results


@mcp.tool()
def get_event(uid: str, calendar_id: Optional[str] = None) -> dict:
    """Get full details of a specific event by its UID.

    Args:
        uid: The event's unique identifier.
        calendar_id: Optional calendar name or URL to narrow the search.
    """
    principal = _get_principal()
    _, event = _find_event_by_uid(principal, uid, calendar_id)
    ical = Calendar.from_ical(event.data)
    for component in ical.walk():
        if component.name == "VEVENT":
            data = _extract_event_data(component)
            data["raw_ical"] = event.data
            return data
    raise ValueError(f"No VEVENT found in event with UID '{uid}'")


@mcp.tool()
def create_event(
    calendar_id: str,
    title: str,
    start: str,
    end: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
) -> dict:
    """Create a new event on a calendar.

    Args:
        calendar_id: Calendar name or URL path.
        title: Event title/summary.
        start: Start datetime in ISO 8601 format.
        end: End datetime in ISO 8601 format.
        description: Optional event description.
        location: Optional event location.
    """
    principal = _get_principal()
    cal = _find_calendar_by_name_or_path(principal, calendar_id)

    start_dt = dateutil_parser.isoparse(start)
    end_dt = dateutil_parser.isoparse(end)

    ical = Calendar()
    ical.add("prodid", "-//iCloud Calendar MCP//EN")
    ical.add("version", "2.0")

    vevent = Event()
    vevent.add("summary", title)
    vevent.add("dtstart", start_dt)
    vevent.add("dtend", end_dt)
    if description:
        vevent["description"] = vText(description)
    if location:
        vevent["location"] = vText(location)

    import uuid

    event_uid = str(uuid.uuid4())
    vevent.add("uid", event_uid)
    vevent.add("dtstamp", datetime.now(timezone.utc))

    ical.add_component(vevent)

    cal.save_event(ical.to_ical().decode("utf-8"))

    return {
        "uid": event_uid,
        "summary": title,
        "dtstart": start_dt.isoformat(),
        "dtend": end_dt.isoformat(),
        "description": description or "",
        "location": location or "",
        "status": "created",
    }


@mcp.tool()
def update_event(
    uid: str,
    calendar_id: Optional[str] = None,
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
) -> dict:
    """Update an existing event by UID. Only provided fields are changed.

    Args:
        uid: The event's unique identifier.
        calendar_id: Optional calendar name or URL to narrow the search.
        title: New event title.
        start: New start datetime in ISO 8601 format.
        end: New end datetime in ISO 8601 format.
        description: New description.
        location: New location.
    """
    principal = _get_principal()
    _, event = _find_event_by_uid(principal, uid, calendar_id)

    ical = Calendar.from_ical(event.data)
    modified = False

    for component in ical.walk():
        if component.name == "VEVENT":
            if title is not None:
                component["summary"] = vText(title)
                modified = True
            if start is not None:
                component.pop("dtstart", None)
                component.add("dtstart", dateutil_parser.isoparse(start))
                modified = True
            if end is not None:
                component.pop("dtend", None)
                component.add("dtend", dateutil_parser.isoparse(end))
                modified = True
            if description is not None:
                component["description"] = vText(description)
                modified = True
            if location is not None:
                component["location"] = vText(location)
                modified = True

    if not modified:
        return {"uid": uid, "status": "no changes"}

    event.data = ical.to_ical().decode("utf-8")
    event.save()

    # Re-read to confirm
    for component in ical.walk():
        if component.name == "VEVENT":
            data = _extract_event_data(component)
            data["status"] = "updated"
            return data

    return {"uid": uid, "status": "updated"}


@mcp.tool()
def delete_event(uid: str, calendar_id: Optional[str] = None) -> dict:
    """Delete an event by its UID.

    Args:
        uid: The event's unique identifier.
        calendar_id: Optional calendar name or URL to narrow the search.
    """
    principal = _get_principal()
    _, event = _find_event_by_uid(principal, uid, calendar_id)
    event.delete()
    return {"uid": uid, "status": "deleted"}


@mcp.tool()
def search_events(
    query: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> list[dict]:
    """Search events across all calendars by text query within a date range.

    Args:
        query: Text to search for in event summaries, descriptions, and locations.
        start: Start date in ISO 8601 format. Defaults to 30 days ago.
        end: End date in ISO 8601 format. Defaults to 30 days from now.
    """
    principal = _get_principal()
    calendars = principal.calendars()

    now = datetime.now(timezone.utc)
    start_dt = dateutil_parser.isoparse(start) if start else now - timedelta(days=30)
    end_dt = dateutil_parser.isoparse(end) if end else now + timedelta(days=30)

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    query_lower = query.lower()
    results = []

    for cal in calendars:
        try:
            events = cal.search(start=start_dt, end=end_dt, event=True, expand=True)
        except Exception:
            continue

        for event in events:
            ical = Calendar.from_ical(event.data)
            for component in ical.walk():
                if component.name == "VEVENT":
                    data = _extract_event_data(component)
                    searchable = " ".join(
                        [
                            data.get("summary", ""),
                            data.get("description", ""),
                            data.get("location", ""),
                        ]
                    ).lower()
                    if query_lower in searchable:
                        data["calendar"] = cal.name
                        results.append(data)

    return results


if __name__ == "__main__":
    mcp.run()
