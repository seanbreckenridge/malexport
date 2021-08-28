"""
Uses MALs API to download forum posts
"""

import json
from typing import Iterator

from .mal_session import MalSession
from ..paths import LocalDir, _expand_path
from ..common import Json


# one is created by, one is commented on, doesn't really matter which is which
FORUM_BASES = [
    "https://api.myanimelist.net/v2/forum/topics?user_name={mal_username}&limit=100",
    "https://api.myanimelist.net/v2/forum/topics?topic_user_name={mal_username}&limit=100",
]

FORUM_POST = "https://api.myanimelist.net/v2/forum/topic/{forum_id}?limit=100"


class ForumManager:
    """
    Download any forum posts which you've created/commented on
    """

    def __init__(self, localdir: LocalDir, mal_session: MalSession) -> None:
        self.localdir = localdir
        self.mal_session = mal_session
        self.mal_session.authenticate()
        self.forum_index_path = (
            _expand_path(self.localdir.data_dir / "forum") / "index.json"
        )

    def download_forum_index(self) -> Iterator[Json]:
        """
        Download a 'forum index' (i.e., the IDs/modification time for any
        post you've created/commented on) by paginating through the data
        """
        for forum_base in FORUM_BASES:
            url = forum_base.format(mal_username=self.localdir.username)
            for data_response in self.mal_session.paginate_all_data(url):
                yield from data_response

    def load_forum_index(self) -> Json:
        """
        Assuming the forum index exists, load the JSON file
        """
        assert self.forum_index_path.exists(), "Forum index doesnt exist!"
        return json.loads(self.forum_index_path.read_text())

    def update_forum_index(self) -> None:
        """
        Download and save the forum index. This doesn't attempt to
        do anything complicated, it just re-downloads the entire thing
        """
        data = list(self.download_forum_index())
        data_json = json.dumps(data)
        self.forum_index_path.write_text(data_json)

    def update_changed_forum_posts(self) -> None:
        """
        Load the forum index, and call .update_if_changed on each forum post
        """
        for forum_post in self.load_forum_index():
            forum = ForumPost(
                localdir=self.localdir,
                mal_session=self.mal_session,
                forum_id=int(forum_post["id"]),
                last_post_created_at=str(forum_post["last_post_created_at"]),
            )
            forum.update_if_changed()


class ForumPost:
    """
    Manages/Downloads data for one forum post
    """

    def __init__(
        self,
        localdir: LocalDir,
        mal_session: MalSession,
        forum_id: int,
        last_post_created_at: str,
    ) -> None:
        self.localdir = localdir
        self.mal_session = mal_session
        self.forum_id = forum_id
        self.last_post_created_at = last_post_created_at
        self.forum_path = (
            _expand_path(self.localdir.data_dir / "forum") / f"{forum_id}.json"
        )

    def forum_post_has_changed(self) -> bool:
        """
        Determine whether or not the forum post has new data, by looking at the last_post_created_at
        (downloaded in the forum index)
        """
        if self.forum_path.exists():
            data = json.loads(self.forum_path.read_text())
            if "last_post_created_at" in data:
                # if these aren't the same, the data has changed, should update
                return str(data["last_post_created_at"]) != self.last_post_created_at
            else:
                # hmm? didnt save last_post_created_at for some reason?
                return True
        else:
            # doesnt exist, need to download
            return True

    def download_forum_post(self) -> Json:
        """
        For a particular forum post, paginate through all the posts
        """
        responses = list(
            self.mal_session.paginate_all_data(
                FORUM_POST.format(forum_id=self.forum_id)
            )
        )
        assert len(responses) > 0, f"No data returned for {self.forum_id}!"
        # need to attach all 'posts' to the response
        data = responses[0]
        for resp in responses[1:]:
            data["posts"].extend(resp["posts"])
        # save when this was last updated from the forum index
        data["last_post_created_at"] = self.last_post_created_at
        return data

    def update_if_changed(self) -> None:
        """
        If the forum post has to be updated, update it
        """
        if not self.forum_post_has_changed():
            return
        data_json = json.dumps(self.download_forum_post())
        self.forum_path.write_text(data_json)
