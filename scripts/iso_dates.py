"""Strict ISO date parsing shared by event facts and article publication dates."""
from datetime import date, datetime, time, timezone
import re


def iso_datetime(value, *, allow_date_only=False):
    """Parse an offset-bearing timestamp; optional dates use midnight UTC.

    Normalize only the UTC suffix for Python 3.9 compatibility. A missing offset
    is an error, never an invitation to infer the author's timezone.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError('date is missing or empty')
    value = value.strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        if not allow_date_only:
            raise ValueError('full timestamps require a timezone offset')
        return datetime.combine(date.fromisoformat(value), time(), timezone.utc)
    result = datetime.fromisoformat(value[:-1] + '+00:00' if value.endswith('Z') else value)
    if 'T' not in value or result.utcoffset() is None:
        raise ValueError('full timestamps require a timezone offset')
    return result
