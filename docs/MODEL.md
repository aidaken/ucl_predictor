# Model

UCL 2026/27. 36 clubs, eight league-phase matches, top eight to the round of 16, 9th–24th into a two-legged playoff, then two-legged rounds until a single-leg final. Away goals do not count.

## Strength

The number on the club row is the same blend as the World Cup engine: Elo 0.35, xG form 0.30, squad value 0.15, outright odds 0.20. A missing signal gives its weight to the signals that club actually has. Injuries are not inside that sum. They scale the goal rates.

## Goals

Attack and defense start from Elo (`(elo / 1650) ^ 0.9`). Once a club has recent matches, opponent-adjusted xG (or goals, if xG is missing) pulls those rates. UCL matches count double a domestic match. Squad value and the outright market tilt attack only, so Elo is not counted twice.

Home expected goals are multiplied by `HOME_ADV` (1.28). A neutral final uses 1.0. Scores are independent Poisson. Extra time is 30% of those rates. Penalties shrink the Elo gap most of the way back to a coin flip.

`HOME_ADV` was checked with `scripts/backtest.py --sweep` on the 36 finished matchday 1–2 games. The sample is home-heavy (21 wins, 3 draws, 12 away wins) and the Brier score was still falling at the edge of the grid, so the prior stays at 1.28 instead of chasing that edge.

## Table

Points, goal difference, goals scored, away goals, wins, away wins, then UEFA coefficient. That is the in-season league-phase order. Head-to-head is not in those criteria.

## Bracket

Playoffs are 9v24, 10v23, … 16v17. The better-ranked club hosts the second leg. The round of 16 pairs 1st with the winner of 16v17 and keeps 1st and 2nd in opposite halves. Title probabilities resimulate the remaining league games. The bracket on the site is the separate question: if today's table never moved.

## Health

Each club is fetched from its own domestic league and from Champions League (`league=2`) only. The two feeds merge on player id. The harsher injury status wins. Only key players move the multiplier: a short name list (Haaland, Yamal, and the rest in `config.py`) plus the top two by goal involvement. Floor is 0.75.
