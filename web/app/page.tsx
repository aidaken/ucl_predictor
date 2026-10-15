"use client";

import { Fragment, useEffect, useState } from "react";

type Probs = {
  win_probability: number;
  top8_probability: number;
  playoff_probability: number;
  eliminated_probability: number;
  reach_r16_probability: number;
  reach_qf_probability: number;
  reach_sf_probability: number;
  reach_final_probability: number;
};

type Club = {
  id: string;
  name: string;
  elo: number;
  strength: number;
  injury_multiplier: number;
  signals: Record<string, unknown>;
  probabilities: Probs;
};

type TableRow = {
  club_id: string;
  rank: number;
  name: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  gd: number;
  points: number;
  top8_probability: number;
  playoff_probability: number;
  eliminated_probability: number;
  win_probability: number;
};

type Payload = {
  _meta: { model_version: string; simulations: number; generated_at: string; home_advantage: number };
  table: TableRow[];
  clubs: Club[];
  bracket: {
    note?: string;
    playoff?: Array<{ leg1_home: string; leg2_home: string; advance: Record<string, number> }>;
    round_of_16?: Array<{ seed: string; advance: Record<string, number> }>;
  };
};

function pct(value: number | undefined) {
  return `${((value || 0) * 100).toFixed(1)}%`;
}

function zone(rank: number) {
  if (rank <= 8) return "zone-direct";
  if (rank <= 16) return "zone-seed";
  if (rank <= 24) return "zone-playoff";
  return "zone-out";
}

export default function Page() {
  const [data, setData] = useState<Payload | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/predictions")
      .then(async (response) => {
        if (!response.ok) throw new Error("predictions unavailable");
        return response.json();
      })
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <main className="wrap"><p>{error}</p></main>;
  if (!data) return <main className="wrap"><p>Loading the league…</p></main>;

  const names = Object.fromEntries(data.clubs.map((club) => [club.id, club.name]));
  const byTitle = [...data.clubs].sort(
    (a, b) => b.probabilities.win_probability - a.probabilities.win_probability,
  );
  const favourite = byTitle[0];

  return (
    <main className="wrap">
      <header>
        <div>
          <p className="kicker">UEFA Champions League</p>
          <h1>2026–27 predictor</h1>
        </div>
        <p className="meta">
          model {data._meta.model_version}
          <br />
          {data._meta.simulations.toLocaleString()} seasons
          <br />
          {new Date(data._meta.generated_at).toUTCString()}
        </p>
      </header>

      <section className="hero">
        <article className="card">
          <p className="kicker">Title favourite</p>
          <h2>{favourite.name}</h2>
          <p className="pct">{pct(favourite.probabilities.win_probability)} to win it</p>
          <p className="note">
            Final {pct(favourite.probabilities.reach_final_probability)} ·
            semis {pct(favourite.probabilities.reach_sf_probability)} ·
            top 8 {pct(favourite.probabilities.top8_probability)}
          </p>
        </article>
        <article className="card">
          <p className="kicker">Title odds</p>
          <div className="bars">
            {byTitle.slice(0, 8).map((club) => (
              <div className="bar-row" key={club.id}>
                <span>{club.name}</span>
                <div className="track">
                  <div className="fill" style={{ width: `${Math.max(club.probabilities.win_probability / (favourite.probabilities.win_probability || 1), 0.04) * 100}%` }} />
                </div>
                <span>{pct(club.probabilities.win_probability)}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <h2 className="section-title">League phase</h2>
      <p className="note">Green is a direct round-of-16 place. Gold is a seeded playoff. The rest of the top 24 play unseeded. Click a club for the signals behind the rating.</p>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Club</th>
              <th className="num">P</th>
              <th className="num">W-D-L</th>
              <th className="num">GD</th>
              <th className="num">Pts</th>
              <th className="num">Top 8</th>
              <th className="num">Playoff</th>
              <th className="num">Out</th>
              <th className="num">Title</th>
            </tr>
          </thead>
          <tbody>
            {data.table.map((row) => {
              const club = data.clubs.find((item) => item.id === row.club_id);
              const signals = club?.signals || {};
              return (
                <Fragment key={row.club_id}>
                  <tr className={zone(row.rank)}>
                    <td>{row.rank}</td>
                    <td>
                      <button className="linkish" onClick={() => setOpen(open === row.club_id ? null : row.club_id)}>
                        {row.name}
                      </button>
                    </td>
                    <td className="num">{row.played}</td>
                    <td className="num">{row.wins}-{row.draws}-{row.losses}</td>
                    <td className="num">{row.gd > 0 ? `+${row.gd}` : row.gd}</td>
                    <td className="num">{row.points}</td>
                    <td className="num">{pct(row.top8_probability)}</td>
                    <td className="num">{pct(row.playoff_probability)}</td>
                    <td className="num">{pct(row.eliminated_probability)}</td>
                    <td className="num">{pct(row.win_probability)}</td>
                  </tr>
                  {open === row.club_id && (
                    <tr className="detail">
                      <td colSpan={10}>
                        <div>
                          <span>Elo {String(signals.elo ?? club?.elo)}</span>
                          <span>strength {club?.strength}</span>
                          <span>form {String(signals.form_source)} {String(signals.xg_form_ratio ?? "")}</span>
                          <span>injury {String(signals.injury_multiplier)}</span>
                          <span>squad €{Number(signals.squad_value_eur || 0).toLocaleString()}</span>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      <h2 className="section-title">If the table froze tonight</h2>
      <p className="note">{data.bracket.note}</p>
      <div className="card">
        <div className="ties">
          {(data.bracket.playoff || []).map((tie) => {
            const entries = Object.entries(tie.advance).sort((a, b) => b[1] - a[1]);
            return (
              <div className="tie" key={`${tie.leg1_home}-${tie.leg2_home}`}>
                <div>
                  <strong>{names[entries[0][0]] || entries[0][0]}</strong>
                  <div className="note">hosts the second leg · first leg at {names[tie.leg1_home] || tie.leg1_home}</div>
                </div>
                <div>
                  {entries.map(([id, prob]) => (
                    <div key={id}>{pct(prob)} {names[id] || id}</div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </main>
  );
}
