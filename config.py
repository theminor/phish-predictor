API_BASE = 'https://api.phish.net/v5'
ARTIST = 'Phish'
CACHE_TTL_HOURS = 24
DB_PATH = 'phish.db'
DEFAULT_TOP_N = 20
MIN_TIMES_PLAYED = 3

# Normalization caps.
OVERDUE_CAP = 3.0   # A song 3x more overdue than its own cadence is "max overdue".
TREND_CAP = 10.0    # Appearing in 10+ of the last 25 shows is "max trend".

# The venue feature only kicks in when a venue has at least this many shows of
# history; below that, per-venue rates are pure noise and we stay neutral.
MIN_VENUE_SHOWS = 8

# Scoring weights. Frequency dominates; 'trend' (recent momentum) is a strong
# signal; a heavy 'repeat_penalty' (don't predict what just played) helps a lot;
# raw 'overdue' adds nothing by default. 'repeat_penalty' is subtracted;
# venue/tour/dow/season only apply with a target date.
#
# Defaults come from a grid search over the last 100 shows, backtesting each
# show against a prediction made only from the shows before it. Change these at
# runtime via the web UI (Weights tab) or `python main.py --weights ...`; saved
# overrides are written to weights.json and take precedence over this file.
WEIGHTS = {
    'overdue': 0.0,
    'freq': 0.50,
    'trend': 0.80,
    'repeat_penalty': 0.35,
    'venue': 0.30,
    'tour': 0.05,
    'dow': 0.05,
    'season': 0.10,
}
PENALTY_KEYS = {'repeat_penalty'}
