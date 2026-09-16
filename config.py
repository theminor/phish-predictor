API_BASE = 'https://api.phish.net/v5'
ARTIST = 'Phish'
CACHE_TTL_HOURS = 24
DB_PATH = 'phish.db'
DEFAULT_TOP_N = 20
MIN_TIMES_PLAYED = 3

# Normalization caps.
OVERDUE_CAP = 3.0   # A song 3x more overdue than its own cadence is "max overdue".
TREND_CAP = 10.0    # Appearing in 10+ of the last 25 shows is "max trend".

# Scoring weights. 'overdue', 'freq', 'trend' are the core drivers;
# 'repeat_penalty' is subtracted; venue/tour/dow/season only apply with --date.
WEIGHTS = {
    'overdue': 0.35,
    'freq': 0.30,
    'trend': 0.20,
    'repeat_penalty': 0.15,
    'venue': 0.10,
    'tour': 0.05,
    'dow': 0.05,
    'season': 0.10,
}
PENALTY_KEYS = {'repeat_penalty'}
