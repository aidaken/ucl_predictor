"""League phase plus two-legged knockout Monte Carlo."""

from __future__ import annotations

import random
from typing import Any

import config
from src.poisson import expected_goals, pens_probability, sample_score
from src.table import apply_result, rank_clubs, template_from_played

# Playoff pair indexes into the ranked list (0 = 1st).
# 9th vs 24th, 10th vs 23rd, ... 16th vs 17th.
PLAYOFF_PAIRS = [(8, 23), (9, 22), (10, 21), (11, 20), (12, 19), (13, 18), (14, 17), (15, 16)]

# Round of 16: (league rank index, playoff-pair index whose winner they meet).
# 1st meets the winner of 16v17. 1st and 2nd sit in opposite halves.
R16_SLOTS = [(0, 7), (7, 0), (3, 4), (4, 3), (1, 6), (6, 1), (2, 5), (5, 2)]
QF_PAIRS = [(0, 1), (2, 3), (4, 5), (6, 7)]
SF_PAIRS = [(0, 1), (2, 3)]


def _lambdas_for(clubs: dict[str, dict[str, Any]]) -> dict[tuple[str, str], tuple[float, float]]:
    ids = list(clubs)
    out: dict[tuple[str, str], tuple[float, float]] = {}
    for home in ids:
        for away in ids:
            if home == away:
                continue
            out[(home, away)] = expected_goals(clubs[home], clubs[away], neutral=False)
    return out


def _neutral_lambda(clubs: dict[str, dict[str, Any]], a: str, b: str) -> tuple[float, float]:
    return expected_goals(clubs[a], clubs[b], neutral=True)


def play_two_legged(
    better: str,
    worse: str,
    lambdas: dict[tuple[str, str], tuple[float, float]],
    clubs: dict[str, dict[str, Any]],
    rng: random.Random,
) -> str:
    """
    Worse side hosts leg 1, better side hosts leg 2.
    Away goals do not count. Level aggregate goes to extra time, then penalties.
    """
    leg1_h, leg1_a = lambdas[(worse, better)]
    s1_worse, s1_better = sample_score(leg1_h, leg1_a, rng)
    leg2_h, leg2_a = lambdas[(better, worse)]
    s2_better, s2_worse = sample_score(leg2_h, leg2_a, rng)

    goals_better = s1_better + s2_better
    goals_worse = s1_worse + s2_worse
    if goals_better > goals_worse:
        return better
    if goals_worse > goals_better:
        return worse

    et_home, et_away = sample_score(leg2_h * config.ET_FRACTION, leg2_a * config.ET_FRACTION, rng)
    if et_home != et_away:
        return better if et_home > et_away else worse

    prob_better = pens_probability(
        float(clubs[better].get("elo") or 1600),
        float(clubs[worse].get("elo") or 1600),
    )
    return better if rng.random() < prob_better else worse


def aggregate_winner(
    leg1_home_goals: int,
    leg1_away_goals: int,
    leg2_home_goals: int,
    leg2_away_goals: int,
    *,
    leg1_home: str,
    leg2_home: str,
) -> str | None:
    """Pure aggregate. None means the tie is level and needs extra time."""
    goals_leg1_home = leg1_home_goals + leg2_away_goals
    goals_leg2_home = leg1_away_goals + leg2_home_goals
    if goals_leg1_home > goals_leg2_home:
        return leg1_home
    if goals_leg2_home > goals_leg1_home:
        return leg2_home
    return None


