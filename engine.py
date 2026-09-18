import json
import os

import pandas as pd
from datetime import datetime, timezone

import config
import fetch
import features
import predict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_FILE = os.path.join(BASE_DIR, 'weights.json')
VALID_WEIGHT_KEYS = set(config.WEIGHTS.keys())


def load_weights():
    """Effective weights: config defaults, overridden by weights.json if present."""
    weights = dict(config.WEIGHTS)
    if os.path.exists(WEIGHTS_FILE):
        try:
            with open(WEIGHTS_FILE) as f:
                saved = json.load(f)
            for key, value in saved.items():
                if key in VALID_WEIGHT_KEYS:
                    weights[key] = float(value)
        except (OSError, ValueError):
            pass
    return weights


def save_weights(weights):
    """Persist weight overrides to weights.json. Returns the effective weights."""
    clean = {}
    for key, value in (weights or {}).items():
        if key not in VALID_WEIGHT_KEYS:
            continue
        value = float(value)
        if value != value or value < 0:  # NaN or negative
            raise ValueError('weight "%s" must be a non-negative number' % key)
        clean[key] = value
    if not clean:
        raise ValueError('no valid weights to save')
    with open(WEIGHTS_FILE, 'w') as f:
        json.dump(clean, f, indent=2, sort_keys=True)
    return load_weights()


def reset_weights():
    """Delete saved overrides so the config defaults apply again."""
    if os.path.exists(WEIGHTS_FILE):
        os.remove(WEIGHTS_FILE)
    return load_weights()


def _effective_weights(weights):
    return weights if weights else load_weights()


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


def predict_next(top_n=None, target_date=None, force_refresh=False, weights=None):
    weights = _effective_weights(weights)
    if top_n is None:
        top_n = config.DEFAULT_TOP_N
    merged = fetch.get_data(force_refresh=force_refresh)
    feats = features.compute_features(merged, target_date)
    result = predict.predict(feats, weights=weights, top_n=top_n)
    return result, _metadata(merged)


def backtest(show_date, top_n=None, force_refresh=False, weights=None):
    """Predict for a past show using only the history before it, then compare."""
    weights = _effective_weights(weights)
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
    predicted = predict.predict(feats, weights=weights, top_n=top_n)

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


def evaluate_weights(n_shows=20, top_n=None, force_refresh=False, weights=None):
    """Backtest the last N shows with a weight set and report average hits.

    Used by the Weights tab so the user can see how a candidate weight set
    performs before saving it. No leakage: each show is predicted only from the
    shows before it.
    """
    weights = _effective_weights(weights)
    if top_n is None:
        top_n = config.DEFAULT_TOP_N
    n_shows = max(1, min(int(n_shows), 100))

    merged = fetch.get_data(force_refresh=force_refresh)
    merged = merged.copy()
    merged['showdate'] = pd.to_datetime(merged['showdate'])
    dates = sorted(merged['showdate'].unique())[-n_shows:]

    per_show = []
    for d in dates:
        history = merged[merged['showdate'] < d]
        if history.empty:
            continue
        actual = set(merged.loc[merged['showdate'] == d, 'song'])
        feats = features.compute_features(history)
        top = set(predict.predict(feats, weights=weights, top_n=top_n)['song'])
        per_show.append({
            'date': str(pd.Timestamp(d).date()),
            'hits': len(top & actual),
            'actual': len(actual),
        })

    if not per_show:
        raise ValueError('not enough shows to evaluate')

    return {
        'n_shows': len(per_show),
        'top_n': int(top_n),
        'avg_hits': round(sum(p['hits'] for p in per_show) / len(per_show), 3),
        'per_show': per_show,
        'weights': weights,
    }
