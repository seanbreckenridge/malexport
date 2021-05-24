import sys
from typing import Callable, Optional

import click

from .paths import LocalDir, _iterate_local_identifiers


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
        default=None,
        help="Identifier/Username to use",
    ),
]


def shared(func: Callable[..., None]) -> Callable[..., None]:
    """
    Decorator to apply shared arguments
    """
    for decorator in SHARED:
        func = decorator(func)
    return func


def _handle_username(username: Optional[str]) -> str:
    """
    If the user didn't provide a username and they have only one
    account, default to that identifier
    """
    if username is not None:
        return username
    ids = _iterate_local_identifiers()
    if len(ids) == 0:
        click.echo("No accounts found, run the 'setup' command to set one up", err=True)
        sys.exit(1)
    elif len(ids) == 1:
        click.echo(f"Defaulting to '{ids[0]}'...")
        return ids[0]
    else:
        click.echo(
            f"Found multiple identifiers '{ids}', specify one with the --username flag"
        )
        sys.exit(1)


@main.command(short_help="print some info/stats about an account")
@shared
@click.option(
    "-p",
    "--print-credentials",
    is_flag=True,
    default=False,
    help="Print your saved credentials",
)
def info(username: Optional[str], print_credentials: bool) -> None:
    """
    Print some information regarding this account/identifier
    """
    username = _handle_username(username)
    ldir = LocalDir.from_username(username=username)
    assert (
        ldir.credential_path.exists()
    ), f"Expected credential file at {ldir.credential_path}. Run the 'setup' command"
    click.echo(f"Data Directory: {ldir.data_dir}")
    click.echo(f"Credential File: {ldir.credential_path}")
    if print_credentials:
        click.echo(ldir.credential_path.read_text().strip())


@main.command(short_help="initial setup")
@click.option(
    "--username",
    help="Username/Identifier for this account",
    prompt="Enter a username for this account",
    type=str,
)
def setup(username: str) -> None:
    """
    Setup an account/data directory
    """
    ldir = LocalDir.from_username(username=username)
    ldir.load_or_prompt_credentials()
    click.secho("Done! Run 'malexport update' to update your local data", fg="green")


if __name__ == "__main__":
    main(prog_name="malexport")
