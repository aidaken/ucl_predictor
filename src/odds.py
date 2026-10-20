"""Outright winner odds. Manual file wins when the API has no market."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

import config
from src.clubs import ClubRegistry
from src.utils import DATA_DIR, load_json, retry

logger = logging.getLogger("ucl")
MANUAL_ODDS_PATH = DATA_DIR / "manual_odds.json"


def load_manual_odds() -> dict[str, float]:
    """Values are decimal prices or already-implied probabilities (if <= 1)."""
    doc = load_json(MANUAL_ODDS_PATH)
    raw = doc.get("odds") or doc.get("clubs") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for tid, price in raw.items():
        try:
            value = float(price)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        out[str(tid)] = value if value <= 1 else 1.0 / value
    return out


@retry(max_attempts=2)
def _fetch_odds() -> list[dict[str, Any]]:
    api_key = os.getenv("ODDS_API_KEY", "").strip()
    if not api_key:
        return []
    url = f"{config.ODDS_API_BASE}/sports/{config.ODDS_SPORT_KEY}/odds"
    params = {
        "apiKey": api_key,
        "regions": "eu",
        "markets": "outrights",
        "oddsFormat": "decimal",
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("message"):
        raise RuntimeError(payload["message"])
    return payload


def get_implied_probs(registry: ClubRegistry, active: list[str]) -> dict[str, float] | None:
    manual = load_manual_odds()
    if manual:
        logger.info("using manual outright odds (%d clubs)", len(manual))
        return {tid: manual[tid] for tid in active if tid in manual} or None

    try:
        events = _fetch_odds()
    except Exception as exc:
        logger.warning("Odds API failed: %s", exc)
        return None
    if not events:
        logger.warning("Odds API unavailable")
        return None

    buckets: dict[str, list[float]] = {}
    for event in events:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market.get("key") != "outrights":
                    continue
                for outcome in market.get("outcomes", []):
                    price = outcome.get("price")
                    club_id = registry.resolve(outcome.get("name"))
                    if not club_id or not price or price <= 1:
                        continue
                    buckets.setdefault(club_id, []).append(1.0 / price)

    if not buckets:
        return None
    averaged = {tid: sum(probs) / len(probs) for tid, probs in buckets.items() if tid in active}
    return averaged or None
