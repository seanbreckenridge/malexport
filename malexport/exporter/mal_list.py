"""
Requests MAL Lists (animelist/mangalist) for a user,
doesn't require authentication

This requests using the load.json endpoint, the same
mechanism that works on modern MAL lists
"""

import os
import json
from typing import List
from pathlib import Path

import requests

from ..list_type import ListType
from ..common import Json, safe_request_json, logger
from ..paths import LocalDir

# this is order=5, which requests items that were edited by you recently
BASE_URL = "https://myanimelist.net/{list_type}list/{username}/load.json?status=7&order=5&offset={offset}"

LIST_USER_AGENT = os.environ.get(
    "MALEXPORT_LIST_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0",
)


OFFSET_CHUNK = 300


def handle_unauthorized(r: requests.Response) -> None:
    if r.status_code in [400, 403]:
        if (
            "Content-Type" in r.headers
            and "application/json" in r.headers["Content-Type"]
        ):
            logger.warning(r.json())
        else:
            logger.warning(r.text)
        raise RuntimeError(
            f"Auth/Permission error retrieving {r.url}, probably a permission error; the user has restricted access to their list"
        )


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
        """
        Creates the offset URL (ordered by most recently edited) for a particular type/username/offset
        This is the same request that runs when you scroll down on a modern list and the next 300 chunks
        of entries load in
        """
        return BASE_URL.format(
            list_type=self.list_type.value,
            username=self.localdir.username,
            offset=offset,
        )

    @property
    def list_path(self) -> Path:
        return self.localdir.data_dir / f"{self.list_type.value}list.json"

    def load_list(self) -> List[Json]:
        """
        Load the list from the JSON file
        """
        if self.list_path.exists():
            try:
                return list(json.loads(self.list_path.read_text()))
            except json.JSONDecodeError:
                pass
        raise FileNotFoundError(f"No file found at {self.list_type.value}")

    def update_list(self) -> None:
        """
        Paginate through all the data till you hit a chunk of data which has
        less than OFFSET_CHUNK (300) items
        """
        list_data: List[Json] = []
        # overwrite the list with new data
        offset = 0
        session = requests.Session()
        session.headers.update({"User-Agent": LIST_USER_AGENT})
        while True:
            url = self.offset_url(offset)
            new_data = safe_request_json(
                url, session=session, on_error=handle_unauthorized
            )
            list_data.extend(new_data)
            if len(new_data) < OFFSET_CHUNK:
                logger.info(
                    f"After {offset // OFFSET_CHUNK} pages, only received {len(new_data)} (typical pages have {OFFSET_CHUNK}), stopping..."
                )
                break
            offset += OFFSET_CHUNK
        encoded_data = json.dumps(list_data)
        self.list_path.write_text(encoded_data)
