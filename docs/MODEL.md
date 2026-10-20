# Model

UCL 2026/27. 36 clubs, eight league-phase matches, top eight to the round of 16, 9th–24th into a two-legged playoff, then two-legged rounds until a single-leg final. Away goals do not count.

## What is not in the rating

The UEFA club coefficient, and the number of European titles, do not add strength. Real Madrid's history is why they are often the favourite in the press. It is not a term in this model. The coefficient is used only as the last league-phase tie-break, which is the rule UEFA applies during the phase.

## Strength

The number on the club row blends current Elo 0.22, recent goals 0.33, squad value 0.10, and outright markets 0.35. A missing signal gives its weight to the signals that club actually has. Injuries and fixture load are not inside that sum. They scale the goal rates.

## Goals

Attack and defense start from a domestic-league prior (Premier League clubs share a base, Azerbaijan a lower one) plus a small gap for squad value inside that league. Played Champions League matches then move the Elo. Recent goals pull the rates once there is a sample. Champions League matches count double a domestic match. Domestic results come from the public ESPN scoreboards for 15 September–15 October 2026.

Outright prices are the Polymarket 2027-champion market, blended with bookmaker outrights when `ODDS_API_KEY` is set. A higher price raises both attack and defense. The stretch is logarithmic, so 23% and 10% do not collapse into the same boost. Squad value is a smaller attack-only nudge.

Home expected goals are multiplied by `HOME_ADV` (1.28). A neutral final uses 1.0. Scores are independent Poisson. Extra time is 30% of those rates. Penalties shrink the Elo gap most of the way back to a coin flip.

`HOME_ADV` was checked with `scripts/backtest.py --sweep` on the first two matchdays. That sample is home-heavy, so the prior stays at 1.28.

## Rest and injuries

Rest counts finished matches in the 28 days before 15 October, across the league, domestic cups, and the Champions League. A club busier than four matches in that window has its goal rates trimmed, down to 0.94. One crowded week does not rewrite a whole season, so the trim stays small. If we have no domestic calendar for a club, rest stays at 1.

Injuries still use the key-player multiplier (floor 0.75) from API-Football, domestic league plus Champions League, and only for these 36 clubs. That feed is empty until `API_FOOTBALL_KEY` is set. The notes say so instead of inventing absences.

## Table

Points, goal difference, goals scored, away goals, wins, away wins, then UEFA coefficient.

## Bracket

Playoffs are 9v24, 10v23, … 16v17. The better-ranked club hosts the second leg. The round of 16 pairs 1st with the winner of 16v17 and keeps 1st and 2nd in opposite halves. The bracket on the site is the frozen table: each later round shows the club that most often lands on that side, and their chance of going through. Title probabilities resimulate the remaining league games.
