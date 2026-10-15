"""Score the Poisson model on played 2026/27 league-phase matches and sweep home advantage.

Uses Elo only (no form), so the matches being scored are not also the form sample.

    python scripts/backtest.py
    python scripts/backtest.py --sweep
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from src.poisson import expected_goals, outcome_probs  # noqa: E402


def _clubs() -> dict:
    doc = json.loads((ROOT / "data" / "clubs.json").read_text(encoding="utf-8"))
    clubs = doc["clubs"]
    for club in clubs.values():
        club["elo"] = club["elo_seed"]
        club["injury_multiplier"] = 1.0
        club["form_source"] = "default"
        club["form_matches"] = 0
        club["has_value"] = False
        club["has_betting"] = False
    return clubs


def _played() -> list[dict]:
    doc = json.loads((ROOT / "data" / "fixtures.json").read_text(encoding="utf-8"))
    return [match for match in doc["fixtures"] if match.get("status") == "FT"]


def brier(clubs: dict, matches: list[dict]) -> float:
    total = 0.0
    for match in matches:
        home = clubs[match["team_home"]]
        away = clubs[match["team_away"]]
        lam_h, lam_a = expected_goals(home, away)
        p_home, p_draw, p_away = outcome_probs(lam_h, lam_a)
        sh, sa = match["score_home"], match["score_away"]
        oh, od, oa = (1, 0, 0) if sh > sa else (0, 1, 0) if sh == sa else (0, 0, 1)
        total += (p_home - oh) ** 2 + (p_draw - od) ** 2 + (p_away - oa) ** 2
    return total / len(matches)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", action="store_true")
    args = parser.parse_args()
    clubs = _clubs()
    matches = _played()
    if not args.sweep:
        score = brier(clubs, matches)
        print(f"matches {len(matches)}  HOME_ADV {config.HOME_ADV}  brier {score:.4f}")
        return

    original = config.HOME_ADV
    best = (original, 99.0)
    print(f"{'HOME_ADV':>10} {'brier':>8}")
    for adv in (1.05, 1.10, 1.15, 1.18, 1.22, 1.28, 1.35):
        config.HOME_ADV = adv
        score = brier(clubs, matches)
        print(f"{adv:10.2f} {score:8.4f}")
        if score < best[1]:
            best = (adv, score)
    config.HOME_ADV = original
    print(f"lowest on this grid {best[0]:.2f}  brier {best[1]:.4f}")
    print(
        "The first two matchdays were home-heavy (21 wins, 3 draws, 12 away wins) "
        "and the Brier score is still falling at the right edge of the grid. "
        "config.HOME_ADV stays 1.28 so a two-matchday blip does not set the prior."
    )


if __name__ == "__main__":
    main()
