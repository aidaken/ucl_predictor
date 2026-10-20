"use client";

import { Fragment, useEffect, useState, type CSSProperties } from "react";

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
  report?: string;
};

type Side = { id: string; present: number; advance: number } | null;
type Tie = { left: Side; right: Side; note?: string };
type Round = { id: string; label: string; ties: Tie[] };

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
    rounds?: Round[];
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

function displayRounds(rounds: Round[]): Round[] {
  const feeder = [7, 0, 4, 3, 6, 1, 5, 2];
  return rounds.map((round) => {
    if (round.id !== "playoff" || round.ties.length !== feeder.length) return round;
    return { ...round, ties: feeder.map((index) => round.ties[index]) };
  });
}

function slotStyle(roundId: string, index: number): CSSProperties {
  if (roundId === "playoff") return { gridColumn: 1, gridRow: index + 1 };
  if (roundId === "r16") return { gridColumn: 2, gridRow: index + 1 };
  if (roundId === "qf") return { gridColumn: 3, gridRow: `${index * 2 + 1} / span 2` };
  if (roundId === "sf") return { gridColumn: 4, gridRow: `${index * 4 + 1} / span 4` };
  return { gridColumn: 5, gridRow: "1 / span 8" };
}

function Starball() {
  return (
    <svg className="starball" viewBox="0 0 200 200" aria-hidden="true">
      <defs>
        <radialGradient id="ball" cx="35%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#7ec8ff" />
          <stop offset="45%" stopColor="#1a4d9c" />
          <stop offset="100%" stopColor="#06122a" />
        </radialGradient>
        <linearGradient id="rim" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#f0d78c" />
          <stop offset="50%" stopColor="#d4af37" />
          <stop offset="100%" stopColor="#8a6a1a" />
        </linearGradient>
      </defs>
      <circle cx="100" cy="100" r="88" fill="url(#ball)" stroke="url(#rim)" strokeWidth="4" />
      {[0, 45, 90, 135].map((deg) => (
        <g key={deg} transform={`rotate(${deg} 100 100)`}>
          <path
            d="M100 28 C118 58, 118 78, 100 100 C82 78, 82 58, 100 28 Z"
            fill="none"
            stroke="url(#rim)"
            strokeWidth="2.2"
            opacity="0.9"
          />
        </g>
      ))}
      <circle cx="100" cy="100" r="6" fill="#f0d78c" />
    </svg>
  );
}

