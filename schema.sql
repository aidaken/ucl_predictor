-- Applied automatically by src/store.py. Checked in so the shape is reviewable.

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
