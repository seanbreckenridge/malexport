"""
Relating to storing credentials and handling location of the data/config directories
"""

import os
import json
from pathlib import Path
from typing import Union, Dict

import yaml
import click

PathIsh = Union[str, Path]

default_local_dir = os.path.join(Path.home(), ".local", "share")
local_directory: str = os.environ.get("XDG_DATA_HOME", default_local_dir)

default_config_dir = os.path.join(Path.home(), ".config")
config_directory: str = os.environ.get("XDG_CONFIG_HOME", default_config_dir)

default_data_dir = Path(local_directory) / "malexport"
default_conf_dir = Path(config_directory) / "malexport"

if "MALEXPORT_DIR" in os.environ:
    default_data_dir = Path(os.environ["MALEXPORT_DIR"])

if "MALEXPORT_CFG" in os.environ:
    default_conf_dir = Path(os.environ["MALEXPORT_CFG"])

default_data_dir.mkdir(exist_ok=True, parents=True)
default_conf_dir.mkdir(exist_ok=True, parents=True)


def _expand_path(pathish: PathIsh, is_dir: bool = True) -> Path:
    """
    given some path-like input, expand the path
    if is_dir:
        make that directory if it doesnt exist
    else:
        make the parent directory, assuming this is a file
    """
    p: Path
    if isinstance(pathish, str):
        p = Path(pathish)
    else:
        p = pathish
    p = p.expanduser().absolute()
    if is_dir:
        p.mkdir(parents=True, exist_ok=True)
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _expand_file(pathish: PathIsh) -> Path:
    return _expand_path(pathish, is_dir=False)


class LocalDir:
    def __init__(self, application_base: Path, config_base: Path, username: str):
        self.application_base: Path = _expand_path(application_base)
        self.config_base: Path = _expand_path(config_base)
        self.username: str = username

        # to save your personal Client ID from the MAL Dashboard
        self.mal_client_info = self.config_base / "mal_client_id.json"

        # where to save oauth refresh info
        self.refresh_info: Path = (
            _expand_path(self.config_base / "accounts")
            / f"{self.username}_refresh_info.json"
        )

        # To save MAL Username/Password
        self.credential_path: Path = (
            _expand_path(self.config_base / "accounts")
            / f"{self.username}_credentials.yaml"
        )

        # Base directory to store all data
        self.data_dir = _expand_path(self.application_base / self.username)

    def load_or_prompt_mal_client_info(self) -> Dict[str, str]:
        if not self.mal_client_info.exists():
            click.echo(
                "No MAL Client Id/Secret found, create an ID (other/hobbyist) at https://myanimelist.net/apiconfig"
            )
            client_id = click.prompt(text="Client ID")
            with self.mal_client_info.open("w") as f:
                json.dump({"client_id": client_id}, f)
        with self.mal_client_info.open() as f:
            data: Dict[str, str] = json.load(f)
            return data

    def load_or_prompt_credentials(self) -> Dict[str, str]:
        if not self.credential_path.exists():
            click.echo(
                "No credentials found. Enter your username/password for MAL. These are stored locally and used to authenticate a session with MAL",
                err=True,
            )
            username = click.prompt(text="MAL Username")
            password = click.prompt(text="MAL Password")
            with open(self.credential_path, "w") as f:
                yaml.dump({"username": username, "password": password}, f)
                click.echo("Saved to {}".format(self.credential_path))
        with open(self.credential_path) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        return dict(
            username=data["username"],
            password=data["password"],
        )

    @staticmethod
    def from_username(
        username: str,
        *,
        data_dir: Path = default_data_dir,
        conf_dir: Path = default_conf_dir,
    ) -> "LocalDir":
        return LocalDir(
            application_base=_expand_path(data_dir),
            config_base=_expand_path(conf_dir),
            username=username,
        )
