import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

import config


def get_api_key():
    load_dotenv()
    key = os.getenv('PHISH_API_KEY')
    if not key:
        raise RuntimeError(
            'PHISH_API_KEY not set. Copy .env.example to .env and add your key '
            'from https://phish.net/api/keys'
        )
    return key.strip()


def api_get(path, params=None):
    params = dict(params or {})
    params['apikey'] = get_api_key()
    url = config.API_BASE + '/' + path
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get('error') not in (False, None):
        msg = 'API error ' + str(payload.get('error')) + ': ' + str(payload.get('error_message'))
        raise RuntimeError(msg)
    return payload.get('data', [])


def fetch_setlists():
    df = pd.DataFrame(api_get(
        'setlists/artist/' + config.ARTIST,
        {'order_by': 'showdate', 'direction': 'ASC'},
    ))
    return df.rename(columns={'set': 'setno'})


def fetch_songs():
    return pd.DataFrame(api_get('songs/artist/' + config.ARTIST))


def fetch_shows():
    return pd.DataFrame(api_get('shows/artist/' + config.ARTIST))


def _conn():
    return sqlite3.connect(config.DB_PATH)


def save_cache(df, table):
    conn = _conn()
    try:
        df.to_sql(table, conn, if_exists='replace', index=False)
        conn.execute('CREATE TABLE IF NOT EXISTS _meta (key TEXT PRIMARY KEY, value TEXT)')
        conn.execute(
            'INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)',
            ('updated_at_' + table, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def _cache_age_seconds(conn, table):
    row = conn.execute(
        'SELECT value FROM _meta WHERE key = ?', ('updated_at_' + table,)
    ).fetchone()
    if not row:
        return None
    updated = datetime.fromisoformat(row[0])
    return (datetime.now(timezone.utc) - updated).total_seconds()


def load_cache(table):
    conn = _conn()
    try:
        try:
            df = pd.read_sql_query('SELECT * FROM ' + table, conn)
        except pd.errors.DatabaseError:
            return None
        age = _cache_age_seconds(conn, table)
        if age is None or age > config.CACHE_TTL_HOURS * 3600:
            return None
        return df
    finally:
        conn.close()


def _get_table(fetch_fn, table, force_refresh):
    if not force_refresh:
        cached = load_cache(table)
        if cached is not None:
            print('  ' + table + ': cache hit')
            return cached
    print('  ' + table + ': fetching from API ...')
    df = fetch_fn()
    save_cache(df, table)
    return df


def get_data(force_refresh=False):
    setlists = _get_table(fetch_setlists, 'setlists', force_refresh)
    return setlists
