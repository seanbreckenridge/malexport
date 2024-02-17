import os
import sys
from pathlib import Path
from typing import Callable, Optional, Any, Literal, List

import click

from .list_type import ListType
from .paths import default_zip_base


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
    envvar="MAL_USERNAME",
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
    acc.update_messages()


@update.command(name="lists", short_help="update animelist and mangalists")
@apply_shared(USERNAME, ONLY)
def _lists_update(only: str, username: str) -> None:
    from .exporter import Account

    acc = Account.from_username(username)
    only_update: Optional[ListType] = None
    if only is not None:
        only_update = ListType.__members__[only.upper()]
    acc.update_lists(only=only_update)


@update.command(name="messages", short_help="update messages (DMs)")
@apply_shared(USERNAME)
@click.option(
    "--thread-count",
    type=int,
    default=None,
    help="how many new threads to update before giving up",
)
@click.option(
    "--start-page", type=int, default=1, help="which page to start requesting from"
)
def _messages_update(
    username: str, start_page: int, thread_count: Optional[int] = None
) -> None:
    from .exporter import Account

    acc = Account.from_username(username)
    acc.update_messages(start_page=start_page, thread_count=thread_count)


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
@click.option(
    "--use-merged-file",
    default=False,
    is_flag=True,
    envvar="MALEXPORT_USE_MERGED_FILE",
    help="use a single merged JSON file instead of storing history data in individual files",
)
def _history(
    username: str,
    only: Optional[str],
    driver_type: str,
    count: Optional[int],
    use_merged_file: bool,
) -> None:
    from .exporter import Account

    acc = Account.from_username(username)
    only_update: Optional[ListType] = None
    if only is not None:
        only_update = ListType.__members__[only.upper()]
    acc.update_history(
        only=only_update,
        count=count,
        driver_type=driver_type,
        use_merged_file=use_merged_file,
    )


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
@click.argument("XML_FILE", type=click.Path(exists=True))
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
@click.argument("LIST_FILE", type=click.Path(exists=True))
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
            sys.stdout.write("\n")
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
@click.argument("API_LIST_FILE", type=click.Path(exists=True))
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
            sys.stdout.write("\n")
        sys.stdout.flush()
    else:
        click.echo(serialize(list(idata)))


@parse.command(name="forum", short_help="extract forum posts by your user")
@apply_shared(USERNAME)
def _forum_parse(username: str) -> None:
    from .parse import iter_forum_posts
    from .common import serialize

    click.echo(serialize(list(iter_forum_posts(username))))


@parse.command(name="manual-history", short_help="parse manually entered user history")
@apply_shared(USERNAME)
@click.option(
    "-o",
    "--output",
    type=click.Choice(["json", "jsonl", "markdown"]),
    help="output format. Defaults to json",
    default="json",
)
def _manual_history_parse(
    username: str, output: Literal["json", "jsonl", "markdown"]
) -> None:
    from .parse.history import parse_manual_history, History
    from .paths import LocalDir
    from .common import serialize

    localdir = LocalDir.from_username(username)
    data: List[History] = list(
        parse_manual_history(localdir.data_dir / "manual_history.yaml")
    )

    if output == "json":
        click.echo(serialize(data))
    elif output == "jsonl":
        for hist in data:
            for ent in hist.entries:
                click.echo(
                    serialize(
                        {
                            "title": hist.title,
                            "list_type": hist.list_type,
                            "number": ent.number,
                            "at": ent.at,
                        }
                    )
                )

    else:
        from datetime import datetime

        items = []
        for hist in data:
            for ent in hist.entries:
                items.append((hist.title, hist.list_type, ent.number, ent.at))

        items.sort(key=lambda x: x[3])

        for title, list_type, number, at in items:
            ldt = datetime.fromtimestamp(at.timestamp())
            click.echo(
                f"# {title}\n{'Episode' if list_type == 'anime' else 'Chapter'} {number} - {ldt}"
            )


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


@parse.command(name="messages", short_help="parse downloaded message history")
@apply_shared(USERNAME)
def _messages_parse(username: str) -> None:
    from .parse import iter_user_threads
    from .common import serialize

    click.echo(serialize(list(iter_user_threads(username))))


@parse.command(name="friends", short_help="parse user friends")
@apply_shared(USERNAME)
def _friends_parse(username: str) -> None:
    from .common import serialize
    from .parse import iter_friends

    click.echo(serialize(list(iter_friends(username))))


@main.group(short_help="recover data for deleted MAL entries")
def recover_deleted() -> None:
    """
    lets you recover data from zip backups of your malexport dir
    """


