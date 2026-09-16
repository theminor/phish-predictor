# phish-predictor

Predicts the songs Phish is most likely to play at their next show, using full
setlist history from the [Phish.net API v5](https://docs.phish.net/).

For each song it computes a set of features, combines them into a single score,
and ranks the field.

## Features used

| Feature | Meaning |
|---------|---------|
| `gap` | Shows since the song was last played (higher = more "due") |
| `trend_25` | Times played in the last 25 shows (hot/cold streak) |
| `freq_100` | Plays per 100 shows (long-term rate; lightly penalized) |
| `played_last_5` | Was it played in the last 5 shows? (penalized) |
| `venue_played` | Ever played at the target venue (only with `--date`) |
| `tour_match` | Played on the target tour (only with `--date`) |
| `dow_match` | How often played on that day of week (only with `--date`) |
| `season_match` | How often played in that quarter (only with `--date`) |

The score is a weighted sum of the normalized features; `repeat_penalty` and
`freq_100` are subtracted. Weights live in `config.py`.

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

## How it works

- `fetch.py` pulls `setlists`, `songs`, and `shows` from the API and caches them
  in a local SQLite file (`phish.db`), refreshing automatically after 24h.
- `features.py` turns the history into per-song features.
- `predict.py` scores and ranks the songs.
- `main.py` is the CLI.

## Notes

- `phish.db` and `.env` are git-ignored.
- The model is a transparent weighted heuristic for now; a backtester and a
  learned model are natural next steps.
