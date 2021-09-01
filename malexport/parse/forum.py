import os
import json
import glob
from datetime import datetime
from typing import NamedTuple, Iterator

from ..paths import LocalDir


class Post(NamedTuple):
    title: str
    comment_id: int
    username: str
    url: str
    created_at: datetime
    body: str


def iter_forum_posts(username: str) -> Iterator[Post]:
    localdir = LocalDir.from_username(username)
    mal_username = localdir.load_or_prompt_credentials()["username"]
    forum_dir = localdir.data_dir / "forum"
    for forum_path in glob.glob(os.path.join(forum_dir, "*.json")):
        yield from _extract_posts_by_user(forum_path, mal_username)


def _extract_posts_by_user(forum_path: str, username: str) -> Iterator[Post]:
    forum_id, _ = os.path.splitext(os.path.basename(forum_path))
    if not forum_id.isnumeric():  # not a valid post, probably index.json
        return
    with open(forum_path, "r") as f:
        data = json.load(f)
    for post in data["posts"]:
        if username.casefold() == post["created_by"]["name"].casefold():
            yield Post(
                title=data["title"],
                comment_id=post["id"],
                created_at=datetime.fromisoformat(post["created_at"]),
                username=username,
                url=f"""https://myanimelist.net/forum/?topicid={forum_id}&show=0#msg{post["id"]}""",
                body=post["body"],
            )
