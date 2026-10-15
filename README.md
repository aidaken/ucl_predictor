# UCL 2026–27 Predictor

League-phase table, qualification odds, and title probabilities for the 36-club Champions League. The match model is Poisson, with home advantage, two-legged ties, and injuries taken from each club's domestic league plus the UCL itself.

Neon project `ucl-predictor` (`rough-fire-38678919`) is the source of truth. The site reads it through the Next.js API in `web/`. `data/predictions.json` is the local cache and the fallback when `DATABASE_URL` is unset.

## Run the engine

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_league_data.py   # only if you need to regenerate the seed
python update.py --demo                # cached data, 400 sims
python update.py                       # full sim, writes Neon when DATABASE_URL is set
python update.py --live                # also refresh fixtures and multi-league health
python scripts/backtest.py --sweep
python -m unittest discover -s tests -v
```

Copy `.env.example` to `.env` for `DATABASE_URL`, `API_FOOTBALL_KEY`, and `ODDS_API_KEY`.

## Site

```bash
cd web
npm install
npm run dev
```

Vercel project root is `web/`. Set `DATABASE_URL` there. Routes:

- `GET /api/predictions`
- `GET /api/table`
- `GET /api/bracket`
- `GET /api/clubs/:id`

GitHub Actions runs the tests on every push. `Update predictions` is manual or daily, and it needs the same secrets.

Math notes: [`docs/MODEL.md`](docs/MODEL.md).
