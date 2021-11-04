import json
from typing import Iterator

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

    def download_friend_index(self) -> Iterator[Json]:
        page = 1
        while True:
            try:
                new_data = safe_request_json(self.friend_page_url(page))
                if "friends" in new_data and len(new_data["friends"]) > 0:
                    nfriends = new_data["friends"]
                    yield from nfriends
                    # hit the last page
                    if len(nfriends) < self.friend_chunk_size:
                        return
            except requests.exceptions.RequestException:
                # failed too many times? Assume Jikan failed for some reason,
                # or we've hit a page that doesn't exist (if user had a multiple
                # of friends that was exactly self.friend_chunk_size)
                return
            page += 1

    def update_friend_index(self) -> None:
        """
        Paginate through friends till you hit a chunk of data which has nothing
        """
        friends = list(self.download_friend_index())
        # in case this was an error, don't overwrite data with nothing
        if len(friends) == 0:
            logger.info(
                f"No friends found for {self.localdir.username}, skipping write to file..."
            )
            return
        encoded_data = json.dumps(friends)
        self.friend_index_path.write_text(encoded_data)
