import numpy as np

import config

FEATURE_COL = {
    'overdue': 'overdue_norm',
    'freq': 'freq_norm',
    'trend': 'trend_norm',
    'era': 'era_rate',
    'cooc': 'cooc',
    'repeat_penalty': 'played_last_5',
    'venue': 'venue_played',
    'tour': 'tour_match',
    'dow': 'dow_match',
    'season': 'season_match',
}

OUTPUT_COLS = ['rank', 'song', 'score', 'gap', 'times_played', 'overdue', 'trend_25', 'played_last_5']


def _cooc_lift(plays, anchors, songids, base_rate):
    """For each candidate song, the max co-occurrence lift with any anchor.

    lift(Z | A) = P(Z plays | A plays) / P(Z plays) — how much more likely Z is
    when anchor A is in the show. Only pairs with at least COOC_MIN_CO shared
    shows count. Returns a 0..1 array aligned to `songids`.
    """
    shows_by_song = {sid: list(sh) for sid, sh in plays.groupby('songid')['showid']}
    songs_by_show = {sh: list(s) for sh, s in plays.groupby('showid')['songid']}

    cooc = np.zeros(len(songids))
    for A in anchors:
        showsA = shows_by_song.get(A)
        if not showsA:
            continue
        cntA = len(showsA)
        if cntA < config.COOC_MIN_CO:
            continue
        co = {}
        for sh in showsA:
            for Z in songs_by_show.get(sh, ()):
                co[Z] = co.get(Z, 0) + 1
        for i, Z in enumerate(songids):
            if Z == A:
                continue
            c = co.get(Z, 0)
            if c < config.COOC_MIN_CO:
                continue
            br = base_rate[i]
            if br and br > 0:
                lift = (c / cntA) / br
                if lift > cooc[i]:
                    cooc[i] = lift
    return np.minimum(cooc / config.COOC_LIFT_CAP, 1.0)


def predict(features, weights=None, top_n=None, plays=None):
    weights = weights or config.WEIGHTS
    if top_n is None:
        top_n = config.DEFAULT_TOP_N
    df = features.copy()
    df['score'] = 0.0
    cooc_w = weights.get('cooc', 0.0)

    # Base score from the ordinary features (co-occurrence handled in a 2nd pass
    # below, since it depends on the top-ranked "anchor" songs).
    for key, col in FEATURE_COL.items():
        if key == 'cooc':
            continue
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

    if cooc_w and plays is not None:
        anchor_idx = df['score'].nlargest(config.COOC_ANCHORS).index
        anchors = df.loc[anchor_idx, 'songid'].tolist()
        cooc_norm = _cooc_lift(plays, anchors, df['songid'].tolist(),
                               df['base_rate'].to_numpy(dtype=float))
        df['score'] = df['score'] + cooc_w * cooc_norm

    df = df.sort_values('score', ascending=False).reset_index(drop=True)
    df.insert(0, 'rank', df.index + 1)
    return df[OUTPUT_COLS].head(top_n).reset_index(drop=True)
