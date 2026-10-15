"""Squad values. Pinned euros are the default; a Transfermarkt page is optional."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests
from bs4 import BeautifulSoup

import config
from src.utils import DATA_DIR, load_json

logger = logging.getLogger("ucl")
VALUES_PATH = DATA_DIR / "squad_values.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
}


def load_squad_values() -> dict[str, int]:
    doc = load_json(VALUES_PATH)
    raw = doc.get("values_eur") or {}
    out: dict[str, int] = {}
    for tid, val in raw.items():
        try:
            out[str(tid)] = int(val)
        except (TypeError, ValueError):
            continue
    return out


def _parse_market_value(raw: str) -> int | None:
    if not raw:
        return None
    text = raw.strip().lower().replace("€", "").replace(",", ".")
    multiplier = 1
    if "bn" in text or "mrd" in text:
        multiplier = 1_000_000_000
    elif "m" in text:
        multiplier = 1_000_000
    elif "k" in text:
        multiplier = 1_000
    number = re.sub(r"[^0-9.]", "", text)
    try:
        return int(float(number) * multiplier)
    except ValueError:
        return None


def scrape_squad_value(slug: str) -> int | None:
    url = f"https://www.transfermarkt.com/{slug}/startseite/verein"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    node = soup.select_one(".data-header__market-value-wrapper")
    if node is None:
        return None
    return _parse_market_value(node.get_text(" ", strip=True))


def get_squad_values(clubs: dict[str, dict[str, Any]], *, live: bool = False) -> dict[str, int]:
    pinned = load_squad_values()
    if not live:
        return pinned

    values = dict(pinned)
    for cid, club in clubs.items():
        slug = club.get("transfermarkt_slug")
        if not slug:
            continue
        try:
            scraped = scrape_squad_value(slug)
            if scraped:
                values[cid] = scraped
            time.sleep(config.TRANSFERMARKT_DELAY_S)
        except Exception as exc:
            logger.warning("Transfermarkt failed for %s: %s", cid, exc)
    return values
