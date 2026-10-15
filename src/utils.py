"""Shared utilities: logging, retries, JSON I/O, normalization."""

from __future__ import annotations

import functools
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

from dotenv import load_dotenv

import config

load_dotenv()

T = TypeVar("T")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def setup_logging() -> logging.Logger:
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="[%(levelname)s]  %(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("ucl")


def retry(max_attempts: int | None = None, backoff_factor: float | None = None):
    attempts = max_attempts or config.MAX_RETRIES
    backoff = backoff_factor or config.RETRY_BACKOFF_FACTOR

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < attempts - 1:
                        time.sleep(backoff ** attempt)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


def load_json(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path | str, data: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def normalize_minmax(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    vmin = min(values.values())
    vmax = max(values.values())
    if vmax == vmin:
        return {k: 0.5 for k in values}
    return {k: (v - vmin) / (vmax - vmin) for k, v in values.items()}


def normalize_betting_probs(
    betting: dict[str, float],
    active_team_ids: list[str],
) -> dict[str, float]:
    if not active_team_ids:
        return {}
    raw = {tid: max(float(betting.get(tid, 0.0)), 0.0) for tid in active_team_ids}
    total = sum(raw.values())
    if total <= 0:
        equal = 1.0 / len(active_team_ids)
        return {tid: round(equal, 4) for tid in active_team_ids}
    return {tid: round(v / total, 4) for tid, v in raw.items()}


def elo_from_coefficient(coefficient: float) -> float:
    """Map a UEFA club coefficient onto a ClubElo-shaped rating when the CSV is down."""
    return round(1480.0 + float(coefficient) * 3.6, 1)
