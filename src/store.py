"""Write a model run to Neon. Missing DATABASE_URL is a no-op so local runs still work."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("ucl")


def version_key(value: str | None) -> tuple[int, ...]:
    """Split a model version into numbers so 1.10.0 sorts after 1.9.0."""
    parts: list[int] = []
    for piece in str(value or "0").split("."):
        digits = ""
        for char in piece:
            if char.isdigit():
                digits += char
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_downgrade(incoming: str | None, stored: str | None) -> bool:
    """True when this run is an older model than one already stored."""
    if not stored:
        return False
    return version_key(incoming) < version_key(stored)

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id BIGSERIAL PRIMARY KEY,
    model_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    n_simulations INT NOT NULL,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    payload JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS clubs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT,
    domestic_league_id INT,
    api_football_id INT,
    coefficient DOUBLE PRECISION,
    elo DOUBLE PRECISION,
    elo_seed DOUBLE PRECISION,
    squad_value_eur BIGINT
);

CREATE TABLE IF NOT EXISTS fixtures (
    run_id BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    fixture_key TEXT NOT NULL,
    matchday INT,
    stage TEXT,
    home_id TEXT,
    away_id TEXT,
    score_home INT,
    score_away INT,
    status TEXT,
    kickoff DATE,
    PRIMARY KEY (run_id, fixture_key)
);

CREATE TABLE IF NOT EXISTS predictions (
    run_id BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    club_id TEXT NOT NULL,
    win_probability DOUBLE PRECISION,
    top8_probability DOUBLE PRECISION,
    playoff_probability DOUBLE PRECISION,
    eliminated_probability DOUBLE PRECISION,
    reach_r16_probability DOUBLE PRECISION,
    reach_qf_probability DOUBLE PRECISION,
    reach_sf_probability DOUBLE PRECISION,
    reach_final_probability DOUBLE PRECISION,
    strength DOUBLE PRECISION,
    injury_multiplier DOUBLE PRECISION,
    signals JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (run_id, club_id)
);

CREATE TABLE IF NOT EXISTS injuries (
    run_id BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    club_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    status TEXT,
    reason TEXT,
    PRIMARY KEY (run_id, club_id, player_name)
);
"""


def upsert_run(payload: dict[str, Any], clubs: dict[str, dict[str, Any]], fixtures: list[dict[str, Any]], injuries: dict[str, list[dict[str, Any]]]) -> int | None:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        logger.info("DATABASE_URL not set, skipping Neon")
        return None

    import psycopg

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
            meta = payload.get("_meta") or {}
            incoming = str(meta.get("model_version") or "0")
            cur.execute("SELECT model_version FROM runs")
            stored = [row[0] for row in cur.fetchall()]
            newest = max(stored, key=version_key) if stored else None
            if is_downgrade(incoming, newest):
                logger.error(
                    "refusing Neon write: model %s is older than stored %s",
                    incoming,
                    newest,
                )
                return None
            cur.execute(
                """
                INSERT INTO runs (model_version, n_simulations, meta, payload)
                VALUES (%s, %s, %s::jsonb, %s::jsonb)
                RETURNING id
                """,
                (
                    meta.get("model_version", "unknown"),
                    int(meta.get("simulations") or 0),
                    json.dumps(meta),
                    json.dumps(payload),
                ),
            )
            run_id = cur.fetchone()[0]

            for cid, club in clubs.items():
                cur.execute(
                    """
                    INSERT INTO clubs (
                        id, name, country, domestic_league_id, api_football_id,
                        coefficient, elo, elo_seed, squad_value_eur
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        country = EXCLUDED.country,
                        domestic_league_id = EXCLUDED.domestic_league_id,
                        api_football_id = EXCLUDED.api_football_id,
                        coefficient = EXCLUDED.coefficient,
                        elo = EXCLUDED.elo,
                        elo_seed = EXCLUDED.elo_seed,
                        squad_value_eur = EXCLUDED.squad_value_eur
                    """,
                    (
                        cid,
                        club.get("name"),
                        club.get("country"),
                        club.get("domestic_league_id"),
                        club.get("api_football_id"),
                        club.get("coefficient"),
                        club.get("elo"),
                        club.get("elo_seed"),
                        club.get("squad_value_eur"),
                    ),
                )

            preds = {row["id"]: row for row in payload.get("clubs") or []}
            for cid, row in preds.items():
                probs = row.get("probabilities") or {}
                cur.execute(
                    """
                    INSERT INTO predictions (
                        run_id, club_id, win_probability, top8_probability,
                        playoff_probability, eliminated_probability,
                        reach_r16_probability, reach_qf_probability,
                        reach_sf_probability, reach_final_probability,
                        strength, injury_multiplier, signals
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                    )
                    """,
                    (
                        run_id,
                        cid,
                        probs.get("win_probability"),
                        probs.get("top8_probability"),
                        probs.get("playoff_probability"),
                        probs.get("eliminated_probability"),
                        probs.get("reach_r16_probability"),
                        probs.get("reach_qf_probability"),
                        probs.get("reach_sf_probability"),
                        probs.get("reach_final_probability"),
                        row.get("strength"),
                        row.get("injury_multiplier"),
                        json.dumps(row.get("signals") or {}),
                    ),
                )

            for index, match in enumerate(fixtures):
                key = match.get("id") or f"{match.get('team_home')}-{match.get('team_away')}-{match.get('date')}"
                cur.execute(
                    """
                    INSERT INTO fixtures (
                        run_id, fixture_key, matchday, stage, home_id, away_id,
                        score_home, score_away, status, kickoff
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        str(key),
                        match.get("matchday"),
                        match.get("stage"),
                        match.get("team_home"),
                        match.get("team_away"),
                        match.get("score_home"),
                        match.get("score_away"),
                        match.get("status"),
                        match.get("date") or None,
                    ),
                )
                if index > 400:
                    break

            for cid, rows in injuries.items():
                for injury in rows:
                    name = injury.get("name") or str(injury.get("player_id") or "unknown")
                    cur.execute(
                        """
                        INSERT INTO injuries (run_id, club_id, player_name, status, reason)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (run_id, club_id, player_name) DO NOTHING
                        """,
                        (run_id, cid, name[:120], injury.get("status"), injury.get("reason")),
                    )
        conn.commit()
    logger.info("wrote Neon run %s", run_id)
    return int(run_id)
