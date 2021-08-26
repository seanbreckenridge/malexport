import json
from enum import Enum
from typing import List
from pathlib import Path

from ..common import Json, safe_request_json
from ..paths import LocalDir

base_url = "https://myanimelist.net/{list_type}/{username}/load.json?status=7&order=5&offset={offset}"


OFFSET_CHUNK = 300


class ListType(Enum):
    ANIME = "animelist"
    MANGA = "mangalist"


class MalList:
    """
    Requests/Updates the load.json endpoint for a particular user and list type
    """

    def __init__(self, list_type: ListType, localdir: LocalDir):
        self.list_type = list_type
        self.localdir = localdir

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(list_type={self.list_type}, localdir={self.localdir})"

    __str__ = __repr__

    def offset_url(self, offset: int) -> str:
        return base_url.format(
            list_type=self.list_type.value,
            username=self.localdir.username,
            offset=offset,
        )

    @property
    def list_path(self) -> Path:
        return self.localdir.data_dir / f"{self.list_type.value}.json"

    def load_list(self) -> List[Json]:
        if self.list_path.exists():
            try:
                return list(json.loads(self.list_path.read_text()))
            except ValueError:
                pass
        return []

    def update_list(self) -> None:
        list_data: List[Json] = []
        # overwrite the list with new data
        offset = 0
        while True:
            url = self.offset_url(offset)
            new_data = safe_request_json(url)
            list_data.extend(new_data)
            if len(new_data) < OFFSET_CHUNK:
                break
            offset += OFFSET_CHUNK
        self.list_path.write_text(json.dumps(list_data))
