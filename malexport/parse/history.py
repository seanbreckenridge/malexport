import json
from pathlib import Path
from datetime import datetime, timezone
from typing import NamedTuple, List, Iterator, Tuple, Union

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
    history_dir = localdir.data_dir / "history"
    # i.e. for anime / manga
    for _type in map(str.lower, ListType.__members__):
        yield from parse_history_dir(history_dir / _type, _type)


def parse_history_dir(
    history_dir: Path, list_type: Union[str, ListType]
) -> Iterator[History]:
    lt: str = list_type.value.lower() if isinstance(list_type, ListType) else list_type
    for history_path in history_dir.glob("*.json"):
        assert (
            history_path.stem.isnumeric()
        ), f"Expected history JSON file, found {history_path}"
        title, entries = _parse_history_file(history_path)
        # only return items which have at least one history entry
        if len(entries) == 0:
            continue
        yield History(
            list_type=lt,
            mal_id=int(history_path.stem),
            title=title,
            entries=entries,
        )


def _parse_history_file(history_path: Path) -> Tuple[str, List[HistoryEntry]]:
    history_data = json.loads(history_path.read_text())
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
