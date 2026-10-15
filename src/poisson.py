"""Independent Poisson goals. Home advantage sits on the home rate only."""

from __future__ import annotations

import math
import random
from typing import Any

import config


def clamp_lambda(value: float) -> float:
    return min(config.LAMBDA_MAX, max(config.LAMBDA_MIN, value))


def attack_defense(club: dict[str, Any]) -> tuple[float, float]:
    """
    Attack and defense indexes, 1.0 = baseline club.
    Elo sets the prior. xG (or a goals proxy) pulls it once there are matches.
    Squad value and outright odds tilt attack. They do not get fed back into Elo.
    """
    elo = float(club.get("elo") or config.ELO_BASELINE)
    elo_idx = (elo / config.ELO_BASELINE) ** config.ELO_EXPONENT

    games = float(club.get("form_matches") or 0)
    source = club.get("form_source") or "default"
    trust = min(1.0, games / config.XG_TRUST_GAMES)
    if source == "default":
        trust = 0.0
    elif source == "goals":
        trust *= 0.65

    blend = config.XG_BLEND * trust
    xgf = club.get("avg_xg_for")
    xga = club.get("avg_xg_against")

    if xgf is None or blend <= 0:
        attack = elo_idx
    else:
        xg_att = min(1.7, max(0.6, float(xgf) / config.BASE_XG))
        attack = (1.0 - blend) * elo_idx + blend * xg_att

    if xga is None or blend <= 0:
        defense = elo_idx
    else:
        xg_def = min(1.7, max(0.6, config.BASE_XG / max(float(xga), 0.45)))
        defense = (1.0 - blend) * elo_idx + blend * xg_def

    injury = float(club.get("injury_multiplier") or 1.0)
    attack *= injury
    defense *= 0.65 + 0.35 * injury

    parts: list[float] = []
    if club.get("has_value") and club.get("squad_value_normalized") is not None:
        parts.append(float(club["squad_value_normalized"]))
    if club.get("has_betting") and club.get("betting_implied_prob") is not None:
        # Implied probs are small (they sum to 1). Stretch the rank signal:
        # a club at 3x the equal share is hot, a club at 0 is cold.
        equal = float(club.get("betting_equal_share") or 0.0)
        implied = float(club["betting_implied_prob"])
        if equal > 0:
            parts.append(max(0.0, min(1.0, implied / (equal * 4.0))))
        else:
            parts.append(implied)
    if parts:
        idx = sum(parts) / len(parts)
        attack *= 1.0 + (idx - 0.5) * config.SQUAD_ODDS_TILT

    return max(attack, 0.2), max(defense, 0.2)


def expected_goals(
    home: dict[str, Any],
    away: dict[str, Any],
    *,
    neutral: bool = False,
) -> tuple[float, float]:
    att_h, def_h = attack_defense(home)
    att_a, def_a = attack_defense(away)
    adv = 1.0 if neutral else config.HOME_ADV
    lam_h = config.BASE_XG * adv * att_h / def_a
    lam_a = config.BASE_XG * att_a / def_h
    return clamp_lambda(lam_h), clamp_lambda(lam_a)


def sample_poisson(lam: float, rng: random.Random) -> int:
    """Knuth sampler. Fine for football lambdas, which sit well under 5."""
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    produced = 1.0
    count = 0
    while produced > limit:
        count += 1
        produced *= rng.random()
        if count > 16:
            break
    return count - 1


def sample_score(
    lam_home: float,
    lam_away: float,
    rng: random.Random,
) -> tuple[int, int]:
    return sample_poisson(lam_home, rng), sample_poisson(lam_away, rng)


def outcome_probs(lam_home: float, lam_away: float, max_goals: int = 8) -> tuple[float, float, float]:
    """Truncated independent Poisson: P(home win), P(draw), P(away win)."""
    def masses(lam: float) -> list[float]:
        raw = [math.exp(-lam) * lam ** k / math.factorial(k) for k in range(max_goals + 1)]
        total = sum(raw) or 1.0
        return [p / total for p in raw]

    home = masses(lam_home)
    away = masses(lam_away)
    p_home = p_draw = p_away = 0.0
    for i, hp in enumerate(home):
        for j, ap in enumerate(away):
            p = hp * ap
            if i > j:
                p_home += p
            elif i == j:
                p_draw += p
            else:
                p_away += p
    return p_home, p_draw, p_away


def pens_probability(better_elo: float, worse_elo: float) -> float:
    """P(better side wins a shootout). Shrunk hard toward 0.5."""
    raw = 1.0 / (1.0 + 10 ** ((worse_elo - better_elo) / config.PENS_ELO_SCALE))
    prob = 0.5 + (raw - 0.5) * config.PENS_SHRINK
    return min(0.62, max(0.38, prob))