_ISO_FORMAT = "%Y-%m-%dT%H-%M-%SZ"


def utcnow() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime(_ISO_FORMAT)


@recover_deleted.command(short_help="zips your current malexport dir")
@apply_shared(USERNAME)
def backup(username: str) -> None:
    import shutil

    from .paths import default_zip_base
    from .exporter import Account

    backup_to_dir = default_zip_base / username
    backup_to_dir.mkdir(parents=True, exist_ok=True)
    from_dir = Account.from_username(username).localdir.data_dir

    backup_zip_base = str(backup_to_dir / f"{utcnow()}")
    backup_zip_full = f"{backup_zip_base}.zip"

    # shutil doesn't want the '.zip' at the end of the file
    # automatically compresses if possible
    shutil.make_archive(backup_zip_base, "zip", root_dir=from_dir, base_dir=".")

    click.echo(f"Backed up {from_dir} to {backup_zip_full}", err=True)
    click.echo(
        "Backup Size: {:.2f} MB".format(Path(backup_zip_full).stat().st_size / 1024**2),
        err=True,
    )


@recover_deleted.command(short_help="stats about mal-id-cache git dir")
def approved_ids_stats() -> None:
    from .parse.recover_deleted_entries import Approved

    Approved.git_pull()
    apr = Approved.parse_from_git_dir()

    click.echo(f"Approved Anime: {len(apr.anime)}")
    click.echo(f"Approved Manga: {len(apr.manga)}")


@recover_deleted.command(short_help="update approved ids")
def approved_update() -> None:
    from .parse.recover_deleted_entries import Approved

    commit_id_before, commit_id_after = Approved.git_pull()

    if commit_id_before == commit_id_after:
        click.echo("Git repo is up to date", err=True)
    else:
        click.echo(
            f"Updated git repo from {commit_id_before} to {commit_id_after}", err=True
        )


@recover_deleted.command(short_help="recover deleted MAL entries from your zip backups")
@click.option(
    "--data-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=str(default_zip_base),
)
@click.option(
    "-F",
    "--filter-with-activity",
    is_flag=True,
    help="only return items which have some activity (read/watched)",
)
@apply_shared(ONLY)
def recover(data_dir: Path, filter_with_activity: bool, only: str) -> None:
    from .parse.recover_deleted_entries import recover_deleted as rec_del, Approved
    from .common import serialize

    full_resp = {}

    for acc in data_dir.iterdir():
        username = acc.name
        zips = sorted(acc.glob("*.zip"), key=lambda x: x.name)

        rec_anime, rec_manga = rec_del(
            approved=Approved.parse_from_git_dir(),
            username=username,
            backups=zips,
            filter_with_activity=filter_with_activity,
        )

        resp: Any = {
            "anime": rec_anime,
            "manga": rec_manga,
        }

        # if user specified only, only return that type
        if only:
            assert only in resp
            resp = resp[only]
            assert isinstance(resp, list)

        full_resp[username] = resp
    click.echo(serialize(full_resp))


@main.command(short_help="add a history episode manually")
@apply_shared(USERNAME)
@click.option(
    "-t",
    "--type",
    "type_",
    type=click.Choice(["anime", "manga"]),
    default="anime",
    help="type of entry to add",
)
@click.option(
    "--at",
    type=int,
    default=None,
    help="unix timestamp of when you watched/read this episode/chapter",
)
@click.option(
    "-i",
    "--id",
    type=int,
    required=False,
    help="ID to add",
    default=None,
)
@click.option(
    "-l",
    "--loop",
    is_flag=True,
    default=False,
    help="Add multiple episodes/chapters",
)
@click.option(
    "-n",
    "--number",
    prompt=True,
    required=True,
    type=int,
    help="Which episode/chapter to add",
)
def manual_history(
    username: str,
    type_: str,
    at: int,
    id: Optional[int],
    loop: bool,
    number: int,
) -> None:
    """
    This lets you add to your user history manually, for example if you
    watched one episode but dont want to mess with MAL to mark just that
    one episode as watched.
    """
    from datetime import datetime, timezone
    from .manual_episode import add_to_history

    entry_type = ListType.ANIME if type_ == "anime" else ListType.MANGA
    while True:
        item = add_to_history(
            username=username,
            entry_type=entry_type,
            at=datetime.fromtimestamp(at, tz=timezone.utc) if at else None,
            id=id,
            number=number,
        )
        if item:
            click.echo(f"Added: {item}", err=True)
        if loop:
            if not click.confirm("Add another episode?", default=True):
                break
        else:
            break


if __name__ == "__main__":
    main(prog_name="malexport")
