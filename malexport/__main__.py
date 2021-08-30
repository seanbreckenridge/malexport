import os
from typing import Callable, Optional

import click

from .exporter import Account
from .parse import parse_xml, parse_list
from .common import serialize
from .list_type import ListType


@click.group()
def main() -> None:
    """
    malexport
    """


# shared click options/args
SHARED = [
    click.option(
        "-u",
        "--username",
        "username",
        required=True,
        help="Username to use",
    ),
]


def shared(func: Callable[..., None]) -> Callable[..., None]:
    """
    Decorator to apply shared arguments
    """
    for decorator in SHARED:
        func = decorator(func)
    return func


@main.group()
def update() -> None:
    """
    update data for an account
    """


@update.command(name="all", short_help="update all data")
@shared
def _all(username: str) -> None:
    """
    update all data for the account
    """
    acc = Account.from_username(username)
    acc.update_lists()
    acc.update_exports()
    acc.update_forum_posts()
    acc.update_history()
    click.secho("Done updating!", fg="green")


@update.command(name="lists", short_help="update animelist and mangalists")
@shared
def _lists(username: str) -> None:
    acc = Account.from_username(username)
    acc.update_lists()


@update.command(name="export", short_help="export xml lists")
@shared
def _export(username: str) -> None:
    acc = Account.from_username(username)
    acc.update_exports()


@update.command(name="history", short_help="update episode history")
@click.option(
    "-o",
    "--only",
    type=click.Choice(["anime", "manga"], case_sensitive=False),
    required=False,
    help="Only update anime or manga history specifically",
)
@shared
def _history(username: str, only: Optional[str]) -> None:
    acc = Account.from_username(username)
    only_update: Optional[ListType] = None
    if only is not None:
        only_update = ListType.__members__[only.upper()]
    acc.update_history(only=only_update)


@update.command(name="forum", short_help="update forum posts")
@shared
def _forum(username: str) -> None:
    acc = Account.from_username(username)
    acc.update_forum_posts()


@main.group(name="parse")
def parse() -> None:
    """parse the resulting exported files"""


@parse.command(name="xml", short_help="parse the XML export files")
@click.argument("XML_FILE")
def _xml(xml_file: str) -> None:
    xml_data = parse_xml(xml_file)
    click.echo(serialize(xml_data))


@parse.command(name="list", short_help="parse the list file")
@click.option(
    "--type",
    "_type",
    type=click.Choice(["anime", "manga"], case_sensitive=False),
    required=False,
    help="Specify type of list. If not supplied, this tries to guess based on the filename",
)
@click.argument("LIST_FILE")
def _list(_type: Optional[str], list_file: str) -> None:
    chosen_type: ListType
    if _type is not None:
        chosen_type = ListType.__members__[_type.upper()]
    else:
        chosen_type = (
            ListType.ANIME if "anime" in os.path.basename(list_file) else ListType.MANGA
        )
    list_data = parse_list(list_file, list_type=chosen_type)
    click.echo(serialize(list_data))


if __name__ == "__main__":
    main(prog_name="malexport")
