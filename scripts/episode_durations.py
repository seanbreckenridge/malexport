"""
This lists the duration of each episode and the total duration of each anime in your list.
This uses the average episode duration from the API list and the episode count from the XML list.

To use this, I would recommend first updating all your local data

malexport update lists -u <username>
malexport update api-lists -u <username>
malexport update export -u <username>
"""

import json
import csv
from typing import NamedTuple, Optional, List, Literal, get_args

import click
from malexport.__main__ import USERNAME
from malexport.parse.combine import combine


class DurationInfo(NamedTuple):
    anime_id: int
    title: str
    number_of_episodes: int
    duration_per_episode: int
    total_duration: int  # if there is no episode count, this will be None


OutputFormat = Literal["pprint", "csv", "json"]


@click.command()
@USERNAME
@click.option(
    "--output-format",
    type=click.Choice(get_args(OutputFormat), case_sensitive=False),
    default="csv",
    help="Output format",
)
@click.option(
    "--sort-by",
    type=click.Choice(list(DurationInfo._fields), case_sensitive=False),
    default="title",
    help="Sort by the given field",
)
@click.option(
    "--reverse",
    is_flag=True,
    help="Reverse the sort order",
)
def main(
    username: str, output_format: OutputFormat, sort_by: str, reverse: bool
) -> None:
    anime_data, _ = combine(username)
    durations: List[DurationInfo] = []

    for anime in anime_data:
        assert (
            anime.APIList is not None
        ), f"missing apilist data for id {anime.XMLData.anime_id}, update with `malexport update api-lists -u {username}`"
        assert anime.APIList.average_episode_duration is not None

        # default to 0 if theres no data
        # this makes sorting easier and can just remove rows later if needed
        total_duration = (anime.XMLData.episodes or 0) * (
            anime.APIList.average_episode_duration or 0
        )

        durations.append(
            DurationInfo(
                anime_id=anime.id,
                title=anime.XMLData.title,
                number_of_episodes=anime.XMLData.episodes,
                duration_per_episode=anime.APIList.average_episode_duration,
                total_duration=total_duration,
            )
        )

    durations.sort(key=lambda x: getattr(x, sort_by), reverse=reverse)

    csv_writer = csv.writer(
        click.get_text_stream("stdout"),
        delimiter=",",
        lineterminator="\n",
        quoting=csv.QUOTE_ALL,
    )

    for duration in durations:
        match output_format:
            case "pprint":
                print(duration)
            case "csv":
                csv_writer.writerow([*duration._asdict().values()])
            case "json":
                click.echo(json.dumps(duration._asdict()))


if __name__ == "__main__":
    main()
