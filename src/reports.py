"""Short club notes built from the signals. No invented injury or team news."""

from __future__ import annotations

from typing import Any

import config


_COUNTRY = {
    "ENG": "English",
    "ESP": "Spanish",
    "GER": "German",
    "ITA": "Italian",
    "FRA": "French",
    "POR": "Portuguese",
    "NED": "Dutch",
    "BEL": "Belgian",
    "TUR": "Turkish",
    "AUT": "Austrian",
    "GRE": "Greek",
    "CZE": "Czech",
    "UKR": "Ukrainian",
    "NOR": "Norwegian",
    "SVK": "Slovak",
    "AZE": "Azerbaijani",
}


def injury_notes(rows: list[dict[str, Any]] | None) -> list[str]:
    notes: list[str] = []
    for row in rows or []:
        status = str(row.get("status") or "").strip()
        if not status or status.lower() == "questionable":
            continue
        name = row.get("name") or "Unnamed player"
        notes.append(f"{name} ({status})")
    return notes


def write_report(
    club: dict[str, Any],
    *,
    market: float | None,
    model_title: float | None,
    rest: dict[str, Any],
    injuries: list[str],
) -> str:
    name = club.get("name") or club.get("id")
    country = _COUNTRY.get(str(club.get("country") or ""), "their")
    sentences = [
        (
            f"{name} is rated from the {country} league level, then from the Champions League "
            "matches already played. European titles and the five-year coefficient are not a strength bonus."
        )
    ]
    if market is not None:
        sentences.append(f"Prediction markets put them at {market * 100:.1f}% to win the title.")
    else:
        sentences.append("No outright price was matched for them, so that signal is left out.")
    matches = int(club.get("form_matches") or 0)
    if matches:
        source = str(club.get("form_source") or "goals").replace("_", " ")
        sentences.append(
            f"The last {matches} matches ({source}) average "
            f"{club.get('avg_xg_for')} goals for and {club.get('avg_xg_against')} against, "
            "with Champions League games counted twice and domestic games counted once."
        )
    if rest.get("known"):
        comps = ", ".join(rest.get("competitions") or [])
        load = (
            f" Goal rates are trimmed to {rest.get('multiplier')}."
            if float(rest.get("multiplier") or 1) < 1
            else " That is a normal month, so rest stays neutral."
        )
        sentences.append(
            f"They have played {rest.get('matches')} times in the last {config.REST_WINDOW_DAYS} days ({comps})."
            + load
        )
    else:
        sentences.append("No domestic calendar was matched, so rest is left neutral.")
    if injuries:
        sentences.append("Confirmed absences: " + "; ".join(injuries) + ".")
    else:
        sentences.append("The injury feed has no confirmed absences on this run.")
    if market is not None and model_title is not None and abs(model_title - market) >= 0.02:
        gap = (model_title - market) * 100
        direction = "above" if gap > 0 else "below"
        sentences.append(
            f"The simulations finish {abs(gap):.1f} points {direction} that market price."
        )
    return " ".join(sentences)
