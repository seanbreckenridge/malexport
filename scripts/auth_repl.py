#!/usr/bin/env python3
# a script to let me use my authenticated
# session in a REPL to interact with the API

BASE = "https://api.myanimelist.net/v2"

import click
import IPython  # type: ignore[import]
from malexport.exporter import Account

try:
    from my.config.seanb.malexport_secret import *  # type: ignore
except ImportError:
    pass


@click.command()
@click.option(
    "-u",
    "--username",
    "username",
    required=True,
    help="Username to use",
)
def main(username: str) -> None:
    acc = Account.from_username(username)
    acc.mal_api_authenticate()
    mal_session = acc.mal_session
    assert mal_session is not None
    sess = mal_session.session
    req = mal_session.safe_json_request
    click.secho(
        "Use 'sess' to interact with the requests.Session, or 'req' to make a JSON request"
    )
    click.echo("Docs: https://myanimelist.net/apiconfig/references/api/v2")
    IPython.embed()


if __name__ == "__main__":
    main()
