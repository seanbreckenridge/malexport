import json
from typing import List

import requests

from ..paths import LocalDir, _expand_file
from ..common import safe_request_json, Json
from ..log import logger


class FriendDownloader:
    """
    Download friends for a user
    """

    def __init__(self, localdir: LocalDir) -> None:
        self.localdir = localdir
        self.friend_index_path = _expand_file(self.localdir.data_dir / "friends.json")
        self.friend_chunk_size = 100

    def friend_page_url(self, page: int) -> str:
        assert page >= 1
        if page == 1:
            return f"https://api.jikan.moe/v3/user/{self.localdir.username}/friends"
        else:
            return (
                f"https://api.jikan.moe/v3/user/{self.localdir.username}/friends/{page}"
            )

    def download_friend_index(self) -> List[Json]:
        page = 1
        data: List[Json] = []
        while True:
            try:
                new_data = safe_request_json(self.friend_page_url(page))
                assert (
                    "friends" in new_data
                ), f"No friends key in Jikan response: {new_data}"
                data.extend(new_data["friends"])
                # hit the last page (or there was no data, if we're on the first page)
                if len(new_data["friends"]) < self.friend_chunk_size:
                    return data
            except requests.exceptions.RequestException:
                # failed too many times? Assume Jikan failed for some reason,
                # or we've hit a page that doesn't exist (if user had a multiple
                # of friends that was exactly self.friend_chunk_size)
                # we don't want to overwrite if a pagination failed, so return
                # an empty list
                return []
            page += 1

    def update_friend_index(self) -> None:
        """
        Paginate through friends till you hit a chunk of data which has nothing
        """
        friends = self.download_friend_index()
        # in case this was an error, don't overwrite data with nothing
        if len(friends) == 0:
            logger.info(
                f"No friends found for {self.localdir.username} (could've failed to request, or user has no friends), skipping write to file..."
            )
            return
        self.friend_index_path.write_text(json.dumps(friends))