def _knockout(
    order: list[str],
    lambdas: dict[tuple[str, str], tuple[float, float]],
    clubs: dict[str, dict[str, Any]],
    rng: random.Random,
    reach: dict[str, dict[str, int]] | None = None,
) -> str:
    """Return the champion. `order` is best league rank first."""
    playoff_winners: list[str] = []
    for better_i, worse_i in PLAYOFF_PAIRS:
        better, worse = order[better_i], order[worse_i]
        winner = play_two_legged(better, worse, lambdas, clubs, rng)
        playoff_winners.append(winner)

    if reach is not None:
        for club_id in order[:8]:
            reach["r16"][club_id] += 1
        for club_id in playoff_winners:
            reach["r16"][club_id] += 1

    r16: list[str] = []
    for seed_i, pair_i in R16_SLOTS:
        seed = order[seed_i]
        opponent = playoff_winners[pair_i]
        # Top 8 are the higher seed and host the second leg.
        winner = play_two_legged(seed, opponent, lambdas, clubs, rng)
        r16.append(winner)

    def round_of(slots: list[str], pairs: list[tuple[int, int]], stage: str) -> list[str]:
        winners = []
        for i, j in pairs:
            a, b = slots[i], slots[j]
            better, worse = _higher_seed(a, b, order)
            winner = play_two_legged(better, worse, lambdas, clubs, rng)
            winners.append(winner)
            if reach is not None:
                reach[stage][a] += 1
                reach[stage][b] += 1
        return winners

    qf = round_of(r16, QF_PAIRS, "qf")
    sf = round_of(qf, SF_PAIRS, "sf")
    finalists = sf
    if reach is not None:
        for club_id in finalists:
            reach["final"][club_id] += 1

    a, b = finalists
    lam_a, lam_b = _neutral_lambda(clubs, a, b)
    ga, gb = sample_score(lam_a, lam_b, rng)
    if ga == gb:
        et_a, et_b = sample_score(lam_a * config.ET_FRACTION, lam_b * config.ET_FRACTION, rng)
        ga += et_a
        gb += et_b
    if ga != gb:
        return a if ga > gb else b
    prob_a = pens_probability(float(clubs[a].get("elo") or 1600), float(clubs[b].get("elo") or 1600))
    return a if rng.random() < prob_a else b


def _higher_seed(a: str, b: str, order: list[str]) -> tuple[str, str]:
    return (a, b) if order.index(a) < order.index(b) else (b, a)


def _play_final(
    a: str,
    b: str,
    clubs: dict[str, dict[str, Any]],
    rng: random.Random,
) -> str:
    lam_a, lam_b = _neutral_lambda(clubs, a, b)
    ga, gb = sample_score(lam_a, lam_b, rng)
    if ga == gb:
        et_a, et_b = sample_score(lam_a * config.ET_FRACTION, lam_b * config.ET_FRACTION, rng)
        ga += et_a
        gb += et_b
    if ga != gb:
        return a if ga > gb else b
    prob_a = pens_probability(float(clubs[a].get("elo") or 1600), float(clubs[b].get("elo") or 1600))
    return a if rng.random() < prob_a else b


def _top_side(counts: dict[str, int], wins: dict[str, int], n: int) -> dict[str, Any] | None:
    if not counts:
        return None
    club_id, present = max(counts.items(), key=lambda item: item[1])
    return {
        "id": club_id,
        "present": round(present / n, 4),
        "advance": round(wins.get(club_id, 0) / n, 4),
    }


