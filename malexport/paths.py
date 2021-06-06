"""
Relating to storing credentials and handling location of the data/config directories
"""

import os
from pathlib import Path
from typing import NamedTuple, List, Union

import click
import yaml

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


class Credentials(NamedTuple):
    username: str
    password: str


def _expand_path(pathish: Union[str, Path], is_dir: bool = True) -> Path:
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


class LocalDir(NamedTuple):
    application_base: Path
    config_base: Path
    username: str

    @property
    def credentials(self) -> Credentials:
        return self.load_or_prompt_credentials()

    @property
    def credential_path(self) -> Path:
        return self.config_base / f"{self.username}.yaml"

    def load_or_prompt_credentials(self) -> Credentials:
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
        return Credentials(
            username=data["username"],
            password=data["password"],
        )

    @property
    def data_dir(self) -> Path:
        return _expand_path(self.application_base / self.username / "data")

    @staticmethod
    def from_username(
        *,
        username: str,
        data_dir: Path = default_data_dir,
        conf_dir: Path = default_conf_dir,
    ) -> "LocalDir":
        return LocalDir(
            application_base=_expand_path(data_dir),
            config_base=_expand_path(conf_dir),
            username=username,
        )


def _iterate_local_identifiers() -> List[str]:
    """
    Loop through all local account identifiers
    """
    return [
        p
        for p in os.listdir(default_data_dir)
        if os.path.isdir(os.path.join(default_data_dir, p))
    ]
