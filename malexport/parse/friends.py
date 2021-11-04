from typing import NamedTuple, Iterator
from datetime import datetime
import json

from ..paths import LocalDir
from ..log import logger


class Friend(NamedTuple):
    url: str
    username: str
    image_url: str
    friends_since: datetime
    last_online: datetime


def iter_friends(username: str) -> Iterator[Friend]:
    localdir = LocalDir.from_username(username)
    friends_path = localdir.data_dir / "friends.json"
    if not friends_path.exists():
        logger.debug(f"{friends_path} doesn't exist, returning empty iterator")
        return
    for fblob in json.loads(friends_path.read_text()):
        yield Friend(
            url=fblob["url"],
            username=fblob["username"],
            image_url=fblob["image_url"],
            last_online=datetime.fromisoformat(fblob["last_online"]),
            friends_since=datetime.fromisoformat(fblob["friends_since"]),
        )
