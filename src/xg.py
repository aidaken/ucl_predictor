"""xG form. UCL matches count more than domestic ones. Goals stand in when xG is missing."""

from __future__ import annotations

from typing import Any

import config
from src.utils import DATA_DIR, load_json

MANUAL_XG_PATH = DATA_DIR / "manual_xg.json"


def load_manual_xg() -> dict[str, dict[str, float]]:
    doc = load_json(MANUAL_XG_PATH)
    raw = doc.get("xg") or doc.get("clubs") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, float]] = {}
    for tid, vals in raw.items():
        if not isinstance(vals, dict):
            continue
        try:
            entry: dict[str, float] = {"xg": float(vals["xg"]), "xga": float(vals["xga"])}
        except (KeyError, TypeError, ValueError):
            continue
        if vals.get("mp"):
            try:
                entry["mp"] = float(vals["mp"])
            except (TypeError, ValueError):
                pass
        out[str(tid)] = entry
    return out


def _match_weight(match: dict[str, Any]) -> float:
    if match.get("stage") in ("league", "ucl", "knockout", "playoff"):
        return config.XG_UCL_MATCH_WEIGHT
    return 1.0


def _clamp(value: float) -> float:
    return min(max(value, config.XG_ADJ_CLAMP_LO), config.XG_ADJ_CLAMP_HI)


def _perspective(match: dict[str, Any]) -> tuple[float, float, float, bool]:
    home = match["_perspective"] == "home"
    xg_for = match.get("xg_home") if home else match.get("xg_away")
    xg_against = match.get("xg_away") if home else match.get("xg_home")
    goals_for = match.get("score_home") if home else match.get("score_away")
    goals_against = match.get("score_away") if home else match.get("score_home")
    if xg_for is not None and xg_against is not None:
        return float(xg_for), float(xg_against), float(goals_for or 0), True
    gf = float(goals_for or 0)
    ga = float(goals_against or 0)
    return max(gf, 0.15), max(ga, 0.15), gf, False


def calculate_form_ratios(
    fixtures: list[dict[str, Any]],
    team_ids: list[str] | None = None,
) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
    by_team: dict[str, list[dict[str, Any]]] = {}
    for match in fixtures:
        if match.get("status") not in ("FT", "AET", "PEN"):
            continue
        home, away = match.get("team_home"), match.get("team_away")
        if home:
            by_team.setdefault(home, []).append({**match, "_perspective": "home"})
        if away:
            by_team.setdefault(away, []).append({**match, "_perspective": "away"})

    if team_ids:
        for tid in team_ids:
            by_team.setdefault(tid, [])

    for tid, matches in by_team.items():
        matches.sort(key=lambda m: m.get("date") or "", reverse=True)
        by_team[tid] = matches[: config.XG_FORM_GAMES]

    ratios: dict[str, float] = {}
    meta: dict[str, dict[str, Any]] = {}
    raw_rates: dict[str, dict[str, float]] = {}

    for tid, matches in by_team.items():
        if not matches:
            ratios[tid] = 0.5
            meta[tid] = {
                "has_xg_data": False,
                "matches_used": 0,
                "form_source": "default",
                "avg_xg_for": None,
                "avg_xg_against": None,
                "sos_multiplier": 1.0,
            }
            continue

        val_for = val_against = goals_for = weight_sum = 0.0
        any_xg = False
        opponents: list[str] = []
        for match in matches:
            weight = _match_weight(match)
            vf, va, gf, used_xg = _perspective(match)
            any_xg = any_xg or used_xg
            weight_sum += weight
            val_for += vf * weight
            val_against += va * weight
            goals_for += gf * weight
            opp = match.get("team_away") if match["_perspective"] == "home" else match.get("team_home")
            if opp:
                opponents.append(opp)

        avg_for = val_for / weight_sum
        avg_against = val_against / weight_sum
        # Two clean sheets are not a 0.15 xGA defense. Pull goal proxies toward the
        # league average so a short sample cannot dominate the Poisson rates.
        if not any_xg:
            prior_n = 6.0
            sample_n = float(len(matches))
            avg_for = (avg_for * sample_n + config.BASE_XG * prior_n) / (sample_n + prior_n)
            avg_against = (avg_against * sample_n + config.BASE_XG * prior_n) / (sample_n + prior_n)
        raw_rates[tid] = {"xgf": avg_for, "xga": avg_against, "opponents": opponents}  # type: ignore[dict-item]
        source = "xg" if any_xg else "goals"
        ratios[tid] = round(avg_for / (avg_for + avg_against), 4) if (avg_for + avg_against) else 0.5
        if any_xg and avg_for > 0 and (goals_for / weight_sum) / avg_for > config.XG_LUCK_THRESHOLD:
            ratios[tid] = min(ratios[tid], 0.55)
        meta[tid] = {
            "has_xg_data": any_xg,
            "matches_used": len(matches),
            "form_source": source,
            "avg_xg_for": round(avg_for, 3),
            "avg_xg_against": round(avg_against, 3),
            "sos_multiplier": 1.0,
            "opponents": opponents,
        }

    if config.XG_OPPONENT_ADJUST and raw_rates:
        league_xgf = sum(r["xgf"] for r in raw_rates.values()) / len(raw_rates)
        league_xga = sum(r["xga"] for r in raw_rates.values()) / len(raw_rates)
        for tid, rate in raw_rates.items():
            faced = [opp for opp in rate["opponents"] if opp in raw_rates]
            if not faced or league_xgf <= 0 or league_xga <= 0:
                continue
            opp_xga = sum(raw_rates[opp]["xga"] for opp in faced) / len(faced)
            opp_xgf = sum(raw_rates[opp]["xgf"] for opp in faced) / len(faced)
            att_mult = _clamp(league_xga / opp_xga) if opp_xga > 0 else 1.0
            def_mult = _clamp(league_xgf / opp_xgf) if opp_xgf > 0 else 1.0
            adj_for = rate["xgf"] * att_mult
            adj_against = rate["xga"] * def_mult
            denom = adj_for + adj_against
            ratios[tid] = round(adj_for / denom, 4) if denom else 0.5
            meta[tid]["avg_xg_for"] = round(adj_for, 3)
            meta[tid]["avg_xg_against"] = round(adj_against, 3)
            meta[tid]["sos_multiplier"] = round((att_mult + 1.0 / def_mult) / 2.0, 3)
            if meta[tid]["form_source"] in ("xg", "goals"):
                meta[tid]["form_source"] = meta[tid]["form_source"] + "_adj"

    manual = load_manual_xg()
    for tid, vals in manual.items():
        if team_ids is not None and tid not in team_ids:
            continue
        mp = vals.get("mp") or 1
        ratios[tid] = round(vals["xg"] / (vals["xg"] + vals["xga"]), 4) if (vals["xg"] + vals["xga"]) else 0.5
        meta[tid] = {
            "has_xg_data": True,
            "matches_used": int(mp),
            "form_source": "xg_table",
            "avg_xg_for": round(vals["xg"] / mp, 3),
            "avg_xg_against": round(vals["xga"] / mp, 3),
            "sos_multiplier": 1.0,
        }

    return ratios, meta
