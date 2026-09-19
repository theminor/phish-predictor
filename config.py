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

# Era weighting: each show's contribution to the 'era' rate decays exponentially
# with its age, halving every ERA_HALFLIFE_SHOWS shows. Shorter = more weight on
# the recent era (and on new music). 150 found best in backtests (~4.5 years).
ERA_HALFLIFE_SHOWS = 150

# Co-occurrence ("if X plays, Y likely plays too"): the anchors are the top
# COOC_ANCHORS base-score songs; a song's lift is capped at COOC_LIFT_CAP and a
# pair needs at least COOC_MIN_CO shared shows to count at all.
COOC_ANCHORS = 10
COOC_LIFT_CAP = 4.0
COOC_MIN_CO = 5

# Scoring weights. Frequency dominates; 'trend' (recent momentum) and 'era'
# (recency-weighted rate, keeps current-rotation + new music hot) are strong; a
# heavy 'repeat_penalty' (don't re-predict what just played) helps a lot; 'cooc'
# (co-occurrence with the top picks) helps a little and is fragile, so keep it
# low; raw 'overdue' adds nothing by default. 'repeat_penalty' is subtracted;
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
    'era': 0.40,
    'cooc': 0.25,
    'repeat_penalty': 0.35,
    'venue': 0.30,
    'tour': 0.05,
    'dow': 0.05,
    'season': 0.10,
}
PENALTY_KEYS = {'repeat_penalty'}
