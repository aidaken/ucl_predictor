"""API-Football client. Injuries and player stats are read per club, domestic league plus UCL."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

import config
from src.clubs import ClubRegistry
from src.injury import merge_injuries, merge_player_stats
from src.utils import retry

logger = logging.getLogger("ucl")


class FetchError(Exception):
    """API-Football refused the call or the key is missing."""


def _api_key() -> str:
    key = os.getenv("API_FOOTBALL_KEY", "").strip()
    if not key:
        raise FetchError("API_FOOTBALL_KEY not set")
    return key


def _headers() -> dict[str, str]:
    return {"x-apisports-key": _api_key()}


@retry()
def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{config.API_FOOTBALL_BASE}{path}"
    response = requests.get(url, headers=_headers(), params=params or {}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    errors = payload.get("errors")
    if errors:
        raise FetchError(str(errors))
    return payload


def _normalize_fixture(item: dict[str, Any], registry: ClubRegistry, stage: str) -> dict[str, Any]:
    fixture = item.get("fixture", {})
    teams = item.get("teams", {})
    goals = item.get("goals", {})
    score = item.get("score", {})
    status = fixture.get("status", {}).get("short", "NS")
    home = teams.get("home", {})
    away = teams.get("away", {})
    home_id = registry.resolve(home.get("id")) or registry.resolve(home.get("name"))
    away_id = registry.resolve(away.get("id")) or registry.resolve(away.get("name"))
    sh, sa = goals.get("home"), goals.get("away")
    winner = None
    if status in ("FT", "AET", "PEN") and sh is not None and sa is not None:
        if sh > sa:
            winner = home_id
        elif sa > sh:
            winner = away_id
        elif status == "PEN":
            pen = score.get("penalty") or {}
            if (pen.get("home") or 0) > (pen.get("away") or 0):
                winner = home_id
            elif (pen.get("away") or 0) > (pen.get("home") or 0):
                winner = away_id
    return {
        "api_fixture_id": fixture.get("id"),
        "date": (fixture.get("date") or "")[:10],
        "team_home": home_id,
        "team_away": away_id,
        "score_home": sh,
        "score_away": sa,
        "winner": winner,
        "status": status,
        "xg_home": None,
        "xg_away": None,
        "stage": stage,
        "round": (item.get("league") or {}).get("round"),
    }


def get_ucl_fixtures(registry: ClubRegistry) -> list[dict[str, Any]]:
    payload = _get("/fixtures", {"league": config.UCL_LEAGUE_ID, "season": config.API_FOOTBALL_SEASON})
    fixtures = []
    for item in payload.get("response", []):
        round_name = ((item.get("league") or {}).get("round") or "").lower()
        if "league" in round_name or "group" in round_name:
            stage = "league"
        elif "play-off" in round_name or "playoff" in round_name:
            stage = "playoff"
        else:
            stage = "knockout"
        fixtures.append(_normalize_fixture(item, registry, stage))
    return [match for match in fixtures if match.get("team_home") and match.get("team_away")]


def get_domestic_fixtures(registry: ClubRegistry, club: dict[str, Any]) -> list[dict[str, Any]]:
    """Last domestic results for one UCL club. Used as form, not as the UCL table."""
    league_id = club.get("domestic_league_id")
    api_id = club.get("api_football_id")
    if not league_id or not api_id:
        return []
    payload = _get("/fixtures", {
        "league": league_id,
        "season": config.API_FOOTBALL_SEASON,
        "team": api_id,
        "last": 8,
    })
    out = []
    for item in payload.get("response", []):
        match = _normalize_fixture(item, registry, stage="domestic")
        # Domestic opponents outside the 36 won't resolve. Keep the UCL club's side
        # only when both clubs are in the registry; otherwise skip. Form still gets
        # the UCL matches, and a goals line is enough when the opponent is known.
        if match.get("team_home") and match.get("team_away"):
            out.append(match)
    return out


def _player_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    players = []
    for block in payload.get("response", []):
        player = block.get("player", {})
        stats = (block.get("statistics") or [{}])[0]
        games = stats.get("games") or {}
        goals = stats.get("goals") or {}
        minutes = games.get("minutes") or 0
        played = max((minutes or 0) / 90.0, 0.01)
        appearances = games.get("appearences") or games.get("appearances") or 0
        players.append({
            "player_id": player.get("id"),
            "name": player.get("name"),
            "position": games.get("position"),
            "goals": goals.get("total") or 0,
            "assists": goals.get("assists") or 0,
            "minutes": minutes or 0,
            "xg_per90": (goals.get("total") or 0) / played,
            "xa_per90": (goals.get("assists") or 0) / played,
            "is_starting_xi": appearances >= 3,
        })
    return players


def _injury_rows(payload: dict[str, Any], starters: set[int]) -> list[dict[str, Any]]:
    injuries = []
    for item in payload.get("response", []):
        player = item.get("player", {})
        player_id = player.get("id")
        injuries.append({
            "player_id": player_id,
            "name": player.get("name"),
            "status": player.get("type") or "Injured",
            "reason": player.get("reason"),
            "is_starting_xi": player_id in starters,
        })
    return injuries


def get_club_health(club: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Player stats and injuries for one club, from its domestic league and the UCL.
    Either feed can fail. The caller still gets whatever came back.
    """
    api_id = club.get("api_football_id")
    if not api_id:
        return [], []

    leagues = []
    if club.get("domestic_league_id"):
        leagues.append(int(club["domestic_league_id"]))
    if config.UCL_LEAGUE_ID not in leagues:
        leagues.append(config.UCL_LEAGUE_ID)

    stat_rows: list[dict[str, Any]] = []
    injury_rows: list[dict[str, Any]] = []
    for league_id in leagues:
        params = {"league": league_id, "season": config.API_FOOTBALL_SEASON, "team": api_id}
        try:
            stat_rows.extend(_player_rows(_get("/players", params)))
        except Exception as exc:
            logger.warning("player stats failed league %s team %s: %s", league_id, api_id, exc)
        try:
            injury_rows.extend(_injury_rows(_get("/injuries", params), set()))
        except Exception as exc:
            logger.warning("injuries failed league %s team %s: %s", league_id, api_id, exc)

    stats = merge_player_stats(stat_rows)
    starters = {p["player_id"] for p in stats if p.get("is_starting_xi") and p.get("player_id")}
    for row in injury_rows:
        if row.get("player_id") in starters:
            row["is_starting_xi"] = True
    return stats, merge_injuries(injury_rows)


def fetch_health_for_clubs(
    clubs: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    stats: dict[str, list[dict[str, Any]]] = {}
    injuries: dict[str, list[dict[str, Any]]] = {}
    for cid, club in clubs.items():
        try:
            club_stats, club_injuries = get_club_health(club)
        except FetchError as exc:
            logger.warning("health skipped for %s: %s", cid, exc)
            continue
        stats[cid] = club_stats
        injuries[cid] = club_injuries
    return stats, injuries
