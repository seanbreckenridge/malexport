import sys
from typing import Callable, Optional

import click

from .paths import LocalDir, _iterate_local_identifiers
from .mal.account import Account


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


def _handle_account(username: str) -> Account:
    return Account(localdir=LocalDir.from_username(username=username))


@update.command(name="all")
@shared
def _all(username: str) -> None:
    """
    update all data for the account
    """
    acc = _handle_account(username)
    acc.update_lists()
    acc.update_history()
    click.secho("Done updating!", fg="green")


@update.command(name="lists", short_help="update animelist and mangalists")
@shared
def _lists(username: str) -> None:
    acc = _handle_account(username)
    acc.update_lists()


@update.command(name="history", short_help="update episode history")
@shared
def _history(username: str) -> None:
    acc = _handle_account(username)
    acc.update_history()


@update.command(name="forum", short_help="update forum posts")
@shared
def _forum(username: str) -> None:
    acc = _handle_account(username)
    acc.update_forum_posts()


if __name__ == "__main__":
    main(prog_name="malexport")
