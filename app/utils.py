from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from dateutil import parser


def parse_iso_date(value: Any) -> Optional[date]:
    """Best-effort date parser.

    Sell custom field type 'date' might arrive as:
      - YYYY-MM-DD
      - MM/DD/YYYY
      - DD/MM/YYYY
    """
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        dt = parser.parse(str(value))
        return dt.date()
    except Exception:
        return None


def normalize_list_value(raw: Any) -> tuple[Optional[str], Optional[str]]:
    """Normalize Sell 'list' custom field values.

    Depending on endpoint/version, a list value may arrive as:
      - a plain string (label or code)
      - a number (option id)
      - an object like {"id": 1, "name": "ABC"}

    Returns (id, label) as strings when possible.
    """
    if raw is None:
        return None, None

    if isinstance(raw, dict):
        _id = raw.get("id")
        name = raw.get("name") or raw.get("label")
        return (str(_id) if _id is not None else None, str(name) if name is not None else None)

    if isinstance(raw, (int, float)):
        return str(int(raw)), None

    s = str(raw).strip()
    return (s if s else None, s if s else None)


def normalize_int(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, (int, float)):
        return int(raw)
    try:
        return int(str(raw).strip())
    except Exception:
        return None
