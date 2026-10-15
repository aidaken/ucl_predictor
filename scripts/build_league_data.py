"""Write data/clubs.json, data/fixtures.json, and data/squad_values.json from the 2026/27 league phase."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.utils import elo_from_coefficient, write_json  # noqa: E402

# id, name, country, domestic league, api-football id, coefficient, transfermarkt slug, pot, aliases
CLUBS = [
    ("PSG", "Paris Saint-Germain", "FRA", 61, 85, 132.000, "paris-saint-germain", 1, ["Paris", "PSG"]),
    ("BAY", "Bayern Munich", "GER", 78, 157, 147.500, "fc-bayern-munchen", 1, ["Bayern", "Bayern München"]),
    ("RMA", "Real Madrid", "ESP", 140, 541, 144.500, "real-madrid", 1, ["Real Madrid"]),
    ("LIV", "Liverpool", "ENG", 39, 40, 130.000, "fc-liverpool", 1, ["Liverpool"]),
    ("INT", "Inter", "ITA", 135, 505, 127.000, "inter-mailand", 1, ["Inter Milan", "Internazionale"]),
    ("MCI", "Manchester City", "ENG", 39, 50, 125.500, "manchester-city", 1, ["Man City"]),
    ("ARS", "Arsenal", "ENG", 39, 42, 119.000, "fc-arsenal", 1, ["Arsenal"]),
    ("BAR", "Barcelona", "ESP", 140, 529, 113.250, "fc-barcelona", 1, ["Barcelona"]),
    ("ATM", "Atlético Madrid", "ESP", 140, 530, 104.750, "atletico-madrid", 1, ["Atletico Madrid", "Atlético de Madrid"]),
    ("DOR", "Borussia Dortmund", "GER", 78, 165, 100.750, "borussia-dortmund", 2, ["Dortmund"]),
    ("ROM", "Roma", "ITA", 135, 497, 97.750, "as-rom", 2, ["AS Roma"]),
    ("SCP", "Sporting CP", "POR", 94, 228, 84.000, "sporting-lissabon", 2, ["Sporting"]),
    ("AVL", "Aston Villa", "ENG", 39, 66, 83.000, "aston-villa", 2, ["Aston Villa"]),
    ("POR", "Porto", "POR", 94, 212, 80.750, "fc-porto", 2, ["FC Porto"]),
    ("MUN", "Manchester United", "ENG", 39, 33, 76.500, "manchester-united", 2, ["Man United"]),
    ("BRU", "Club Brugge", "BEL", 144, 569, 75.250, "club-brugge-kv", 2, ["Club Brugge"]),
    ("BET", "Real Betis", "ESP", 140, 543, 74.500, "real-betis-sevilla", 2, ["Betis"]),
    ("PSV", "PSV Eindhoven", "NED", 88, 197, 71.250, "psv-eindhoven", 2, ["PSV"]),
    ("FEY", "Feyenoord", "NED", 88, 209, 71.000, "feyenoord-rotterdam", 3, ["Feyenoord"]),
    ("LIL", "Lille", "FRA", 61, 79, 68.750, "losc-lille", 3, ["LOSC"]),
    ("BOD", "Bodø/Glimt", "NOR", 103, None, 64.000, "fk-bodo-glimt", 3, ["Bodo/Glimt", "Bodo Glimt"]),
    ("NAP", "Napoli", "ITA", 135, 492, 63.000, "ssc-neapel", 3, ["Napoli"]),
    ("RBL", "RB Leipzig", "GER", 78, 173, 61.000, "rasenballsport-leipzig", 3, ["Leipzig"]),
    ("VIL", "Villarreal", "ESP", 140, 533, 59.000, "fc-villarreal", 3, ["Villarreal"]),
    ("FEN", "Fenerbahçe", "TUR", 203, 611, 57.750, "fenerbahce", 3, ["Fenerbahce"]),
    ("SHK", "Shakhtar Donetsk", "UKR", 333, 550, 56.250, "schachtar-donezk", 3, ["Shakhtar"]),
    ("GAL", "Galatasaray", "TUR", 203, 645, 53.500, "galatasaray", 3, ["Galatasaray"]),
    ("SLP", "Slavia Prague", "CZE", 345, None, 44.000, "slavia-prag", 4, ["Slavia Praha"]),
    ("SLO", "Slovan Bratislava", "SVK", 332, None, 36.000, "sk-slovan-bratislava", 4, ["Slovan"]),
    ("STU", "VfB Stuttgart", "GER", 78, 172, 27.500, "vfb-stuttgart", 4, ["Stuttgart"]),
    ("AEK", "AEK Athens", "GRE", 197, None, 24.000, "aek-athen", 4, ["AEK"]),
    ("LAS", "LASK", "AUT", 218, None, 21.000, "lask", 4, ["LASK Linz"]),
    ("COM", "Como", "ITA", 135, None, 19.989, "como-1907", 4, ["Como 1907"]),
    ("LEN", "Lens", "FRA", 61, 116, 16.699, "rc-lens", 4, ["RC Lens"]),
    ("VIK", "Viking", "NOR", 103, None, 8.247, "viking-fk", 4, ["Viking FK"]),
    ("SAB", "Sabah", "AZE", 419, None, 6.000, "sabah-fk", 4, ["Sabah FK"]),
]

# Pinned squad values in euros. Relative order matters more than the exact figure.
# Source: public Transfermarkt scale, frozen as an estimate until --live can scrape.
VALUES = {
    "RMA": 1_250_000_000, "MCI": 1_180_000_000, "ARS": 1_050_000_000, "BAR": 980_000_000,
    "BAY": 920_000_000, "LIV": 860_000_000, "PSG": 840_000_000, "MUN": 740_000_000,
    "INT": 620_000_000, "ATM": 560_000_000, "DOR": 480_000_000, "NAP": 430_000_000,
    "ROM": 400_000_000, "AVL": 390_000_000, "RBL": 360_000_000, "STU": 330_000_000,
    "POR": 310_000_000, "SCP": 300_000_000, "VIL": 240_000_000, "PSV": 230_000_000,
    "BRU": 210_000_000, "GAL": 200_000_000, "FEN": 190_000_000, "LIL": 185_000_000,
    "BET": 180_000_000, "FEY": 175_000_000, "COM": 160_000_000, "LEN": 155_000_000,
    "SHK": 110_000_000, "SLP": 70_000_000, "BOD": 55_000_000, "AEK": 48_000_000,
    "SLO": 32_000_000, "LAS": 28_000_000, "VIK": 22_000_000, "SAB": 15_000_000,
}

# matchday, date, home, away, score_home, score_away. None scores are unplayed.
MATCHES = [
    # Matchday 1
    (1, "2026-09-08", "AEK", "LAS", 1, 0),
    (1, "2026-09-08", "BRU", "AVL", 2, 3),
    (1, "2026-09-08", "DOR", "VIL", 3, 2),
    (1, "2026-09-08", "POR", "MCI", 0, 2),
    (1, "2026-09-08", "LIL", "BET", 2, 3),
    (1, "2026-09-08", "RMA", "INT", 2, 1),
    (1, "2026-09-09", "BAR", "FEY", 5, 1),
    (1, "2026-09-09", "STU", "VIK", 3, 1),
    (1, "2026-09-09", "LIV", "ATM", 2, 1),
    (1, "2026-09-09", "PSG", "SLO", 6, 1),
    (1, "2026-09-09", "SCP", "GAL", 3, 1),
    (1, "2026-09-09", "NAP", "ARS", 0, 1),
    (1, "2026-09-10", "FEN", "ROM", 1, 1),
    (1, "2026-09-10", "PSV", "SHK", 1, 1),
    (1, "2026-09-10", "COM", "RBL", 4, 1),
    (1, "2026-09-10", "BAY", "BOD", 5, 0),
    (1, "2026-09-10", "MUN", "SAB", 4, 0),
    (1, "2026-09-10", "SLP", "LEN", 2, 3),
    # Matchday 2 — results through 14 October 2026
    (2, "2026-10-14", "MCI", "PSG", 2, 4),
    (2, "2026-10-14", "VIK", "BAY", 3, 3),
    (2, "2026-10-14", "ROM", "RMA", 3, 4),
    (2, "2026-10-14", "LAS", "LIV", 3, 6),
    (2, "2026-10-14", "INT", "BRU", 3, 4),
    (2, "2026-10-14", "ARS", "LIL", 3, 0),
    (2, "2026-10-14", "GAL", "BAR", 1, 4),
    (2, "2026-10-14", "ATM", "MUN", 2, 0),
    (2, "2026-10-14", "BOD", "DOR", 1, 0),
    (2, "2026-10-14", "LEN", "SCP", 0, 2),
    (2, "2026-10-14", "AVL", "FEN", 6, 0),
    (2, "2026-10-14", "BET", "POR", 3, 2),
    (2, "2026-10-14", "RBL", "PSV", 1, 0),
    (2, "2026-10-14", "FEY", "COM", 3, 2),
    (2, "2026-10-14", "VIL", "NAP", 3, 1),
    (2, "2026-10-14", "SHK", "AEK", 3, 1),
    (2, "2026-10-14", "SAB", "SLP", 2, 0),
    (2, "2026-10-14", "SLO", "STU", 0, 3),
    # Matchday 3
    (3, "2026-10-20", "FEN", "SLP", None, None),
    (3, "2026-10-20", "SAB", "DOR", None, None),
    (3, "2026-10-20", "ROM", "SLO", None, None),
    (3, "2026-10-20", "POR", "PSV", None, None),
    (3, "2026-10-20", "LIV", "VIL", None, None),
    (3, "2026-10-20", "MCI", "AEK", None, None),
    (3, "2026-10-20", "PSG", "BAR", None, None),
    (3, "2026-10-20", "NAP", "BOD", None, None),
    (3, "2026-10-20", "STU", "ATM", None, None),
    (3, "2026-10-21", "COM", "MUN", None, None),
    (3, "2026-10-21", "LIL", "GAL", None, None),
    (3, "2026-10-21", "AVL", "VIK", None, None),
    (3, "2026-10-21", "BRU", "LEN", None, None),
    (3, "2026-10-21", "BAY", "ARS", None, None),
    (3, "2026-10-21", "INT", "SHK", None, None),
    (3, "2026-10-21", "RMA", "RBL", None, None),
    (3, "2026-10-21", "BET", "FEY", None, None),
    (3, "2026-10-21", "SCP", "LAS", None, None),
    # Matchday 4
    (4, "2026-11-03", "SHK", "SCP", None, None),
    (4, "2026-11-03", "GAL", "STU", None, None),
    (4, "2026-11-03", "ATM", "BAY", None, None),
    (4, "2026-11-03", "BAR", "AVL", None, None),
    (4, "2026-11-03", "FEY", "INT", None, None),
    (4, "2026-11-03", "BOD", "LIL", None, None),
    (4, "2026-11-03", "LAS", "SLO", None, None),
    (4, "2026-11-03", "MUN", "ROM", None, None),
    (4, "2026-11-03", "VIL", "PSG", None, None),
    (4, "2026-11-04", "AEK", "RMA", None, None),
    (4, "2026-11-04", "FEN", "LIV", None, None),
    (4, "2026-11-04", "DOR", "BET", None, None),
    (4, "2026-11-04", "POR", "NAP", None, None),
    (4, "2026-11-04", "PSV", "BRU", None, None),
    (4, "2026-11-04", "RBL", "MCI", None, None),
    (4, "2026-11-04", "LEN", "COM", None, None),
    (4, "2026-11-04", "SLP", "ARS", None, None),
    (4, "2026-11-04", "VIK", "SAB", None, None),
    # Matchday 5
    (5, "2026-11-24", "BOD", "LAS", None, None),
    (5, "2026-11-24", "GAL", "AVL", None, None),
    (5, "2026-11-24", "ARS", "DOR", None, None),
    (5, "2026-11-24", "COM", "AEK", None, None),
    (5, "2026-11-24", "FEY", "POR", None, None),
    (5, "2026-11-24", "MCI", "NAP", None, None),
    (5, "2026-11-24", "RBL", "LEN", None, None),
    (5, "2026-11-24", "RMA", "PSV", None, None),
    (5, "2026-11-24", "SLO", "BET", None, None),
    (5, "2026-11-25", "SAB", "BAR", None, None),
    (5, "2026-11-25", "SLP", "VIL", None, None),
    (5, "2026-11-25", "ATM", "VIK", None, None),
    (5, "2026-11-25", "BRU", "LIV", None, None),
    (5, "2026-11-25", "INT", "STU", None, None),
    (5, "2026-11-25", "SHK", "FEN", None, None),
    (5, "2026-11-25", "LIL", "BAY", None, None),
    (5, "2026-11-25", "PSG", "ROM", None, None),
    (5, "2026-11-25", "SCP", "MUN", None, None),
    # Matchday 6
    (6, "2026-12-08", "VIK", "FEY", None, None),
    (6, "2026-12-08", "VIL", "SAB", None, None),
    (6, "2026-12-08", "AEK", "GAL", None, None),
    (6, "2026-12-08", "ROM", "SCP", None, None),
    (6, "2026-12-08", "AVL", "PSG", None, None),
    (6, "2026-12-08", "BAR", "MCI", None, None),
    (6, "2026-12-08", "BAY", "SLP", None, None),
    (6, "2026-12-08", "MUN", "RBL", None, None),
    (6, "2026-12-08", "NAP", "BRU", None, None),
    (6, "2026-12-09", "BET", "COM", None, None),
    (6, "2026-12-09", "SLO", "SHK", None, None),
    (6, "2026-12-09", "ARS", "RMA", None, None),
    (6, "2026-12-09", "DOR", "INT", None, None),
    (6, "2026-12-09", "LAS", "FEN", None, None),
    (6, "2026-12-09", "LIV", "POR", None, None),
    (6, "2026-12-09", "PSV", "ATM", None, None),
    (6, "2026-12-09", "LEN", "BOD", None, None),
    (6, "2026-12-09", "STU", "LIL", None, None),
    # Matchday 7
    (7, "2027-01-19", "RMA", "LAS", None, None),
    (7, "2027-01-19", "INT", "LIV", None, None),
    (7, "2027-01-19", "BOD", "ATM", None, None),
    (7, "2027-01-19", "AVL", "DOR", None, None),
    (7, "2027-01-19", "AEK", "ROM", None, None),
    (7, "2027-01-19", "POR", "SLP", None, None),
    (7, "2027-01-19", "STU", "BRU", None, None),
    (7, "2027-01-19", "GAL", "FEY", None, None),
    (7, "2027-01-19", "LIL", "SLO", None, None),
    (7, "2027-01-20", "COM", "PSG", None, None),
    (7, "2027-01-20", "MUN", "BAY", None, None),
    (7, "2027-01-20", "LEN", "MCI", None, None),
    (7, "2027-01-20", "BET", "ARS", None, None),
    (7, "2027-01-20", "SCP", "BAR", None, None),
    (7, "2027-01-20", "VIK", "PSV", None, None),
    (7, "2027-01-20", "RBL", "SHK", None, None),
    (7, "2027-01-20", "FEN", "VIL", None, None),
    (7, "2027-01-20", "SAB", "NAP", None, None),
    # Matchday 8
    (8, "2027-01-27", "ARS", "SAB", None, None),
    (8, "2027-01-27", "ROM", "LIL", None, None),
    (8, "2027-01-27", "ATM", "FEN", None, None),
    (8, "2027-01-27", "DOR", "AEK", None, None),
    (8, "2027-01-27", "BRU", "BOD", None, None),
    (8, "2027-01-27", "BAY", "BET", None, None),
    (8, "2027-01-27", "BAR", "COM", None, None),
    (8, "2027-01-27", "SHK", "RMA", None, None),
    (8, "2027-01-27", "FEY", "RBL", None, None),
    (8, "2027-01-27", "LAS", "POR", None, None),
    (8, "2027-01-27", "LIV", "LEN", None, None),
    (8, "2027-01-27", "MCI", "SCP", None, None),
    (8, "2027-01-27", "PSG", "GAL", None, None),
    (8, "2027-01-27", "PSV", "STU", None, None),
    (8, "2027-01-27", "SLP", "AVL", None, None),
    (8, "2027-01-27", "NAP", "VIK", None, None),
    (8, "2027-01-27", "VIL", "MUN", None, None),
    (8, "2027-01-27", "SLO", "INT", None, None),
]


def main() -> None:
    ids = [row[0] for row in CLUBS]
    if len(ids) != 36 or len(set(ids)) != 36:
        raise SystemExit(f"expected 36 clubs, got {len(set(ids))}")
    if len(MATCHES) != 144:
        raise SystemExit(f"expected 144 matches, got {len(MATCHES)}")

    pairs = []
    home_away = {cid: [0, 0] for cid in ids}
    for matchday, _date, home, away, *_rest in MATCHES:
        if home not in home_away or away not in home_away:
            raise SystemExit(f"unknown club in MD{matchday}: {home} vs {away}")
        if home == away:
            raise SystemExit(f"club plays itself: {home}")
        key = tuple(sorted((home, away)))
        if key in pairs:
            raise SystemExit(f"duplicate fixture {home} vs {away}")
        pairs.append(key)
        home_away[home][0] += 1
        home_away[away][1] += 1

    bad = {cid: counts for cid, counts in home_away.items() if counts != [4, 4]}
    if bad:
        raise SystemExit(f"clubs without 4 home and 4 away: {bad}")

    clubs = {}
    for cid, name, country, league, api_id, coeff, slug, pot, aliases in CLUBS:
        elo = elo_from_coefficient(coeff)
        clubs[cid] = {
            "id": cid,
            "name": name,
            "country": country,
            "domestic_league_id": league,
            "api_football_id": api_id,
            "coefficient": coeff,
            "elo_seed": elo,
            "elo": elo,
            "transfermarkt_slug": slug,
            "pot": pot,
            "aliases": aliases,
            "squad_value_eur": VALUES[cid],
        }

    fixtures = []
    for index, (matchday, date, home, away, sh, sa) in enumerate(MATCHES, start=1):
        status = "FT" if sh is not None else "NS"
        winner = None
        if sh is not None and sa is not None:
            winner = home if sh > sa else away if sa > sh else None
        fixtures.append({
            "id": f"md{matchday}-{index:03d}",
            "matchday": matchday,
            "date": date,
            "team_home": home,
            "team_away": away,
            "score_home": sh,
            "score_away": sa,
            "winner": winner,
            "status": status,
            "stage": "league",
        })

    data = ROOT / "data"
    write_json(data / "clubs.json", {
        "_meta": {
            "competition": "UEFA Champions League 2026/27",
            "source": "UEFA league-phase list and coefficient pots",
            "elo_note": "elo_seed = 1480 + 3.6 * UEFA coefficient. ClubElo CSV replaces this when the file is present.",
        },
        "clubs": clubs,
    })
    write_json(data / "fixtures.json", {
        "_meta": {
            "played_through": "2026-10-14",
            "matchdays_played": 2,
            "source": "UEFA 2026/27 league phase fixtures and results",
        },
        "fixtures": fixtures,
    })
    write_json(data / "squad_values.json", {
        "_meta": {"source": "pinned estimate, relative Transfermarkt scale", "currency": "EUR"},
        "values_eur": VALUES,
    })
    print(f"wrote {len(clubs)} clubs and {len(fixtures)} fixtures")


if __name__ == "__main__":
    main()
