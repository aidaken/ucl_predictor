"""Build strengths and run the UCL Monte Carlo.

    python update.py --demo     # cached clubs + fixtures, no network
    python update.py            # same, and push to Neon when DATABASE_URL is set
    python update.py --live     # refresh fixtures, health, odds, squad values first
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Any

import config
from src.clubs import ClubRegistry
from src.elo import replay_from_seed
from src.injury import calculate_multipliers
from src.odds import get_implied_probs
from src.simulate import run as simulate
from src.store import upsert_run
from src.strength import compute_strength, shrink_xg_toward_neutral
from src.table import standings_from_fixtures
from src.utils import DATA_DIR, normalize_betting_probs, normalize_minmax, setup_logging, write_json
from src.value import get_squad_values
from src.xg import calculate_form_ratios

logger = setup_logging()


def _load() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    import json
    from pathlib import Path

    clubs_doc = json.loads((DATA_DIR / "clubs.json").read_text(encoding="utf-8"))
    fixtures_doc = json.loads((DATA_DIR / "fixtures.json").read_text(encoding="utf-8"))
    clubs = clubs_doc["clubs"] if "clubs" in clubs_doc else clubs_doc
    fixtures = fixtures_doc["fixtures"] if isinstance(fixtures_doc, dict) else fixtures_doc
    return clubs, fixtures


def _maybe_live(clubs: dict[str, dict[str, Any]], fixtures: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict, dict]:
    from src.fetch import FetchError, fetch_health_for_clubs, get_domestic_fixtures, get_ucl_fixtures

    registry = ClubRegistry(clubs)
    try:
        fresh = get_ucl_fixtures(registry)
    except FetchError as exc:
        logger.warning("UCL fixture refresh skipped: %s", exc)
        fresh = []
    domestic: list[dict[str, Any]] = []
    for club in clubs.values():
        try:
            domestic.extend(get_domestic_fixtures(registry, club))
        except Exception as exc:
            logger.warning("domestic fixtures skipped for %s: %s", club.get("name"), exc)
    if fresh:
        # Keep our hand-built ids, but let the API fill scores on matching pairs.
        by_pair = {}
        for match in fresh:
            key = tuple(sorted((match["team_home"], match["team_away"])))
            by_pair[key] = match
        for match in fixtures:
            key = tuple(sorted((match["team_home"], match["team_away"])))
            incoming = by_pair.get(key)
            if not incoming:
                continue
            if incoming.get("status") in ("FT", "AET", "PEN"):
                match["score_home"] = incoming["score_home"]
                match["score_away"] = incoming["score_away"]
                match["winner"] = incoming["winner"]
                match["status"] = incoming["status"]
                if incoming.get("date"):
                    match["date"] = incoming["date"]
    try:
        stats, injuries = fetch_health_for_clubs(clubs)
    except FetchError as exc:
        logger.warning("health refresh skipped: %s", exc)
        stats, injuries = {}, {}
    return domestic, stats, injuries


def build_payload(
    clubs: dict[str, dict[str, Any]],
    fixtures: list[dict[str, Any]],
    *,
    simulations: int,
    live: bool,
    stats: dict | None = None,
    injuries: dict | None = None,
    domestic: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    stats = stats or {}
    injuries = injuries or {}
    ids = list(clubs)

    for club in clubs.values():
        club["elo"] = float(club.get("elo_seed") or club["elo"])
    replay_from_seed(clubs, fixtures)

    form_fixtures = list(fixtures) + list(domestic or [])
    ratios, form_meta = calculate_form_ratios(form_fixtures, ids)
    coverage = sum(1 for tid in ids if form_meta.get(tid, {}).get("has_xg_data")) / max(len(ids), 1)
    for tid in ids:
        ratios[tid] = shrink_xg_toward_neutral(
            ratios.get(tid, 0.5),
            bool(form_meta.get(tid, {}).get("has_xg_data")),
            coverage,
        )

    values = get_squad_values(clubs, live=live)
    for cid, value in values.items():
        if cid in clubs:
            clubs[cid]["squad_value_eur"] = value

    registry = ClubRegistry(clubs)
    betting = get_implied_probs(registry, ids) or {}
    betting = normalize_betting_probs(betting, [tid for tid in ids if tid in betting]) if betting else {}
    # Renormalize across clubs that have a price. Missing clubs get no odds signal.
    if betting:
        total = sum(betting.values())
        betting = {tid: value / total for tid, value in betting.items()} if total else {}

    multipliers = calculate_multipliers(injuries, stats, ids)
    elo_norm = normalize_minmax({cid: float(clubs[cid]["elo"]) for cid in ids})
    value_norm = normalize_minmax({cid: float(values.get(cid, 0)) for cid in ids if values.get(cid)})
    equal_share = 1.0 / len(ids)

    for cid in ids:
        has_xg = form_meta.get(cid, {}).get("form_source") not in (None, "default")
        has_value = cid in value_norm
        has_betting = cid in betting
        components = {
            "elo_normalized": elo_norm[cid],
            "xg_form_ratio": ratios.get(cid, 0.5),
            "squad_value_normalized": value_norm.get(cid, 0.0),
            "betting_implied_prob": betting.get(cid, 0.0),
        }
        strength, weights = compute_strength(
            components,
            config.WEIGHTS,
            has_xg=has_xg,
            has_betting=has_betting,
            has_value=has_value,
        )
        meta = form_meta.get(cid, {})
        clubs[cid]["team_strength"] = strength
        clubs[cid]["injury_multiplier"] = multipliers.get(cid, 1.0)
        clubs[cid]["avg_xg_for"] = meta.get("avg_xg_for")
        clubs[cid]["avg_xg_against"] = meta.get("avg_xg_against")
        clubs[cid]["form_matches"] = meta.get("matches_used") or 0
        clubs[cid]["form_source"] = meta.get("form_source") or "default"
        clubs[cid]["has_xg"] = bool(meta.get("has_xg_data"))
        clubs[cid]["has_value"] = has_value
        clubs[cid]["has_betting"] = has_betting
        clubs[cid]["squad_value_normalized"] = value_norm.get(cid)
        clubs[cid]["betting_implied_prob"] = betting.get(cid)
        clubs[cid]["betting_equal_share"] = equal_share
        clubs[cid]["effective_weights"] = weights
        clubs[cid]["signals"] = {
            "elo": clubs[cid]["elo"],
            "elo_normalized": round(elo_norm[cid], 4),
            "xg_form_ratio": ratios.get(cid, 0.5),
            "form_source": clubs[cid]["form_source"],
            "sos_multiplier": meta.get("sos_multiplier", 1.0),
            "squad_value_eur": clubs[cid].get("squad_value_eur"),
            "squad_value_normalized": None if not has_value else round(value_norm[cid], 4),
            "betting_implied_prob": None if not has_betting else round(betting[cid], 4),
            "injury_multiplier": multipliers.get(cid, 1.0),
            "effective_weights": weights,
        }

    logger.info("simulating %s seasons", simulations)
    sim = simulate(clubs, fixtures, n=simulations, project=True)
    coefficients = {cid: float(clubs[cid].get("coefficient") or 0) for cid in ids}
    table = standings_from_fixtures(ids, fixtures, coefficients)
    names = {cid: clubs[cid]["name"] for cid in ids}

    table_rows = []
    for row in table:
        cid = row["club_id"]
        probs = sim["clubs"][cid]
        table_rows.append({
            **row,
            "name": names[cid],
            "top8_probability": probs["top8_probability"],
            "playoff_probability": probs["playoff_probability"],
            "eliminated_probability": probs["eliminated_probability"],
            "win_probability": probs["win_probability"],
        })

    club_rows = []
    for cid in sim["current_order"]:
        probs = sim["clubs"][cid]
        club_rows.append({
            "id": cid,
            "name": names[cid],
            "country": clubs[cid].get("country"),
            "elo": clubs[cid]["elo"],
            "strength": clubs[cid]["team_strength"],
            "injury_multiplier": clubs[cid]["injury_multiplier"],
            "signals": clubs[cid]["signals"],
            "probabilities": probs,
        })

    return {
        "_meta": {
            "model_version": config.MODEL_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "simulations": sim["simulations"],
            "weights": config.WEIGHTS,
            "home_advantage": config.HOME_ADV,
            "base_xg": config.BASE_XG,
            "competition": "UEFA Champions League 2026/27",
            "data_sources": {
                "fixtures": "uefa league phase through 14 Oct 2026, plus API-Football when --live",
                "elo": "UEFA coefficient prior (1480 + 3.6 * coefficient), replayed through played UCL matches",
                "health": "API-Football domestic league + UCL, 36 clubs only",
            },
        },
        "table": table_rows,
        "clubs": club_rows,
        "bracket": sim["bracket"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Update the UCL 2026-27 predictions")
    parser.add_argument("--demo", action="store_true", help="Cached data, fewer simulations")
    parser.add_argument("--live", action="store_true", help="Refresh fixtures, health, and squad values")
    parser.add_argument("--sims", type=int, default=None)
    args = parser.parse_args()

    clubs, fixtures = _load()
    simulations = args.sims or (config.DEMO_SIMULATIONS if args.demo else config.N_SIMULATIONS)
    if os.getenv("N_SIMULATIONS"):
        simulations = int(os.environ["N_SIMULATIONS"])

    domestic: list[dict[str, Any]] = []
    stats: dict = {}
    injuries: dict = {}
    if args.live and not args.demo:
        domestic, stats, injuries = _maybe_live(clubs, fixtures)

    payload = build_payload(
        clubs,
        fixtures,
        simulations=simulations,
        live=args.live and not args.demo,
        stats=stats,
        injuries=injuries,
        domestic=domestic,
    )
    out = DATA_DIR / "predictions.json"
    write_json(out, payload)
    logger.info("wrote %s", out)

    try:
        upsert_run(payload, clubs, fixtures, injuries)
    except Exception as exc:
        logger.warning("Neon upsert failed: %s", exc)


if __name__ == "__main__":
    main()
