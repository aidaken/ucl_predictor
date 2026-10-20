"""Outright title markets. Polymarket is public. Books are used when a key exists."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import requests

import config
from src.clubs import ClubRegistry
from src.odds import get_implied_probs
from src.utils import DATA_DIR, load_json, write_json

logger = logging.getLogger("ucl")
CACHE_PATH = DATA_DIR / "markets.json"


def probs_from_polymarket_event(event: dict[str, Any], registry: ClubRegistry) -> dict[str, float]:
    """Yes-prices for named clubs. Placeholder outcomes such as 'Team H' are ignored."""
    out: dict[str, float] = {}
    for market in event.get("markets") or []:
        name = market.get("groupItemTitle") or ""
        folded = name.strip()
        if not folded or folded.lower() == "other" or folded.lower().startswith("team "):
            continue
        raw_prices = market.get("outcomePrices")
        if isinstance(raw_prices, str):
            try:
                raw_prices = json.loads(raw_prices)
            except json.JSONDecodeError:
                continue
        if not raw_prices:
            continue
        try:
            yes = float(raw_prices[0])
        except (TypeError, ValueError):
            continue
        if yes <= 0 or yes >= 0.49:
            continue
        club_id = registry.resolve(folded)
        if not club_id:
            logger.info("polymarket name unmatched: %s", folded)
            continue
        out[club_id] = yes
    return out


def _fetch_polymarket(registry: ClubRegistry) -> dict[str, float]:
    url = f"{config.POLYMARKET_GAMMA}/events"
    response = requests.get(url, params={"slug": config.POLYMARKET_EVENT_SLUG}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    event = payload[0] if isinstance(payload, list) else payload
    if not isinstance(event, dict):
        return {}
    probs = probs_from_polymarket_event(event, registry)
    if probs:
        write_json(CACHE_PATH, {
            "source": "polymarket",
            "slug": config.POLYMARKET_EVENT_SLUG,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "probs": {cid: round(p, 4) for cid, p in probs.items()},
        })
    return probs


def _cached() -> dict[str, float]:
    doc = load_json(CACHE_PATH)
    raw = doc.get("probs") or {}
    out: dict[str, float] = {}
    for cid, price in raw.items():
        try:
            value = float(price)
        except (TypeError, ValueError):
            continue
        if value > 0:
            out[str(cid)] = value
    return out


def _blend(sources: list[dict[str, float]], active: list[str]) -> dict[str, float]:
    """Average each source after it is scaled to sum to 1, on the clubs that source prices."""
    buckets: dict[str, list[float]] = {}
    allowed = set(active)
    for source in sources:
        if not source:
            continue
        kept = {cid: price for cid, price in source.items() if cid in allowed and price > 0}
        total = sum(kept.values())
        if total <= 0:
            continue
        for cid, price in kept.items():
            buckets.setdefault(cid, []).append(price / total)
    return {cid: sum(prices) / len(prices) for cid, prices in buckets.items()}


def get_market_probs(
    registry: ClubRegistry,
    active: list[str],
    *,
    refresh: bool,
) -> tuple[dict[str, float], str]:
    """
    Return (implied probs, source label).
    A failed live fetch falls back to the last saved Polymarket snapshot.
    """
    sources: list[tuple[str, dict[str, float]]] = []
    if refresh:
        try:
            live = _fetch_polymarket(registry)
            if live:
                sources.append(("polymarket", live))
        except Exception as exc:
            logger.warning("Polymarket fetch failed: %s", exc)
    if not any(label == "polymarket" for label, _ in sources):
        cached = _cached()
        if cached:
            sources.append(("polymarket-cache", cached))

    try:
        books = get_implied_probs(registry, active) or {}
    except Exception as exc:
        logger.warning("book odds failed: %s", exc)
        books = {}
    if books:
        sources.append(("books", books))

    blended = _blend([prices for _, prices in sources], active)
    label = "+".join(name for name, prices in sources if prices) or "none"
    return blended, label
