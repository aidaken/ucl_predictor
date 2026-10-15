"""League-phase table. Tiebreakers follow the 2026–27 UEFA criteria that apply during the phase."""

from __future__ import annotations

from typing import Any

# pts, gf, ga, away_gf, wins, away_wins
Row = list[int]


def empty_row() -> Row:
    return [0, 0, 0, 0, 0, 0]


def apply_result(rows: dict[str, Row], home: str, away: str, goals_home: int, goals_away: int) -> None:
    rows[home][1] += goals_home
    rows[home][2] += goals_away
    rows[away][1] += goals_away
    rows[away][2] += goals_home
    rows[away][3] += goals_away
    if goals_home > goals_away:
        rows[home][0] += 3
        rows[home][4] += 1
    elif goals_away > goals_home:
        rows[away][0] += 3
        rows[away][4] += 1
        rows[away][5] += 1
    else:
        rows[home][0] += 1
        rows[away][0] += 1


def rank_clubs(rows: dict[str, Row], coefficients: dict[str, float]) -> list[str]:
    """
    Best first.

    During the league phase UEFA ranks on points, goal difference, goals scored,
    away goals, wins, away wins. Coefficient is the last official separator and
    is what we use once the football criteria are level, so a bracket always
    has an order.
    """

    def key(club_id: str) -> tuple:
        pts, gf, ga, away_gf, wins, away_wins = rows[club_id]
        return (pts, gf - ga, gf, away_gf, wins, away_wins, coefficients.get(club_id, 0.0))

    return sorted(rows, key=key, reverse=True)


def standings_from_fixtures(
    club_ids: list[str],
    fixtures: list[dict[str, Any]],
    coefficients: dict[str, float],
) -> list[dict[str, Any]]:
    rows = {cid: empty_row() for cid in club_ids}
    for match in fixtures:
        if match.get("status") not in ("FT", "AET", "PEN"):
            continue
        home, away = match.get("team_home"), match.get("team_away")
        if home not in rows or away not in rows:
            continue
        if match.get("score_home") is None or match.get("score_away") is None:
            continue
        apply_result(rows, home, away, int(match["score_home"]), int(match["score_away"]))

    ordered = rank_clubs(rows, coefficients)
    table = []
    for index, cid in enumerate(ordered, start=1):
        pts, gf, ga, away_gf, wins, away_wins = rows[cid]
        played = wins + away_wins  # incomplete: draws missing
        # played = (3*wins_total + draws) isn't stored. Reconstruct:
        # We didn't store draws or losses. played = games that touched the row.
        # Count from goals? Not reliable for 0-0. Recompute played below.
        table.append({
            "club_id": cid,
            "rank": index,
            "points": pts,
            "gf": gf,
            "ga": ga,
            "gd": gf - ga,
            "away_gf": away_gf,
            "wins": wins,
            "away_wins": away_wins,
        })

    played_count = {cid: 0 for cid in club_ids}
    draws = {cid: 0 for cid in club_ids}
    losses = {cid: 0 for cid in club_ids}
    for match in fixtures:
        if match.get("status") not in ("FT", "AET", "PEN"):
            continue
        home, away = match.get("team_home"), match.get("team_away")
        if home not in played_count or away not in played_count:
            continue
        if match.get("score_home") is None or match.get("score_away") is None:
            continue
        sh, sa = int(match["score_home"]), int(match["score_away"])
        played_count[home] += 1
        played_count[away] += 1
        if sh == sa:
            draws[home] += 1
            draws[away] += 1
        elif sh < sa:
            losses[home] += 1
        else:
            losses[away] += 1

    for row in table:
        cid = row["club_id"]
        row["played"] = played_count[cid]
        row["draws"] = draws[cid]
        row["losses"] = losses[cid]
    return table


def template_from_played(
    club_ids: list[str],
    fixtures: list[dict[str, Any]],
) -> dict[str, Row]:
    rows = {cid: empty_row() for cid in club_ids}
    for match in fixtures:
        if match.get("status") not in ("FT", "AET", "PEN"):
            continue
        home, away = match.get("team_home"), match.get("team_away")
        if home not in rows or away not in rows:
            continue
        if match.get("score_home") is None or match.get("score_away") is None:
            continue
        apply_result(rows, home, away, int(match["score_home"]), int(match["score_away"]))
    return rows
