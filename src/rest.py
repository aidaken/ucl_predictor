"""Fixture load. A crowded month trims goal rates a little. It does not decide the season."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import config


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:10]).date()
    except ValueError:
        return None


def rest_factors(
    club_ids: list[str],
    fixtures: list[dict[str, Any]],
    *,
    as_of: str | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Count finished matches in the trailing window.

    Only calendars that include a domestic (or cup) match count as known.
    Champions League dates alone are not enough to call a club tired or fresh.
    """
    today = _as_date(as_of or config.AS_OF) or date.today()
    window = config.REST_WINDOW_DAYS
    by_club: dict[str, list[dict[str, Any]]] = {cid: [] for cid in club_ids}
    for match in fixtures:
        if match.get("status") not in ("FT", "AET", "PEN"):
            continue
        played = _as_date(match.get("date"))
        if played is None:
            continue
        age = (today - played).days
        if age < 0 or age > window:
            continue
        for side in (match.get("team_home"), match.get("team_away")):
            if side in by_club:
                by_club[side].append(match)

    out: dict[str, dict[str, Any]] = {}
    for cid, matches in by_club.items():
        competitions = sorted({
            str(match.get("competition") or (
                "Champions League"
                if match.get("stage") in ("league", "ucl", "knockout", "playoff")
                else "match"
            ))
            for match in matches
        })
        domestic = [
            match for match in matches
            if match.get("stage") not in ("league", "ucl", "knockout", "playoff")
        ]
        known = len(domestic) > 0
        extra = max(0, len(matches) - config.REST_BASELINE_MATCHES)
        multiplier = 1.0
        if known and extra:
            multiplier = max(config.REST_FLOOR, 1.0 - config.REST_EXTRA_PENALTY * extra)
        out[cid] = {
            "known": known,
            "matches": len(matches),
            "competitions": competitions,
            "multiplier": round(multiplier, 4),
        }
    return out
