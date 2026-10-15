"""Injury penalty. Only key players count, not the whole bench."""

from __future__ import annotations

from typing import Any

import config

# Higher means more likely to miss the next match.
_SEVERITY = {
    "questionable": 1,
    "doubtful": 2,
    "missing fixture": 3,
    "suspended": 3,
    "injury": 4,
    "injured": 4,
}


def _goal_involvement_per90(player: dict[str, Any]) -> float:
    goals = player.get("goals", 0) or 0
    assists = player.get("assists", 0) or 0
    minutes = player.get("minutes", 0) or 0
    if minutes <= 0:
        return 0.0
    return (goals + assists) / minutes * 90.0


def _name_hits(name: str, fragments: list[str]) -> bool:
    lowered = (name or "").lower()
    return any(fragment in lowered for fragment in fragments)


def identify_key_players(player_stats: list[dict[str, Any]], team_id: str) -> set[int | str]:
    """Overrides by name fragment, plus the top goal-involvement players."""
    key: set[int | str] = set()
    fragments = [n.lower() for n in config.KEY_PLAYER_NAMES.get(team_id, [])]
    for player in player_stats:
        player_id = player.get("player_id")
        if fragments and _name_hits(player.get("name", ""), fragments):
            key.add(player_id if player_id else (player.get("name") or "").lower())

    ranked = sorted(player_stats, key=_goal_involvement_per90, reverse=True)
    for player in ranked[: config.KEY_PLAYERS_PER_TEAM]:
        player_id = player.get("player_id")
        if player_id:
            key.add(player_id)
    return key


def _player_importance(player: dict[str, Any], team_avg: float) -> float:
    position = (player.get("position") or "").lower()
    if "goalkeeper" in position and player.get("is_starting_xi", True):
        return config.GK_PENALTY

    xg90 = player.get("xg_per90", 0.0) or 0.0
    xa90 = player.get("xa_per90", 0.0) or 0.0
    if team_avg <= 0:
        importance = 0.05
    else:
        importance = (xg90 + xa90) / team_avg
    return min(importance, config.MAX_PLAYER_IMPORTANCE)


def _team_offensive_avg(player_stats: list[dict[str, Any]]) -> float:
    totals = [
        (p.get("xg_per90", 0.0) or 0.0) + (p.get("xa_per90", 0.0) or 0.0)
        for p in player_stats
    ]
    if not totals:
        return 0.0
    return sum(totals) / len(totals)


def merge_player_stats(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Domestic and UCL stat lines for the same player collapse to the longer sample."""
    best: dict[Any, dict[str, Any]] = {}
    for row in rows:
        key = row.get("player_id") or (row.get("name") or "").lower()
        if not key:
            continue
        current = best.get(key)
        if current is None or (row.get("minutes") or 0) > (current.get("minutes") or 0):
            best[key] = row
    return list(best.values())


def merge_injuries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    One row per player across domestic + UCL injury feeds.
    The more severe status wins when both leagues report him.
    """
    best: dict[Any, dict[str, Any]] = {}
    for row in rows:
        key = row.get("player_id") or (row.get("name") or "").lower()
        if not key:
            continue
        current = best.get(key)
        severity = _SEVERITY.get(str(row.get("status") or "").lower(), 3)
        if current is None:
            best[key] = {**row, "_severity": severity}
            continue
        if severity >= current.get("_severity", 0):
            best[key] = {**current, **row, "_severity": severity}
    cleaned = []
    for row in best.values():
        row = dict(row)
        row.pop("_severity", None)
        cleaned.append(row)
    return cleaned


def _is_key(injury: dict[str, Any], key_players: set[int | str], fragments: list[str]) -> bool:
    player_id = injury.get("player_id")
    if player_id in key_players:
        return True
    name = (injury.get("name") or "").lower()
    if name and name in key_players:
        return True
    return bool(name) and _name_hits(name, fragments)


def calculate_multipliers(
    injuries_by_team: dict[str, list[dict[str, Any]]],
    player_stats_by_team: dict[str, list[dict[str, Any]]],
    team_ids: list[str],
) -> dict[str, float]:
    multipliers: dict[str, float] = {}

    for tid in team_ids:
        multiplier = 1.0
        team_players = player_stats_by_team.get(tid, [])
        team_avg = _team_offensive_avg(team_players)
        player_lookup = {p["player_id"]: p for p in team_players if p.get("player_id")}
        key_players = identify_key_players(team_players, tid)
        fragments = [n.lower() for n in config.KEY_PLAYER_NAMES.get(tid, [])]

        for injury in injuries_by_team.get(tid, []):
            if str(injury.get("status") or "").lower() == "questionable":
                continue
            if not _is_key(injury, key_players, fragments):
                continue
            player = player_lookup.get(injury.get("player_id"), {})
            merged = {**player, **injury}
            if not merged.get("is_starting_xi", True):
                continue
            multiplier -= _player_importance(merged, team_avg)

        multipliers[tid] = round(max(multiplier, config.MIN_INJURY_MULTIPLIER), 4)

    return multipliers