function SideRow({ side, names }: { side: Side; names: Record<string, string> }) {
  if (!side) return <div className="side empty">Open</div>;
  return (
    <div className="side">
      <div>
        <div className="side-name">{names[side.id] || side.id}</div>
        {side.present < 0.98 && <div className="hint">in this slot {pct(side.present)}</div>}
      </div>
      <span className="side-pct">{pct(side.advance)}</span>
    </div>
  );
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

  if (error) {
    return (
      <div className="sky">
        <main className="wrap status"><p>{error}</p></main>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="sky">
        <main className="wrap status"><p>Loading the league…</p></main>
      </div>
    );
  }

  const names = Object.fromEntries(data.clubs.map((club) => [club.id, club.name]));
  const byTitle = [...data.clubs].sort(
    (a, b) => b.probabilities.win_probability - a.probabilities.win_probability,
  );
  const favourite = byTitle[0];
  const rounds = displayRounds(data.bracket.rounds || []);

  return (
    <div className="sky">
      <main>
        <section className="hero-sky">
          <div className="wrap hero-inner">
            <Starball />
            <h1 className="brand">Champions League</h1>
            <p className="hero-line">
              A model of the 2026–27 season. Markets, form, and fixture load — not who has lifted the cup before.
            </p>
            <div className="favourite">
              <p className="label">Title favourite</p>
              <h2 className="name">{favourite.name}</h2>
              <p className="chance">{pct(favourite.probabilities.win_probability)}</p>
              <p className="path">
                Final {pct(favourite.probabilities.reach_final_probability)}
                {" · "}
                Semis {pct(favourite.probabilities.reach_sf_probability)}
                {" · "}
                Top 8 {pct(favourite.probabilities.top8_probability)}
              </p>
            </div>
            <p className="meta-chip">
              <span>Model {data._meta.model_version}</span>
              <span>{data._meta.simulations.toLocaleString()} seasons</span>
              <span>{new Date(data._meta.generated_at).toUTCString()}</span>
            </p>
          </div>
        </section>

        <div className="wrap">
          <section className="section">
            <div className="section-head">
              <p className="section-kicker">Title race</p>
              <h2 className="section-title">Who lifts it</h2>
              <p className="section-note">
                Full-season odds after the remaining league-phase matches are resimulated. The bracket below is the separate question: if tonight&apos;s table never moved.
              </p>
            </div>
            <div className="odds-board">
              {byTitle.slice(0, 8).map((club, index) => (
                <div className="odds-row" key={club.id}>
                  <span className="odds-rank">{String(index + 1).padStart(2, "0")}</span>
                  <div className="odds-main">
                    <span className="odds-name">{club.name}</span>
                    <div className="odds-track">
                      <div
                        className="odds-fill"
                        style={{
                          width: `${Math.max(
                            (club.probabilities.win_probability / (favourite.probabilities.win_probability || 1)) * 100,
                            4,
                          )}%`,
                          animationDelay: `${index * 0.05}s`,
                        }}
                      />
                    </div>
                  </div>
                  <span className="odds-pct">{pct(club.probabilities.win_probability)}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="section">
            <div className="section-head">
              <p className="section-kicker">League phase</p>
              <h2 className="section-title">The table</h2>
              <p className="section-note">
                Click a club for markets, form, rest, and injuries. Qualification odds include every remaining matchday.
              </p>
            </div>
            <p className="legend">
              <span><i className="l-direct" /> Direct round of 16</span>
              <span><i className="l-seed" /> Seeded play-off</span>
              <span><i className="l-playoff" /> Unseeded play-off</span>
              <span><i className="l-out" /> Out</span>
            </p>
            <div className="table-shell">
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
                    <th className="num">Play-off</th>
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
                            <button
                              className="linkish"
                              onClick={() => setOpen(open === row.club_id ? null : row.club_id)}
                            >
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
                              <p className="report">{club?.report}</p>
                              <div className="signals">
                                <span className="signal"><strong>Elo</strong>{String(signals.elo ?? club?.elo)}</span>
                                <span className="signal"><strong>Seed</strong>{String(signals.rating_seed ?? "—")}</span>
                                <span className="signal">
                                  <strong>Market</strong>
                                  {signals.betting_implied_prob == null ? "—" : pct(Number(signals.betting_implied_prob))}
                                </span>
                                <span className="signal">
                                  <strong>Form</strong>
                                  {String(signals.form_source)} {String(signals.matches_used ?? "")} matches
                                </span>
                                <span className="signal">
                                  <strong>Goals</strong>
                                  {String(signals.avg_xg_for)} / {String(signals.avg_xg_against)}
                                </span>
                                <span className="signal"><strong>Injury</strong>{String(signals.injury_multiplier)}</span>
                                <span className="signal">
                                  <strong>Rest</strong>
                                  {String((signals.rest as { multiplier?: number } | undefined)?.multiplier ?? 1)}
                                </span>
                                <span className="signal">
                                  <strong>Squad</strong>€{Number(signals.squad_value_eur || 0).toLocaleString()}
                                </span>
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
          </section>

          <section className="section">
            <div className="section-head">
              <p className="section-kicker">Knockout path</p>
              <h2 className="section-title">The bracket</h2>
              <p className="section-note">
                {data.bracket.note} The gold number is the chance of going through. Where the pairing is not fixed, the name is whoever lands there most often.
              </p>
            </div>
            <div className="bracket-shell">
              <div className="bracket">
                {rounds.map((round) => (
                  <div
                    className="round-label"
                    key={round.id}
                    style={{ gridColumn: slotStyle(round.id, 0).gridColumn, gridRow: 1 }}
                  >
                    {round.label}
                  </div>
                ))}
                {rounds.map((round) =>
                  round.ties.map((tie, index) => {
                    const place = slotStyle(round.id, index);
                    const row =
                      typeof place.gridRow === "number"
                        ? place.gridRow + 1
                        : String(place.gridRow).replace(/^(\d+)/, (_, n) => String(Number(n) + 1));
                    return (
                      <article
                        className="match"
                        key={`${round.id}-${index}`}
                        style={{ ...place, gridRow: row, animationDelay: `${index * 0.03}s` }}
                      >
                        <SideRow side={tie.left} names={names} />
                        <SideRow side={tie.right} names={names} />
                      </article>
                    );
                  }),
                )}
              </div>
            </div>
          </section>

          <section className="section">
            <div className="section-head">
              <p className="section-kicker">Why those numbers</p>
              <h2 className="section-title">Club notes</h2>
              <p className="section-note">
                Markets are the crowd. The league prior is only which country they play in. European titles are not in the formula.
              </p>
            </div>
            <div className="notes">
              {byTitle.slice(0, 6).map((club) => (
                <article className="note-card" key={club.id}>
                  <p className="kicker">{pct(club.probabilities.win_probability)} title</p>
                  <h3>{club.name}</h3>
                  <p>{club.report}</p>
                </article>
              ))}
            </div>
          </section>

          <footer className="footer">
            <span>UEFA Champions League 2026–27</span>
            <span>Not affiliated with UEFA</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
