"""Unit tests for the UCL engine."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.injury import calculate_multipliers, merge_injuries, merge_player_stats
from src.poisson import expected_goals, outcome_probs
from src.simulate import PLAYOFF_PAIRS, R16_SLOTS, aggregate_winner, run
from src.strength import effective_weights
from src.table import standings_from_fixtures
from src.utils import elo_from_coefficient
from src.xg import calculate_form_ratios

ROOT = Path(__file__).resolve().parent.parent


def _club(elo: float, **extra) -> dict:
    base = {
        "elo": elo,
        "injury_multiplier": 1.0,
        "form_matches": 0,
        "form_source": "default",
        "has_value": False,
        "has_betting": False,
    }
    base.update(extra)
    return base


class TestTable(unittest.TestCase):
    def test_league_table_matches_published_order(self):
        doc = json.loads((ROOT / "data" / "fixtures.json").read_text(encoding="utf-8"))
        clubs = json.loads((ROOT / "data" / "clubs.json").read_text(encoding="utf-8"))["clubs"]
        coeffs = {cid: club["coefficient"] for cid, club in clubs.items()}
        table = standings_from_fixtures(list(clubs), doc["fixtures"], coeffs)
        top = [row["club_id"] for row in table[:9]]
        self.assertEqual(top, ["PSG", "BAR", "AVL", "STU", "LIV", "SCP", "ARS", "RMA", "BET"])
        self.assertEqual(table[0]["points"], 6)
        self.assertEqual(table[0]["gf"], 10)
        self.assertEqual(table[0]["gd"], 7)

    def test_goal_difference_before_coefficient(self):
        clubs = ["AAA", "BBB"]
        fixtures = [{
            "team_home": "AAA", "team_away": "BBB", "status": "FT",
            "score_home": 3, "score_away": 0,
        }]
        table = standings_from_fixtures(clubs, fixtures, {"AAA": 1, "BBB": 99})
        self.assertEqual(table[0]["club_id"], "AAA")


class TestPoisson(unittest.TestCase):
    def test_equal_sides_home_scores_more(self):
        home = _club(1700)
        away = _club(1700)
        lam_h, lam_a = expected_goals(home, away)
        self.assertGreater(lam_h, lam_a)

    def test_neutral_strips_home_advantage(self):
        home = _club(1700)
        away = _club(1700)
        lam_h, lam_a = expected_goals(home, away, neutral=True)
        self.assertAlmostEqual(lam_h, lam_a, places=4)

    def test_stronger_side_is_favourite(self):
        home = _club(1900)
        away = _club(1550)
        lam_h, lam_a = expected_goals(home, away, neutral=True)
        p_home, _draw, p_away = outcome_probs(lam_h, lam_a)
        self.assertGreater(p_home, p_away)

    def test_injury_cuts_attack(self):
        fit = _club(1800)
        hurt = _club(1800, injury_multiplier=0.8)
        lam_fit, _ = expected_goals(fit, _club(1700), neutral=True)
        lam_hurt, _ = expected_goals(hurt, _club(1700), neutral=True)
        self.assertLess(lam_hurt, lam_fit)


class TestKnockout(unittest.TestCase):
    def test_aggregate_ignores_away_goals(self):
        # 1-0 away, then 0-0 at home: the away side from leg 1 leads on aggregate.
        winner = aggregate_winner(0, 1, 0, 0, leg1_home="WORSE", leg2_home="BETTER")
        self.assertEqual(winner, "BETTER")

    def test_level_aggregate_is_unresolved(self):
        # 1-0, then 1-0 the other way. Away goals would have split this. Aggregate does not.
        winner = aggregate_winner(1, 0, 1, 0, leg1_home="WORSE", leg2_home="BETTER")
        self.assertIsNone(winner)

    def test_playoff_pairs_seeded_sides(self):
        self.assertEqual(PLAYOFF_PAIRS[0], (8, 23))
        self.assertEqual(PLAYOFF_PAIRS[-1], (15, 16))
        seeds = {slot[0] for slot in R16_SLOTS}
        self.assertEqual(seeds, set(range(8)))

    def test_heavy_favourite_usually_advances(self):
        clubs = {
            "BIG": _club(2050, coefficient=140),
            "SMALL": _club(1500, coefficient=10),
        }
        # One played match so the table has an order, plus no remaining fixtures.
        fixtures = [{
            "team_home": "BIG", "team_away": "SMALL", "status": "FT",
            "score_home": 1, "score_away": 0, "stage": "league", "date": "2026-09-08",
        }]
        # Two-club sim isn't a 36-team league. Exercise the tie directly.
        from src.simulate import play_two_legged, _lambdas_for
        import random

        lambdas = _lambdas_for(clubs)
        rng = random.Random(1)
        wins = 0
        for _ in range(200):
            if play_two_legged("BIG", "SMALL", lambdas, clubs, rng) == "BIG":
                wins += 1
        self.assertGreater(wins, 150)


class TestInjuries(unittest.TestCase):
    def test_merge_keeps_more_severe_status(self):
        rows = merge_injuries([
            {"player_id": 1, "name": "Saka", "status": "Questionable"},
            {"player_id": 1, "name": "Saka", "status": "Injured", "reason": "hamstring"},
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "Injured")
        self.assertEqual(rows[0]["reason"], "hamstring")

    def test_merge_stats_keeps_longer_sample(self):
        merged = merge_player_stats([
            {"player_id": 7, "name": "Haaland", "minutes": 180, "goals": 1},
            {"player_id": 7, "name": "Haaland", "minutes": 900, "goals": 12},
        ])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["minutes"], 900)

    def test_named_star_missing_drops_multiplier(self):
        stats = {
            "MCI": [{
                "player_id": 9,
                "name": "E. Haaland",
                "position": "Attacker",
                "goals": 10,
                "assists": 2,
                "minutes": 900,
                "xg_per90": 0.9,
                "xa_per90": 0.2,
                "is_starting_xi": True,
            }],
        }
        injuries = {
            "MCI": [{
                "player_id": 9,
                "name": "E. Haaland",
                "status": "Injured",
                "is_starting_xi": True,
            }],
        }
        multipliers = calculate_multipliers(injuries, stats, ["MCI"])
        self.assertLess(multipliers["MCI"], 1.0)
        self.assertGreaterEqual(multipliers["MCI"], 0.75)


class TestStrength(unittest.TestCase):
    def test_missing_xg_is_redistributed(self):
        weights = effective_weights(
            {"elo": 0.35, "xg_form": 0.30, "squad_value": 0.15, "betting_odds": 0.20},
            has_xg=False,
            has_betting=True,
        )
        self.assertNotIn("xg_form", weights)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=3)


class TestFormPrior(unittest.TestCase):
    def test_clean_sheets_do_not_zero_the_defense(self):
        fixtures = json.loads((ROOT / "data" / "fixtures.json").read_text(encoding="utf-8"))["fixtures"]
        _ratios, meta = calculate_form_ratios(fixtures, ["ARS"])
        self.assertGreater(meta["ARS"]["avg_xg_against"], 0.7)


class TestEloPrior(unittest.TestCase):
    def test_coefficient_orders_bayern_above_sabah(self):
        self.assertGreater(elo_from_coefficient(147.5), elo_from_coefficient(6))


class TestSimulationSmoke(unittest.TestCase):
    def test_probabilities_sum_and_favourite_leads(self):
        clubs_doc = json.loads((ROOT / "data" / "clubs.json").read_text(encoding="utf-8"))["clubs"]
        fixtures = json.loads((ROOT / "data" / "fixtures.json").read_text(encoding="utf-8"))["fixtures"]
        # Tiny field would break the 36-club bracket. Use the real 36, few sims.
        for club in clubs_doc.values():
            club["injury_multiplier"] = 1.0
            club["form_source"] = "default"
            club["form_matches"] = 0
            club["has_value"] = False
            club["has_betting"] = False
        result = run(clubs_doc, fixtures, n=30, seed=7, project=False)
        win_total = sum(row["win_probability"] for row in result["clubs"].values())
        self.assertAlmostEqual(win_total, 1.0, places=2)
        top8 = sum(row["top8_probability"] for row in result["clubs"].values())
        self.assertAlmostEqual(top8, 8.0, delta=0.05)
        # Bayern's prior is the highest coefficient, so they should not be a long shot.
        self.assertGreater(result["clubs"]["BAY"]["win_probability"], result["clubs"]["SAB"]["win_probability"])


if __name__ == "__main__":
    unittest.main()
