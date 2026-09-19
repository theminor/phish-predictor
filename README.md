# phish-predictor

Predicts the songs Phish is most likely to play at their next show, using full
setlist history from the [Phish.net API v5](https://docs.phish.net/).

For each song it computes a set of features, combines them into a single score,
and ranks the field.

## Features used

| Feature | Meaning |
|---------|---------|
| `freq` (base_rate) | Share of all shows the song has appeared in (long-term frequency) |
| `era_rate` | Recency-weighted play rate — recent shows (and new music) count more |
| `trend_25` | Times played in the last 25 shows (hot/cold momentum) |
| `cooc` | Co-occurrence lift with the top picks ("if X plays, Y likely plays") |
| `played_last_5` | Was it played in the last 5 shows? (penalized) |
| `overdue` | Cadence-relative "due": shows since last played ÷ its normal gap |
| `venue_played` | How often played at the target venue vs elsewhere (recurring venues, target date) |
| `tour_match` | Played on the target tour (only with a target date) |
| `dow_match` | How often played on that day of week (only with a target date) |
| `season_match` | How often played in that quarter (only with a target date) |

Plays are counted **once per show**: a song reprised twice in a night (Tweezer
does this a lot) counts as a single play, not two.

The score is a weighted sum of the normalized features, minus a repeat
penalty. Frequency is the strongest signal; recent momentum (`trend`) and the
recency-weighted `era` rate (so new music stays in the pool) are strong; a heavy
repeat penalty (don't re-predict what just played) helps a lot; `cooc`
(co-occurrence with the top picks) helps a little and is fragile, so keep it
low; raw "overdue" adds nothing by default. When you supply a target date at a
venue Phish have played before, that venue's own song rates matter too. Weights
live in `config.py` and can be overridden at runtime (see **Tuning the weights**).

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

# Override the scoring weights for this run only
python main.py --weights freq=0.5,trend=0.7,repeat_penalty=0.35

# Print the weights currently in effect (defaults / saved / --weights)
python main.py --show-weights
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

There's also a **Weights** tab to tune the model (see below).

## Tuning the weights

The shipped weights come from a grid search that backtests the most recent 100
shows, predicting each from only the shows before it. To tune them yourself:

- **Web UI → Weights tab**: edit any weight, hit **Evaluate** to see the
  average top-20 hits over the last N shows (with a per-show breakdown), then
  **Save**. Saved weights are written to `weights.json`, which takes precedence
  over `config.py` for both the web app and the CLI. **Reset to defaults**
  deletes the saved file.
- **CLI**: `python main.py --weights freq=0.5,trend=0.7` overrides for that run
  only; `python main.py --show-weights` prints the weights in effect.

## How it works

- `fetch.py` pulls `setlists` from the API and caches it in a local SQLite file
  (`phish.db`), refreshing automatically after 24h.
- `features.py` turns the history into per-song features.
- `predict.py` scores and ranks the songs.
- `engine.py` is the shared logic used by both interfaces.
- `main.py` is the CLI; `app.py` is the web backend.

## Notes

- `phish.db`, `.env`, and `weights.json` are git-ignored.
- Only the `setlists` endpoint is used: it carries the song names plus
  venue/tour per set, which is all the model needs. (The `songs` endpoint's
  `artist` filter is unreliable — it means *original songwriter*, so it drops
  most of Phish's original catalog.)
- The model is a transparent weighted heuristic. The shipped weights are the
  best found by a 100-show backtest grid search (~4.6 of the top 20 hit on
  recent shows, vs ~4.4 before adding the `era` and `cooc` features). Natural
  next steps: set-position structure (who opens the encore, per set number) and
  an interactive "predict the rest of tonight" mode built on co-occurrence.
