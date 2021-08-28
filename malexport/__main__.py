from typing import Callable

import click

from .exporter.account import Account


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
@shared
def _history(username: str) -> None:
    acc = Account.from_username(username)
    acc.update_history()


@update.command(name="forum", short_help="update forum posts")
@shared
def _forum(username: str) -> None:
    acc = Account.from_username(username)
    acc.update_forum_posts()


if __name__ == "__main__":
    main(prog_name="malexport")
