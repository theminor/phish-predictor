import pandas as pd
from datetime import datetime, timezone

import config
import fetch
import features
import predict


def _metadata(merged):
    dates = pd.to_datetime(merged['showdate'])
    return {
        'total_shows': int(merged['showid'].nunique()),
        'song_count': int(merged['songid'].nunique()),
        'last_show_date': str(dates.max().date()),
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }


def status(force_refresh=False):
    merged = fetch.get_data(force_refresh=force_refresh)
    return _metadata(merged)


def predict_next(top_n=None, target_date=None, force_refresh=False):
    if top_n is None:
        top_n = config.DEFAULT_TOP_N
    merged = fetch.get_data(force_refresh=force_refresh)
    feats = features.compute_features(merged, target_date)
    result = predict.predict(feats, top_n=top_n)
    return result, _metadata(merged)


def backtest(show_date, top_n=None, force_refresh=False):
    """Predict for a past show using only the history before it, then compare."""
    if top_n is None:
        top_n = config.DEFAULT_TOP_N
    if not show_date:
        raise ValueError('show_date is required for backtest')

    merged = fetch.get_data(force_refresh=force_refresh)
    merged = merged.copy()
    merged['showdate'] = pd.to_datetime(merged['showdate'])
    target = pd.Timestamp(show_date)

    target_rows = merged[merged['showdate'] == target]
    if target_rows.empty:
        prior = merged[merged['showdate'] < target].sort_values('showdate')
        if prior.empty:
            raise ValueError('No shows on or before ' + str(show_date))
        target = prior['showdate'].iloc[-1]
        target_rows = merged[merged['showdate'] == target]

    history = merged[merged['showdate'] < target]
    if history.empty:
        raise ValueError('Not enough history to backtest ' + str(target.date()))

    # Context (venue/tour for that show) comes from the full data; features
    # (gap/freq/trend/venue-played) come from history only, to avoid leakage.
    ctx = features._target_context(merged, str(target.date()))
    feats = features.compute_features(history, context=ctx)
    predicted = predict.predict(feats, top_n=top_n)

    actual = target_rows.sort_values(['setno', 'position'])['song'].tolist()
    pred_songs = predicted['song'].tolist()
    hits = [s for s in pred_songs if s in set(actual)]

    return {
        'show_date': str(target.date()),
        'top_n': int(top_n),
        'history_shows': int(history['showid'].nunique()),
        'predicted': predicted,
        'actual': actual,
        'actual_count': len(actual),
        'hits': hits,
        'hits_in_top_n': len(hits),
    }
