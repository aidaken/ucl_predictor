"""Recent domestic results from the public ESPN scoreboard. Used for form and rest."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any

import requests

from src.clubs import ClubRegistry
from src.utils import DATA_DIR, load_json, write_json

logger = logging.getLogger("ucl")
CACHE_PATH = DATA_DIR / "other_fixtures.json"

# ESPN league slugs for the countries that actually have a 2026–27 UCL club.
LEAGUES = [
    ("eng.1", "Premier League"),
    ("esp.1", "La Liga"),
    ("ger.1", "Bundesliga"),
    ("ita.1", "Serie A"),
    ("fra.1", "Ligue 1"),
    ("por.1", "Primeira Liga"),
    ("ned.1", "Eredivisie"),
    ("bel.1", "Pro League"),
    ("tur.1", "Super Lig"),
    ("aut.1", "Bundesliga"),
    ("gre.1", "Super League"),
    ("cze.1", "Czech First League"),
    ("eng.league_cup", "League Cup"),
    ("esp.copa_del_rey", "Copa del Rey"),
    ("ger.dfb_pokal", "DFB-Pokal"),
    ("ita.coppa_italia", "Coppa Italia"),
    ("fra.coupe_de_france", "Coupe de France"),
]


def load_other_fixtures() -> list[dict[str, Any]]:
    doc = load_json(CACHE_PATH)
    rows = doc.get("fixtures") if isinstance(doc, dict) else None
    return list(rows) if isinstance(rows, list) else []


def _score(competitor: dict[str, Any]) -> int | None:
    raw = competitor.get("score")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def fetch_scoreboard(slug: str, day: date) -> list[dict[str, Any]]:
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"
    response = requests.get(url, params={"dates": day.strftime("%Y%m%d")}, timeout=20)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    return list(payload.get("events") or [])


def fixtures_from_events(
    events: list[dict[str, Any]],
    registry: ClubRegistry,
    competition: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        competitions = event.get("competitions") or []
        if not competitions:
            continue
        comp = competitions[0]
        status = ((comp.get("status") or {}).get("type") or {})
        if not status.get("completed"):
            continue
        home = away = None
        score_home = score_away = None
        for side in comp.get("competitors") or []:
            name = ((side.get("team") or {}).get("displayName")) or ""
            club_id = registry.resolve(name)
            goals = _score(side)
            if side.get("homeAway") == "home":
                home, score_home = club_id or f"ext:{name}", goals
            else:
                away, score_away = club_id or f"ext:{name}", goals
        if score_home is None or score_away is None:
            continue
        ours = [side for side in (home, away) if side and not str(side).startswith("ext:")]
        if not ours:
            continue
        winner = None
        if score_home > score_away:
            winner = home
        elif score_away > score_home:
            winner = away
        rows.append({
            "team_home": home,
            "team_away": away,
            "score_home": score_home,
            "score_away": score_away,
            "winner": winner,
            "status": "FT",
            "date": str(event.get("date") or "")[:10],
            "stage": "domestic",
            "competition": competition,
        })
    return rows


def refresh(clubs: dict[str, dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    """Pull completed matches and keep the ones that involve a UCL club."""
    registry = ClubRegistry(clubs)
    seen: set[tuple[str, str, str]] = set()
    kept: list[dict[str, Any]] = []
    jobs: list[tuple[date, str, str]] = []
    day = start
    while day <= end:
        for slug, competition in LEAGUES:
            jobs.append((day, slug, competition))
        day += timedelta(days=1)

    def _one(job: tuple[date, str, str]) -> list[dict[str, Any]]:
        played, slug, competition = job
        try:
            events = fetch_scoreboard(slug, played)
        except Exception as exc:
            logger.warning("ESPN %s %s skipped: %s", slug, played, exc)
            return []
        return fixtures_from_events(events, registry, competition)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_one, job) for job in jobs]
        for future in as_completed(futures):
            for row in future.result():
                key = (row["date"], str(row["team_home"]), str(row["team_away"]))
                if key in seen:
                    continue
                seen.add(key)
                kept.append(row)
    kept.sort(key=lambda row: row.get("date") or "")
    write_json(CACHE_PATH, {
        "_meta": {
            "source": "ESPN public scoreboard",
            "from": start.isoformat(),
            "to": end.isoformat(),
        },
        "fixtures": kept,
    })
    logger.info("saved %d other-competition matches", len(kept))
    return kept
