"""Elo updates. Ratings are replayed from the pre-league seed every run."""

from __future__ import annotations

from typing import Any

import config


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / config.ELO_SCALE))


def k_factor_for_match(match: dict[str, Any]) -> int:
    stage = match.get("stage", "league")
    if stage in ("knockout", "playoff"):
        return config.K_KNOCKOUT
    if stage == "domestic":
        return config.K_DOMESTIC
    return config.K_LEAGUE


def update_ratings(
    teams: dict[str, dict[str, Any]],
    fixtures: list[dict[str, Any]],
) -> dict[str, float]:
    """Apply completed fixtures in date order. `teams` is mutated."""
    ordered = sorted(fixtures, key=lambda match: match.get("date") or "")
    changes = {tid: 0.0 for tid in teams}
    for match in ordered:
        if match.get("status") not in ("FT", "AET", "PEN"):
            continue
        home, away = match.get("team_home"), match.get("team_away")
        if home not in teams or away not in teams:
            continue
        winner = match.get("winner")
        if winner is None and match.get("score_home") is not None:
            sh, sa = int(match["score_home"]), int(match["score_away"])
            winner = home if sh > sa else away if sa > sh else None
        if winner == home:
            score_h, score_a = 1.0, 0.0
        elif winner == away:
            score_h, score_a = 0.0, 1.0
        else:
            score_h, score_a = 0.5, 0.5

        k = k_factor_for_match(match)
        r_h = float(teams[home]["elo"])
        r_a = float(teams[away]["elo"])
        delta_h = k * (score_h - expected_score(r_h, r_a))
        delta_a = k * (score_a - expected_score(r_a, r_h))
        teams[home]["elo"] = round(r_h + delta_h, 1)
        teams[away]["elo"] = round(r_a + delta_a, 1)
        changes[home] = changes.get(home, 0.0) + delta_h
        changes[away] = changes.get(away, 0.0) + delta_a
    return changes


def assign_rating_seeds(clubs: dict[str, dict[str, Any]]) -> None:
    """
    Seed each club from the league it plays in, plus a small squad-value gap
    inside that league. The UEFA coefficient is not used.
    """
    by_country: dict[str, list[str]] = {}
    for cid, club in clubs.items():
        by_country.setdefault(str(club.get("country") or ""), []).append(cid)
    for country, ids in by_country.items():
        base = float(config.LEAGUE_ELO.get(country, 1600))
        values = [float(clubs[cid].get("squad_value_eur") or 0) for cid in ids]
        lo, hi = min(values), max(values)
        for cid, value in zip(ids, values):
            if hi == lo or value <= 0:
                bump = 0.0
            else:
                bump = ((value - lo) / (hi - lo) - 0.5) * config.LEAGUE_SQUAD_SPREAD
            clubs[cid]["rating_seed"] = round(base + bump, 1)


def replay_from_seed(
    clubs: dict[str, dict[str, Any]],
    fixtures: list[dict[str, Any]],
) -> dict[str, float]:
    """Reset every club to its rating seed, then replay UCL results."""
    work = {}
    for cid, club in clubs.items():
        seed = club.get("rating_seed")
        if seed is None:
            seed = club.get("elo_seed") or club.get("elo") or config.ELO_BASELINE
        work[cid] = {"elo": float(seed)}
    before = {cid: work[cid]["elo"] for cid in work}
    update_ratings(work, fixtures)
    for cid, row in work.items():
        clubs[cid]["elo"] = row["elo"]
        clubs[cid]["elo_change"] = round(row["elo"] - before[cid], 1)
    return {cid: clubs[cid]["elo_change"] for cid in clubs}
