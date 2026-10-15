"""
config.py — knobs for the UCL 2026–27 engine.
Weights, scales, and league ids live here. Don't hardcode them in src/.
"""

import os

MODEL_VERSION = "1.0.0"

# Signal blend for the published strength number. Must sum to 1.0.
# Match lambdas use Elo + xG directly; squad value and odds tilt attack on top.
WEIGHTS = {
    "elo": 0.35,
    "xg_form": 0.30,
    "squad_value": 0.15,
    "betting_odds": 0.20,
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
# How far squad value + outright odds pull attack off the Elo/xG rate.
SQUAD_ODDS_TILT = 0.22
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