def project_bracket(
    clubs: dict[str, dict[str, Any]],
    order: list[str],
    n: int,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Knockout tree if today's table never moved.
    Later rounds name the club most often on each side of the slot.
    """
    lambdas = _lambdas_for(clubs)
    rng = random.Random(seed)
    final_counts: dict[str, int] = {}

    fixed_playoff = []
    for better_i, worse_i in PLAYOFF_PAIRS:
        better, worse = order[better_i], order[worse_i]
        fixed_playoff.append({
            "leg1_home": worse,
            "leg2_home": better,
            "clubs": [better, worse],
            "wins": {better: 0, worse: 0},
        })

    fixed_r16 = []
    for seed_i, pair_i in R16_SLOTS:
        seed_club = order[seed_i]
        fixed_r16.append({
            "seed": seed_club,
            "pair_index": pair_i,
            "wins": {seed_club: 0},
            "opponents": {},
        })

    qf_sides = [({}, {}) for _ in QF_PAIRS]
    qf_wins: list[dict[str, int]] = [{} for _ in QF_PAIRS]
    sf_sides = [({}, {}) for _ in SF_PAIRS]
    sf_wins: list[dict[str, int]] = [{} for _ in SF_PAIRS]
    final_sides: tuple[dict[str, int], dict[str, int]] = ({}, {})
    final_wins: dict[str, int] = {}

    def _bump(bucket: dict[str, int], club_id: str) -> None:
        bucket[club_id] = bucket.get(club_id, 0) + 1

    for _ in range(n):
        winners = []
        for tie in fixed_playoff:
            better, worse = tie["clubs"]
            winner = play_two_legged(better, worse, lambdas, clubs, rng)
            tie["wins"][winner] += 1
            winners.append(winner)
        r16_winners = []
        for slot in fixed_r16:
            opponent = winners[slot["pair_index"]]
            slot["wins"].setdefault(opponent, 0)
            _bump(slot["opponents"], opponent)
            winner = play_two_legged(slot["seed"], opponent, lambdas, clubs, rng)
            slot["wins"][winner] = slot["wins"].get(winner, 0) + 1
            r16_winners.append(winner)
        qf = []
        for idx, (i, j) in enumerate(QF_PAIRS):
            a, b = r16_winners[i], r16_winners[j]
            _bump(qf_sides[idx][0], a)
            _bump(qf_sides[idx][1], b)
            better, worse = _higher_seed(a, b, order)
            winner = play_two_legged(better, worse, lambdas, clubs, rng)
            _bump(qf_wins[idx], winner)
            qf.append(winner)
        sf = []
        for idx, (i, j) in enumerate(SF_PAIRS):
            a, b = qf[i], qf[j]
            _bump(sf_sides[idx][0], a)
            _bump(sf_sides[idx][1], b)
            better, worse = _higher_seed(a, b, order)
            winner = play_two_legged(better, worse, lambdas, clubs, rng)
            _bump(sf_wins[idx], winner)
            sf.append(winner)
        _bump(final_sides[0], sf[0])
        _bump(final_sides[1], sf[1])
        champ = _play_final(sf[0], sf[1], clubs, rng)
        _bump(final_wins, champ)
        final_counts[champ] = final_counts.get(champ, 0) + 1

    def pack_playoff() -> list[dict[str, Any]]:
        packed = []
        for tie in fixed_playoff:
            better, worse = tie["clubs"]
            packed.append({
                "leg1_home": worse,
                "leg2_home": better,
                "advance": {
                    better: round(tie["wins"][better] / n, 4),
                    worse: round(tie["wins"][worse] / n, 4),
                },
            })
        return packed

    def pack_r16() -> list[dict[str, Any]]:
        packed = []
        for slot in fixed_r16:
            advance = {
                club: round(wins / n, 4)
                for club, wins in slot["wins"].items()
                if wins > 0
            }
            packed.append({"seed": slot["seed"], "advance": advance})
        return packed

    def side(club_id: str, advance: float, present: float = 1.0) -> dict[str, Any]:
        return {"id": club_id, "present": present, "advance": advance}

    playoff_ties = []
    for tie in fixed_playoff:
        better, worse = tie["clubs"]
        playoff_ties.append({
            "left": side(better, round(tie["wins"][better] / n, 4)),
            "right": side(worse, round(tie["wins"][worse] / n, 4)),
            "note": "Second leg at the higher seed",
        })

    r16_ties = []
    for slot in fixed_r16:
        opponent = _top_side(slot["opponents"], slot["wins"], n)
        r16_ties.append({
            "left": side(slot["seed"], round(slot["wins"].get(slot["seed"], 0) / n, 4)),
            "right": opponent,
            "note": "Most likely play-off winner on the right",
        })

    def pack_round(sides: list[tuple[dict[str, int], dict[str, int]]], wins: list[dict[str, int]], note: str):
        ties = []
        for idx, (left_counts, right_counts) in enumerate(sides):
            ties.append({
                "left": _top_side(left_counts, wins[idx], n),
                "right": _top_side(right_counts, wins[idx], n),
                "note": note,
            })
        return ties

    rounds = [
        {"id": "playoff", "label": "Play-off", "ties": playoff_ties},
        {"id": "r16", "label": "Round of 16", "ties": r16_ties},
        {
            "id": "qf",
            "label": "Quarter-final",
            "ties": pack_round(qf_sides, qf_wins, "Most likely club on each side"),
        },
        {
            "id": "sf",
            "label": "Semi-final",
            "ties": pack_round(sf_sides, sf_wins, "Most likely club on each side"),
        },
        {
            "id": "final",
            "label": "Final",
            "ties": [{
                "left": _top_side(final_sides[0], final_wins, n),
                "right": _top_side(final_sides[1], final_wins, n),
                "note": "Percent is the chance to win the final from this frozen table",
            }],
        },
    ]

    return {
        "playoff": pack_playoff(),
        "round_of_16": pack_r16(),
        "rounds": rounds,
        "frozen_champion": {
            club: round(count / n, 4) for club, count in final_counts.items()
        },
        "note": (
            "Bracket if the league table froze tonight. Each card is who most often "
            "stands on that side, and their chance of going through. "
            "The title odds above still resimulate the remaining matchdays."
        ),
    }


def run(
    clubs: dict[str, dict[str, Any]],
    fixtures: list[dict[str, Any]],
    n: int | None = None,
    seed: int = 42,
    *,
    project: bool = True,
) -> dict[str, Any]:
    simulations = n or config.N_SIMULATIONS
    ids = list(clubs)
    coefficients = {cid: float(clubs[cid].get("coefficient") or 0.0) for cid in ids}
    lambdas = _lambdas_for(clubs)
    remaining = [
        match for match in fixtures
        if match.get("status") not in ("FT", "AET", "PEN")
        and match.get("team_home") in clubs
        and match.get("team_away") in clubs
    ]
    template = template_from_played(ids, fixtures)

    top8 = {cid: 0 for cid in ids}
    playoff = {cid: 0 for cid in ids}
    eliminated = {cid: 0 for cid in ids}
    champion = {cid: 0 for cid in ids}
    reach = {
        stage: {cid: 0 for cid in ids}
        for stage in ("r16", "qf", "sf", "final")
    }
    rank_sum = {cid: 0 for cid in ids}

    rng = random.Random(seed)
    for _ in range(simulations):
        rows = {cid: template[cid][:] for cid in ids}
        for match in remaining:
            home, away = match["team_home"], match["team_away"]
            lam_h, lam_a = lambdas[(home, away)]
            gh, ga = sample_score(lam_h, lam_a, rng)
            apply_result(rows, home, away, gh, ga)
        order = rank_clubs(rows, coefficients)
        for index, cid in enumerate(order, start=1):
            rank_sum[cid] += index
            if index <= 8:
                top8[cid] += 1
            elif index <= 24:
                playoff[cid] += 1
            else:
                eliminated[cid] += 1
        winner = _knockout(order, lambdas, clubs, rng, reach)
        champion[winner] += 1

    clubs_out = {}
    for cid in ids:
        clubs_out[cid] = {
            "win_probability": round(champion[cid] / simulations, 4),
            "top8_probability": round(top8[cid] / simulations, 4),
            "playoff_probability": round(playoff[cid] / simulations, 4),
            "eliminated_probability": round(eliminated[cid] / simulations, 4),
            "reach_r16_probability": round(reach["r16"][cid] / simulations, 4),
            "reach_qf_probability": round(reach["qf"][cid] / simulations, 4),
            "reach_sf_probability": round(reach["sf"][cid] / simulations, 4),
            "reach_final_probability": round(reach["final"][cid] / simulations, 4),
            "mean_rank": round(rank_sum[cid] / simulations, 2),
        }

    current_order = rank_clubs(template, coefficients)
    bracket = project_bracket(clubs, current_order, n=min(simulations, 2000), seed=seed + 1) if project else {}

    return {
        "simulations": simulations,
        "clubs": clubs_out,
        "current_order": current_order,
        "bracket": bracket,
    }
