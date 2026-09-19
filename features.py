import numpy as np
import pandas as pd

import config


def _norm(s, maxv):
    return (s.astype(float) / maxv).clip(upper=1.0)


def _target_context(merged, target_date):
    if not target_date:
        return None
    t = pd.Timestamp(target_date)
    ctx = {'date': t, 'dow': t.dayofweek, 'quarter': t.quarter, 'venue': None, 'tour': None}
    s = merged.copy()
    s['showdate'] = pd.to_datetime(s['showdate'])
    match = s[s['showdate'] == t]
    if not match.empty:
        row = match.iloc[0]
        ctx['venue'] = row.get('venue')
        ctx['tour'] = row.get('tourname')
    else:
        prior = s[s['showdate'] < t].sort_values('showdate')
        if not prior.empty:
            ctx['tour'] = prior.iloc[-1].get('tourname')
    return ctx


def _venue_rate(merged, base, venue):
    """Per-song play rate at a target venue, or all-NaN if it can't be trusted.

    Returns the fraction of that venue's shows in which each song appeared
    (0..1). When the venue has no known name or fewer than MIN_VENUE_SHOWS of
    history we return NaN (treated as 0) so one-off venues don't inject noise.
    """
    if not venue:
        return float('nan')
    v = merged[merged['venue'] == venue]
    v_shows = v['showid'].nunique()
    if v_shows < config.MIN_VENUE_SHOWS:
        return float('nan')
    rate = v.groupby('songid')['showid'].nunique() / v_shows
    return base['songid'].map(rate).fillna(0.0)


def compute_features(merged, target_date=None, context=None):
    merged = merged.copy()
    merged['showdate'] = pd.to_datetime(merged['showdate'])
    merged = merged.sort_values('showdate')
    # Count each song once per show: a reprise (same song twice in one night,
    # e.g. a Tweezer reprise) is a single play, not two. Dropping the extra
    # rows keeps every downstream count show-based.
    merged = merged.drop_duplicates(subset=['songid', 'showid'])

    ordered_showids = merged['showid'].drop_duplicates().tolist()
    ordinal = {sid: i + 1 for i, sid in enumerate(ordered_showids)}
    merged['show_ord'] = merged['showid'].map(ordinal)
    total_shows = len(ordered_showids)

    last_25 = set(ordered_showids[-25:])
    last_5 = set(ordered_showids[-5:])

    grp = merged.groupby('songid')
    times = grp.size()
    gap = (total_shows - grp['show_ord'].max()).rename('gap')

    trend = (
        merged[merged['showid'].isin(last_25)]
        .groupby('songid')
        .size()
        .rename('trend_25')
    )
    played_last_5 = set(merged[merged['showid'].isin(last_5)]['songid'].unique())

    base = merged[['songid', 'song']].drop_duplicates(subset='songid').reset_index(drop=True)
    base['times_played'] = base['songid'].map(times).astype(int)
    base = base[base['times_played'] >= config.MIN_TIMES_PLAYED]
    base['gap'] = base['songid'].map(gap).astype(int)
    base['trend_25'] = base['songid'].map(trend).fillna(0).astype(int)
    base['played_last_5'] = base['songid'].isin(played_last_5).astype(int)

    # Frequency and cadence-relative overdue-ness.
    base['base_rate'] = base['times_played'] / total_shows
    base['expected_gap'] = total_shows / base['times_played']
    base['overdue'] = base['gap'] * base['base_rate']

    # Era: recency-decay-weighted play rate. Recent shows (and new music) count
    # more than shows from years ago, so a song still in rotation stays "hot"
    # while one that faded years ago drops out. Rates are normalized over
    # distinct shows (not rows) so they sit on the same 0..1 scale as base_rate.
    decay = 0.5 ** (1.0 / config.ERA_HALFLIFE_SHOWS)
    uniq = merged[['showid', 'show_ord']].drop_duplicates('showid').copy()
    uniq['show_w'] = decay ** (total_shows - uniq['show_ord'])
    total_w = uniq['show_w'].sum()
    wmap = uniq.set_index('showid')['show_w']
    era_w = merged['showid'].map(wmap).groupby(merged['songid']).sum()
    base['era_rate'] = (base['songid'].map(era_w).fillna(0.0) / total_w).astype(float)

    # Normalized features for scoring (all roughly 0..1).
    max_times = max(base['times_played'].max(), 1)
    base['overdue_norm'] = (base['overdue'] / config.OVERDUE_CAP).clip(upper=1.0)
    base['freq_norm'] = (np.log1p(base['times_played']) / np.log1p(max_times)).clip(upper=1.0)
    base['trend_norm'] = (base['trend_25'] / config.TREND_CAP).clip(upper=1.0)

    ctx = context if context is not None else _target_context(merged, target_date)
    if ctx is not None:
        base['venue_played'] = _venue_rate(merged, base, ctx.get('venue'))
        if ctx['tour']:
            tour_songs = set(merged[merged['tourname'] == ctx['tour']]['songid'].unique())
            base['tour_match'] = base['songid'].isin(tour_songs).astype(float)
        else:
            base['tour_match'] = float('nan')
        dow = merged.groupby('songid').apply(
            lambda g: (g['showdate'].dt.dayofweek == ctx['dow']).mean())
        base['dow_match'] = base['songid'].map(dow).astype(float)
        qtr = merged.groupby('songid').apply(
            lambda g: (g['showdate'].dt.quarter == ctx['quarter']).mean())
        base['season_match'] = base['songid'].map(qtr).astype(float)

    return base.reset_index(drop=True)
