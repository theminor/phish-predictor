import config

FEATURE_COL = {
    'overdue': 'overdue_norm',
    'freq': 'freq_norm',
    'trend': 'trend_norm',
    'repeat_penalty': 'played_last_5',
    'venue': 'venue_played',
    'tour': 'tour_match',
    'dow': 'dow_match',
    'season': 'season_match',
}

OUTPUT_COLS = ['rank', 'song', 'score', 'gap', 'times_played', 'overdue', 'trend_25', 'played_last_5']


def predict(features, weights=None, top_n=None):
    weights = weights or config.WEIGHTS
    if top_n is None:
        top_n = config.DEFAULT_TOP_N
    df = features.copy()
    df['score'] = 0.0
    for key, col in FEATURE_COL.items():
        if col not in df.columns:
            continue
        w = weights.get(key, 0.0)
        if w == 0:
            continue
        vals = df[col].fillna(0.0)
        if key in config.PENALTY_KEYS:
            df['score'] = df['score'] - w * vals
        else:
            df['score'] = df['score'] + w * vals
    df = df.sort_values('score', ascending=False).reset_index(drop=True)
    df.insert(0, 'rank', df.index + 1)
    return df[OUTPUT_COLS].head(top_n).reset_index(drop=True)
