import json
from pathlib import Path
from datetime import datetime, timezone
from typing import NamedTuple, List, Iterator, Tuple, Union, Any

from ..paths import LocalDir
from ..list_type import ListType


class HistoryEntry(NamedTuple):
    at: datetime
    number: int  # episode or chapter number


class History(NamedTuple):
    mal_id: int
    list_type: str
    title: str
    entries: List[HistoryEntry]

    @property
    def url(self) -> str:
        return f"https://myanimelist.net/{self.list_type}/{self.mal_id}"


def iter_user_history(username: str) -> Iterator[History]:
    localdir = LocalDir.from_username(username)
    yield from iter_history_from_dir(localdir.data_dir)


def iter_history_from_dir(data_dir: Path) -> Iterator[History]:
    # i.e. for anime / manga
    for _type in map(str.lower, ListType.__members__):
        merged_history_file = data_dir / f"{_type}_history.json"
        # parse from both merged history and individual history files,
        # in case either one is missing
        yield from _parse_merged_history(merged_history_file, _type)
        yield from parse_history_dir(data_dir / "history" / _type, _type)


def _parse_merged_history(
    merged_history_file: Path, list_type: Union[str, ListType]
) -> Iterator[History]:
    lt: str = list_type.value.lower() if isinstance(list_type, ListType) else list_type
    if not merged_history_file.exists():
        return
    merged_data = json.loads(merged_history_file.read_text())
    for key, data in merged_data.items():
        title, entries = _parse_history_data(data)
        if len(entries) == 0:
            continue
        yield History(
            list_type=lt,
            mal_id=int(key),
            title=title,
            entries=entries,
        )


def parse_history_dir(
    history_dir: Path, list_type: Union[str, ListType]
) -> Iterator[History]:
    if not history_dir.exists():
        return
    lt: str = list_type.value.lower() if isinstance(list_type, ListType) else list_type
    for history_path in history_dir.glob("*.json"):
        assert (
            history_path.stem.isnumeric()
        ), f"Expected history JSON file, found {history_path}"
        data = json.loads(history_path.read_text())
        title, entries = _parse_history_data(data)
        # only return items which have at least one history entry
        if len(entries) == 0:
            continue
        yield History(
            list_type=lt,
            mal_id=int(history_path.stem),
            title=title,
            entries=entries,
        )


def parse_manual_history(history_file: Path) -> Iterator[History]:
    import itertools
    import autotui.shortcuts
    from ..manual_episode import Data

    if not history_file.exists():
        return

    data = autotui.shortcuts.load_from(Data, history_file)
    data.sort(key=lambda x: x.id)
    # group by episode number
    for mal_id, entries_gen in itertools.groupby(data, lambda x: x.id):
        entries = list(entries_gen)
        first = entries[0]
        yield History(
            list_type=first.entry_type.value,
            mal_id=mal_id,
            title=first.title,
            entries=[
                HistoryEntry(
                    at=entry.at,
                    number=entry.number,
                )
                for entry in entries
            ],
        )


def _parse_history_data(history_data: Any) -> Tuple[str, List[HistoryEntry]]:
    entries: List[HistoryEntry] = []
    for entry_data in history_data["episodes"]:
        [num, epoch] = entry_data
        entries.append(
            HistoryEntry(
                at=datetime.fromtimestamp(epoch, tz=timezone.utc),
                number=num,
            )
        )
    return history_data["title"], entries
