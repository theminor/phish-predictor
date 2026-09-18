import os
import pandas as pd
import click
from rich.console import Console
from rich.table import Table

import config
import engine

console = Console()


def parse_weights(spec):
    """Parse 'key=value,key=value' into a dict (or None if spec is empty)."""
    if not spec:
        return None
    weights = {}
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        if '=' not in part:
            raise ValueError('bad weight "%s" (expected key=value)' % part)
        key, value = part.split('=', 1)
        weights[key.strip()] = float(value.strip())
    return weights


@click.command()
@click.option('-n', '--top-n', default=config.DEFAULT_TOP_N, show_default=True,
              help='Number of predictions to show.')
@click.option('--refresh', is_flag=True, help='Force re-fetch from the API, ignoring cache.')
@click.option('--date', 'target_date', default=None,
              help='Predict for the show on YYYY-MM-DD (uses that show venue/tour/day/season).')
@click.option('--weights', default=None,
              help='Override scoring weights for this run, e.g. freq=0.5,trend=0.7,repeat_penalty=0.35.')
@click.option('--show-weights', is_flag=True, help='Print the effective weights and exit.')
def main(top_n, refresh, target_date, weights, show_weights):
    """Predict Phish's most likely next songs from setlist history."""
    try:
        override = parse_weights(weights)
    except ValueError as e:
        console.print('[red]Error:[/] ' + str(e))
        raise SystemExit(1)

    if show_weights:
        effective = override or engine.load_weights()
        table = Table(title='Effective scoring weights')
        table.add_column('weight', style='bold')
        table.add_column('value', justify='right')
        for key, value in effective.items():
            table.add_row(key, '%.3f' % value)
        console.print(table)
        return

    try:
        console.print('[bold]Loading setlist data...[/]')
        result, meta = engine.predict_next(top_n=top_n, target_date=target_date,
                                           force_refresh=refresh, weights=override)
    except (RuntimeError, ValueError) as e:
        console.print('[red]Error:[/] ' + str(e))
        raise SystemExit(1)

    if result.empty:
        console.print('[red]No songs to score.[/]')
        raise SystemExit(1)

    if override is not None:
        wsource = 'from --weights'
    elif os.path.exists(engine.WEIGHTS_FILE):
        wsource = 'saved in weights.json'
    else:
        wsource = 'defaults (config.py)'

    note = 'all shows' if not target_date else 'target ' + target_date
    note += ' · as of ' + meta['last_show_date']
    console.print('[dim]weights: %s[/]' % wsource)
    table = Table(title='Top ' + str(len(result)) + ' predicted Phish songs (' + note + ')')
    table.add_column('#', justify='right', style='cyan', no_wrap=True)
    table.add_column('Song', style='bold')
    table.add_column('Score', justify='right')
    table.add_column('Gap', justify='right')
    table.add_column('Plays', justify='right')
    table.add_column('Overdue', justify='right')
    table.add_column('Last 25', justify='right')
    table.add_column('In 5', justify='right')

    for _, row in result.iterrows():
        gap = '-' if pd.isna(row['gap']) else str(int(row['gap']))
        table.add_row(
            str(int(row['rank'])),
            str(row['song']),
            '%.3f' % row['score'],
            gap,
            str(int(row['times_played'])),
            '%.1fx' % row['overdue'],
            str(int(row['trend_25'])),
            str(int(row['played_last_5'])),
        )
    console.print(table)


if __name__ == '__main__':
    main()
