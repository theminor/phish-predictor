import pandas as pd
import click
from rich.console import Console
from rich.table import Table

import config
import fetch
import features
import predict

console = Console()


@click.command()
@click.option('-n', '--top-n', default=config.DEFAULT_TOP_N, show_default=True,
              help='Number of predictions to show.')
@click.option('--refresh', is_flag=True, help='Force re-fetch from the API, ignoring cache.')
@click.option('--date', 'target_date', default=None,
              help='Predict for the show on YYYY-MM-DD (uses that show venue/tour/day/season).')
def main(top_n, refresh, target_date):
    """Predict Phish's most likely next songs from setlist history."""
    try:
        console.print('[bold]Loading setlist data...[/]')
        merged = fetch.get_data(force_refresh=refresh)
    except RuntimeError as e:
        console.print('[red]Error:[/] ' + str(e))
        raise SystemExit(1)

    feats = features.compute_features(merged, target_date)
    if feats.empty:
        console.print('[red]No songs to score.[/]')
        raise SystemExit(1)

    result = predict.predict(feats, top_n=top_n)

    note = 'all shows' if not target_date else 'target ' + target_date
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
