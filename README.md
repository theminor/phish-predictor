# phish-predictor

Predicts the songs Phish is most likely to play at their next show, using full
setlist history from the [Phish.net API v5](https://docs.phish.net/).

For each song it computes a set of features, combines them into a single score,
and ranks the field.

## Features used

| Feature | Meaning |
|---------|---------|
| `freq` (base_rate) | Share of all shows the song has appeared in (long-term frequency) |
| `overdue` | Cadence-relative "due": shows since last played ÷ its normal gap |
| `trend_25` | Times played in the last 25 shows (hot/cold momentum) |
| `played_last_5` | Was it played in the last 5 shows? (penalized) |
| `venue_played` | Ever played at the target venue (only with a target date) |
| `tour_match` | Played on the target tour (only with a target date) |
| `dow_match` | How often played on that day of week (only with a target date) |
| `season_match` | How often played in that quarter (only with a target date) |

The score is a weighted sum of the normalized features, minus a repeat
penalty. Frequency is the strongest signal, recent momentum is second, and raw
"overdue" adds little. Weights live in `config.py`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then put your Phish.net API key in .env
```

Get an API key at <https://phish.net/api/keys>.

## Usage

```bash
# Top 20 most likely songs (uses cached data; fetches on first run)
python main.py

# Top 30
python main.py -n 30

# Force a fresh fetch from the API
python main.py --refresh

# Predict for a specific show date (adds venue/tour/day/season context)
python main.py --date 2026-09-15
```

## Web UI

A small web app (FastAPI + vanilla JS) wraps the same engine:

```bash
source .venv/bin/activate
python app.py            # or: uvicorn app:app --reload
```

Then open <http://localhost:8000>.

Two views:
- **Predict next** — the top-N most likely songs, optionally for a target date
  (adds venue/tour/day/season context).
- **Backtest a show** — predicts a past show using only the history before it,
  then shows which of the top-N picks actually got played. The date defaults to
  the most recent show; use it to gauge how well the model does.

The API key stays server-side in `.env`; the browser never sees it.

## How it works

- `fetch.py` pulls `setlists` from the API and caches it in a local SQLite file
  (`phish.db`), refreshing automatically after 24h.
- `features.py` turns the history into per-song features.
- `predict.py` scores and ranks the songs.
- `engine.py` is the shared logic used by both interfaces.
- `main.py` is the CLI; `app.py` is the web backend.

## Notes

- `phish.db` and `.env` are git-ignored.
- Only the `setlists` endpoint is used: it carries the song names plus
  venue/tour per set, which is all the model needs. (The `songs` endpoint's
  `artist` filter is unreliable — it means *original songwriter*, so it drops
  most of Phish's original catalog.)
- The model is a transparent weighted heuristic, tuned by backtesting recent
  shows. A learned model (per-show probabilities, song co-occurrence, set
  structure) is the natural next step.
