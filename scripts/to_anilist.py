#!/usr/bin/env python3

"""
A script to convert my XML export into chunks, so that
it can imported to anilist without cloudflare timing out
"""

from functools import partial
from typing import Tuple
from pathlib import Path

import click
import lxml.etree as ET
from malexport.list_type import ListType
from malexport.paths import LocalDir
from malexport.exporter import ExportDownloader

REMOVE_ATTRS = set(["my_tags"])


def remove_attrs(
    xml_file: Path, media_type: ListType, filter_activity: bool
) -> Tuple[str, int]:
    tree = ET.parse(str(xml_file))
    root = tree.getroot()
    root.remove(root.find("myinfo"))
    for entry in root.findall(media_type.value):
        for attr in entry:
            if attr.tag in REMOVE_ATTRS:
                entry.remove(attr)
        if not filter_activity:
            continue
        # if this has some sort of activity
        has_score = str(entry.find("my_score").text).strip() != "0"
        start_date = str(entry.find("my_start_date").text).strip()
        has_start_date: bool = len(start_date) > 0 and not start_date.startswith("0000")
        completed: bool = str(entry.find("my_status").text).strip() == "Completed"
        # episodes or chapters
        tag_name = (
            "my_watched_episodes"
            if media_type == ListType.ANIME
            else "my_read_chapters"
        )
        has_progress: bool = str(entry.find(tag_name).text).strip() != "0"
        if has_start_date or has_score or completed or has_progress:
            continue
        root.remove(entry)
    return ET.tostring(root, encoding="unicode"), len(root.findall(media_type.value))


def extract_xml_range(xml_data: str, media_type: ListType, in_range: range) -> str:
    tree = ET.fromstring(xml_data)
    for i, tag in enumerate(tree.findall(media_type.value)):
        if i not in in_range:
            tree.remove(tag)
    return str(ET.tostring(tree, encoding="unicode"))


def run_type(
    xml_file: Path,
    media_type: ListType,
    chunk_size: int,
    in_dir: Path,
    filter_activity: bool,
) -> None:
    cleaned_tree, element_count = remove_attrs(xml_file, media_type, filter_activity)
    m = media_type.value
    lower, upper = 0, chunk_size
    while lower < element_count:
        target = in_dir / f"{m}_{str(upper // chunk_size).zfill(3)}.xml"
        click.echo(f"Chunking {m} from {lower} to {upper} to {str(target)}")
        chunked_xml = extract_xml_range(cleaned_tree, media_type, range(lower, upper))
        target.write_text(chunked_xml)
        lower, upper = upper, upper + chunk_size


@click.command(help=__doc__)
@click.option("-u", "--username", envvar="MAL_USERNAME", required=True)
@click.option("-c", "--chunk-size", default=3000)
@click.option(
    "-d",
    "--to-dir",
    type=click.Path(dir_okay=True, file_okay=False, path_type=Path),
    default=Path("."),
    help="Directory to write chunked xml files to",
)
@click.option(
    "-r",
    "--remove-items-without-activity",
    is_flag=True,
    default=False,
    help="Removes any items which don't have activity (a score, start date, on my completed, or has some episode/chapter progress)",
)
def main(
    username: str, chunk_size: int, to_dir: Path, remove_items_without_activity: bool
) -> None:
    ex = ExportDownloader(LocalDir.from_username(username))
    run_with_opts = partial(
        run_type,
        chunk_size=chunk_size,
        in_dir=to_dir,
        filter_activity=remove_items_without_activity,
    )
    if ex.animelist_path.exists():
        run_with_opts(ex.animelist_path, ListType.ANIME)
    else:
        print(f"{ex.animelist_path} doesn't exist, run 'malexport update export' first")
    if ex.mangalist_path.exists():
        run_with_opts(ex.mangalist_path, ListType.MANGA)
    else:
        print(f"{ex.mangalist_path} doesn't exist, run 'malexport update export' first")


if __name__ == "__main__":
    main()
