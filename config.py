"""
config.py — knobs for the UCL 2026–27 engine.
Weights, scales, and league ids live here. Don't hardcode them in src/.
"""

import os

MODEL_VERSION = "1.1.0"

# Published strength blend. Must sum to 1.0.
# Lambdas do not use this blend. They use a league-level Elo prior, recent
# goals, then separate market and squad tilts. Past UCL titles are not an input.
WEIGHTS = {
    "elo": 0.22,
    "xg_form": 0.33,
    "squad_value": 0.10,
    "betting_odds": 0.35,
}

ELO_SCALE = 400
ELO_BASELINE = 1650.0
ELO_EXPONENT = 0.9

# Average goals per side. UCL league phase sits a bit under a wild domestic game.
BASE_XG = 1.40
# Home expected-goals multiplier.
# scripts/backtest.py on the first two matchdays (21 home wins, 3 draws, 12 away
# wins) keeps rewarding anything above 1.30, and the gain has not peaked by 1.60.
# That is two matchdays of a home-heavy start, so the prior stays at 1.28:
# better than 1.18 on the sample (Brier 0.530 vs 0.541) without chasing the edge.
HOME_ADV = 1.28
# Squad value nudges attack inside a league. It is depth, not a trophy count.
SQUAD_TILT = 0.12
# Outright markets (Polymarket, books) move attack and, more gently, defense.
MARKET_TILT = 0.45
# Within a league, the richest squad sits this far above the poorest, in Elo.
LEAGUE_SQUAD_SPREAD = 70.0
XG_BLEND = 0.55
XG_TRUST_GAMES = 6.0
LAMBDA_MIN = 0.15
LAMBDA_MAX = 4.2

# Extra time is 30 minutes, so about a third of a match, slightly deadened.
ET_FRACTION = 0.30
# Penalties shrink Elo toward a coin flip. 1.0 would be a full Elo gap.
PENS_ELO_SCALE = 800
PENS_SHRINK = 0.45

MAX_PLAYER_IMPORTANCE = 0.20
GK_PENALTY = 0.05
MIN_INJURY_MULTIPLIER = 0.75
KEY_PLAYERS_PER_TEAM = 2

# Name fragments. Injury rows match if the fragment is in the player name.
# A handful of attackers and keepers, not a full squad list.
KEY_PLAYER_NAMES = {
    "RMA": ["mbappé", "mbappe", "vinicius", "courtois"],
    "BAR": ["yamal", "lewandowski"],
    "MCI": ["haaland", "ederson"],
    "ARS": ["saka", "raya"],
    "LIV": ["salah", "alisson"],
    "BAY": ["kane", "musiala", "neuer"],
    "PSG": ["dembele", "dembélé", "donnarumma"],
    "INT": ["lautaro", "martinez", "sommer"],
    "ATM": ["griezmann", "oblak"],
    "MUN": ["bruno", "onana"],
    "NAP": ["osimhen", "kvara"],
    "DOR": ["guirassy", "kobel"],
}

K_KNOCKOUT = 50
K_LEAGUE = 40
K_DOMESTIC = 32

XG_FORM_GAMES = 6
XG_UCL_MATCH_WEIGHT = 2.0
XG_LUCK_THRESHOLD = 1.3
XG_COVERAGE_FULL = 0.75
XG_OPPONENT_ADJUST = True
XG_ADJ_CLAMP_LO = 0.70
XG_ADJ_CLAMP_HI = 1.35

N_SIMULATIONS = 8_000
DEMO_SIMULATIONS = 400

# Snapshot date for rest. Remaining matches are a season, so load is a trim,
# not a one-week fatigue tax on every kick.
AS_OF = "2026-10-15"
REST_WINDOW_DAYS = 28
REST_BASELINE_MATCHES = 4
REST_EXTRA_PENALTY = 0.012
REST_FLOOR = 0.94

POLYMARKET_EVENT_SLUG = "uefa-champions-league-2027-champion-20260701202025549"
POLYMARKET_GAMMA = "https://gamma-api.polymarket.com"

# Domestic league quality on a ClubElo-shaped scale. Same league, same base.
# A club's own European history does not add points on top.
LEAGUE_ELO = {
    "ENG": 1765,
    "ESP": 1755,
    "GER": 1750,
    "ITA": 1735,
    "FRA": 1725,
    "POR": 1665,
    "NED": 1655,
    "BEL": 1625,
    "TUR": 1615,
    "AUT": 1585,
    "GRE": 1575,
    "CZE": 1565,
    "UKR": 1555,
    "NOR": 1545,
    "SVK": 1525,
    "AZE": 1485,
}

# API-Football competition ids. Domestic ids are only queried for the 36 clubs.
UCL_LEAGUE_ID = 2
API_FOOTBALL_SEASON = 2026
DOMESTIC_LEAGUES = {
    "ENG": 39,
    "ESP": 140,
    "ITA": 135,
    "GER": 78,
    "FRA": 61,
    "NED": 88,
    "POR": 94,
    "BEL": 144,
    "TUR": 203,
    "CZE": 345,
    "SVK": 332,
    "NOR": 103,
    "AUT": 218,
    "GRE": 197,
    "UKR": 333,
    "AZE": 419,
}

API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_SPORT_KEY = "soccer_uefa_champs_league"
TRANSFERMARKT_DELAY_S = 2.0

MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2.0

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
