from typing import Callable, Optional

import click

from .exporter.account import Account, ListType


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
    acc.update_history()
    acc.update_forum_posts()
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


if __name__ == "__main__":
    main(prog_name="malexport")
