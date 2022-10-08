"""
calculates the length of completed anime between two years
prints number of seconds
"""

from pathlib import Path
from datetime import date
import click

from malexport.parse import iter_api_list, ListType


@click.command()
@click.option("--start-year", default=1978, type=int)
@click.option("--end-year", default=date.today().year, type=int)
@click.argument("API_LIST_FILE", type=click.Path(exists=True, path_type=Path))
def main(start_year: int, end_year: int, api_list_file: Path) -> None:
    total_seconds = 0
    for a in iter_api_list(api_list_file, list_type=ListType.ANIME):
        if (
            a.start_date is None
            or a.end_date is None
            or a.average_episode_duration is None
            or a.episode_count is None
        ):
            continue
        if a.episode_count <= 0 or a.average_episode_duration <= 0:
            continue
        if a.start_date.year < start_year or a.end_date.year > end_year:
            continue
        secs = a.average_episode_duration * a.episode_count
        assert secs >= 0, str(a)
        total_seconds += secs
    click.echo(total_seconds)


if __name__ == "__main__":
    main()
