"""Team strength composition — per-club weight redistribution when signals are missing."""

from __future__ import annotations


def effective_weights(
    base_weights: dict[str, float],
    *,
    has_xg: bool,
    has_betting: bool,
    has_value: bool = True,
) -> dict[str, float]:
    """
    Redistribute weight from missing signals onto the ones we actually have.
    """
    w = dict(base_weights)
    pool = 0.0
    if not has_xg:
        pool += w.pop("xg_form", 0.0)
    if not has_betting:
        pool += w.pop("betting_odds", 0.0)
    if not has_value:
        pool += w.pop("squad_value", 0.0)

    if pool <= 0:
        total = sum(w.values())
        return {k: v / total for k, v in w.items()} if total else w

    receivers = [k for k in w if w[k] > 0]
    if not receivers:
        return base_weights

    receiver_sum = sum(w[k] for k in receivers)
    for key in receivers:
        w[key] += pool * (w[key] / receiver_sum)

    total = sum(w.values())
    return {k: round(v / total, 6) for k, v in w.items()} if total else w


def compute_strength(
    components: dict[str, float],
    weights: dict[str, float],
    *,
    has_xg: bool,
    has_betting: bool,
    has_value: bool = True,
) -> tuple[float, dict[str, float]]:
    """Return (team_strength, effective_weights_used). Injury is applied later on the rates."""
    eff = effective_weights(
        weights, has_xg=has_xg, has_betting=has_betting, has_value=has_value,
    )
    base = (
        components["elo_normalized"] * eff.get("elo", 0.0)
        + components["xg_form_ratio"] * eff.get("xg_form", 0.0)
        + components["squad_value_normalized"] * eff.get("squad_value", 0.0)
        + components["betting_implied_prob"] * eff.get("betting_odds", 0.0)
    )
    return round(base, 4), eff


def shrink_xg_toward_neutral(ratio: float, has_xg: bool, coverage: float) -> float:
    """When few clubs have real xG, pull form toward 0.5."""
    if not has_xg:
        return 0.5
    if coverage >= 0.75:
        return ratio
    return round(0.5 + (ratio - 0.5) * coverage, 4)
