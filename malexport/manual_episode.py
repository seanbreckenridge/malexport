#!/usr/bin/env python3

import datetime
from pathlib import Path
from typing import NamedTuple, Iterator, List, Optional
from functools import lru_cache

import click
from autotui.shortcuts import load_prompt_and_writeback
from pyfzf import FzfPrompt
from more_itertools import first, last

from .list_type import ListType
from .paths import LocalDir
from .parse.xml import parse_xml, Entry


class Data(NamedTuple):
    id: int
    title: str
    number: int
    entry_type: ListType
    at: datetime.datetime


@lru_cache(maxsize=2)
def parse_xml_cached(xml_file: Path) -> List[Entry]:
    return parse_xml(xml_file).entries


def parse_ids(xml_file: Path) -> Iterator[str]:
    for entry in parse_xml_cached(xml_file):
        yield f"{entry.id}: {entry.title}"


class Picked(NamedTuple):
    id: int
    title: str


def pick_id(xml_file: Path) -> Optional[Picked]:
    # If you want to set options for FZF, you can set the FZF_DEFAULT_OPTS environment variable like
    # export FZF_DEFAULT_OPTS="--height 40% --reverse --border"
    # or
    # os.environ["FZF_DEFAULT_OPTS"] = "--height 40% --reverse --border"
    fzf = FzfPrompt()
    try:
        resp = fzf.prompt(parse_ids(xml_file), "--no-multi")
        anime_id, name = first(resp).split(":", maxsplit=1)
        return Picked(int(anime_id), name.strip())
    except ValueError:
        click.echo("No item chosen")
        return None


def add_to_history(
    entry_type: ListType,
    username: str,
    id: Optional[int] = None,
    at: Optional[datetime.datetime] = None,
    number: Optional[int] = None,
) -> Optional[Data]:
    data_dir = LocalDir.from_username(username).data_dir

    xml_file = (
        data_dir / "animelist.xml"
        if entry_type == ListType.ANIME
        else data_dir / "mangalist.xml"
    )
    if not id:
        picked = pick_id(xml_file=xml_file)
        if not picked:
            return None
        id = picked.id
        title = picked.title
    else:
        try:
            title = first([a for a in parse_xml_cached(xml_file) if a.id == id]).title
        except ValueError:
            click.echo(f"Could not find {entry_type.value} with id {id}", err=True)
            title = None

    # create a new entry
    attrs = {"id": id, "entry_type": entry_type}
    if title:
        attrs["title"] = title
    if number:
        attrs["number"] = number
    if at:
        attrs["at"] = at

    return last(
        load_prompt_and_writeback(
            Data,
            data_dir / "manual_history.yaml",
            attr_use_values=attrs,
        )
    )
