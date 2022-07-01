import os
import sys
from typing import Callable, Optional, Any

import click

from .list_type import ListType


@click.group()
def main() -> None:
    """
    exports your data from MyAnimeList
    """


# shared click options/args
USERNAME = click.option(
    "-u",
    "--username",
    "username",
    required=True,
    help="Username to use",
)

ONLY = click.option(
    "-o",
    "--only",
    type=click.Choice(["anime", "manga"], case_sensitive=False),
    required=False,
    help="Only update anime or manga history specifically",
)

STREAM = click.option(
    "-s",
    "--stream",
    is_flag=True,
    default=False,
    help="Stream JSON objects instead of printing a list",
)


def apply_shared(*chosen: Any) -> Any:
    """
    Decorator to apply the username argument
    """

    def _add_options(func: Callable[..., None]) -> Callable[..., None]:
        for dec in chosen:
            func = dec(func)
        return func

    return _add_options


@main.group()
def update() -> None:
    """
    update data for an account
    """


@update.command(name="all", short_help="update all data")
@apply_shared(USERNAME)
def _all(username: str) -> None:
    """
    update all data for the account
    """
    from .exporter import Account

    acc = Account.from_username(username)
    acc.update_lists()
    acc.update_api_lists()
    acc.update_forum_posts()
    acc.update_history()
    acc.update_friends()
    acc.update_exports()


@update.command(name="lists", short_help="update animelist and mangalists")
@apply_shared(USERNAME, ONLY)
def _lists_update(only: str, username: str) -> None:
    from .exporter import Account

    acc = Account.from_username(username)
    only_update: Optional[ListType] = None
    if only is not None:
        only_update = ListType.__members__[only.upper()]
    acc.update_lists(only=only_update)


@update.command(
    name="api-lists", short_help="update animelist and mangalists using the API"
)
@apply_shared(USERNAME, ONLY)
def _api_lists(only: str, username: str) -> None:
    from .exporter import Account

    acc = Account.from_username(username)
    only_update: Optional[ListType] = None
    if only is not None:
        only_update = ListType.__members__[only.upper()]
    acc.update_api_lists(only=only_update)


@update.command(name="export", short_help="export xml lists")
@apply_shared(USERNAME)
def _export(username: str) -> None:
    from .exporter import Account

    acc = Account.from_username(username)
    acc.update_exports()


@update.command(name="history", short_help="update episode history")
@apply_shared(USERNAME, ONLY)
@click.option(
    "-c",
    "--count",
    "count",
    default=None,
    type=int,
    help="Only request the first 'count' entries in the users episode history",
)
@click.option(
    "--driver-type",
    default="chrome",
    type=click.Choice(["chrome", "firefox"]),
    help="whether to use chromedriver/geckodriver as the selenium browser",
)
def _history(
    username: str, only: Optional[str], driver_type: str, count: Optional[int]
) -> None:
    from .exporter import Account

    acc = Account.from_username(username)
    only_update: Optional[ListType] = None
    if only is not None:
        only_update = ListType.__members__[only.upper()]
    acc.update_history(only=only_update, count=count, driver_type=driver_type)


@update.command(name="forum", short_help="update forum posts")
@apply_shared(USERNAME)
def _forum(username: str) -> None:
    from .exporter import Account

    acc = Account.from_username(username)
    acc.update_forum_posts()


@update.command(name="friends", short_help="update friends")
@apply_shared(USERNAME)
def _friends(username: str) -> None:
    from .exporter import Account

    acc = Account.from_username(username)
    acc.update_friends()


@main.group(name="parse")
def parse() -> None:
    """parse the resulting exported files"""


@parse.command(name="xml", short_help="parse the XML export files")
@click.argument("XML_FILE")
def _xml(xml_file: str) -> None:
    from .parse import parse_xml
    from .common import serialize

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
@apply_shared(STREAM)
@click.argument("LIST_FILE")
def _list_parse(_type: Optional[str], list_file: str, stream: bool) -> None:
    from .parse import parse_list
    from .common import serialize

    chosen_type: ListType
    if _type is not None:
        chosen_type = ListType.__members__[_type.upper()]
    else:
        # infer type
        chosen_type = (
            ListType.ANIME if "anime" in os.path.basename(list_file) else ListType.MANGA
        )
    idata = parse_list(list_file, list_type=chosen_type)
    if stream:
        for i in idata:
            sys.stdout.write(serialize(i))
        sys.stdout.flush()
    else:
        click.echo(serialize(list(idata)))


@parse.command(name="api-list", short_help="parse the API list file")
@click.option(
    "--type",
    "_type",
    type=click.Choice(["anime", "manga"], case_sensitive=False),
    required=False,
    help="Specify type of list. If not supplied, this tries to guess based on the filename",
)
@apply_shared(STREAM)
@click.argument("API_LIST_FILE")
def _api_list_file(_type: Optional[str], api_list_file: str, stream: bool) -> None:
    from .parse import iter_api_list
    from .common import serialize

    chosen_type: ListType
    if _type is not None:
        chosen_type = ListType.__members__[_type.upper()]
    else:
        # infer type
        chosen_type = (
            ListType.ANIME
            if "anime" in os.path.basename(api_list_file)
            else ListType.MANGA
        )
    idata = iter_api_list(api_list_file, list_type=chosen_type)
    if stream:
        for i in idata:
            sys.stdout.write(serialize(i))
        sys.stdout.flush()
    else:
        click.echo(serialize(list(idata)))


@parse.command(name="forum", short_help="extract forum posts by your user")
@apply_shared(USERNAME)
def _forum_parse(username: str) -> None:
    from .parse import iter_forum_posts
    from .common import serialize

    click.echo(serialize(list(iter_forum_posts(username))))


@parse.command(
    name="combine", short_help="combines lists, api-lists, xml and history data"
)
@apply_shared(USERNAME, ONLY)
def _combine_parse(only: Optional[str], username: str) -> None:
    """
    This combines relevant info from the lists, xml and history files
    It removes some of the commonly unused fields, and uses the xml for rewatch info/better dates

    It doesn't require you have a list export
    """
    from .parse.combine import combine
    from .common import serialize

    anime, manga = combine(username)
    if only == "anime":
        click.echo(serialize(anime))
    elif only == "manga":
        click.echo(serialize(manga))
    else:
        click.echo(serialize({"anime": anime, "manga": manga}))


@parse.command(name="history", short_help="parse downloaded user history")
@apply_shared(USERNAME)
def _history_parse(username: str) -> None:
    from .parse import iter_user_history
    from .common import serialize

    click.echo(serialize(list(iter_user_history(username))))


@parse.command(name="friends", short_help="parse user friends")
@apply_shared(USERNAME)
def _friends_parse(username: str) -> None:
    from .common import serialize
    from .parse import iter_friends

    click.echo(serialize(list(iter_friends(username))))


if __name__ == "__main__":
    main(prog_name="malexport")
