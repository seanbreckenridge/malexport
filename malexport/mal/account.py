from typing import Optional

from ..paths import LocalDir
from .list_type import ListType
from .mal_list import MalList
from .mal_session import MalSession
from .episode_history import HistoryManager
from .forum import ForumManager


class Account:
    """
    This encapsulates all interaction with this MAL library
    to request/parse data from MAL
    """

    def __init__(self, localdir: LocalDir):
        self.localdir = localdir
        self.animelist = MalList(list_type=ListType.ANIME, localdir=self.localdir)
        self.mangalist = MalList(list_type=ListType.MANGA, localdir=self.localdir)
        self.mal_session: Optional[MalSession] = None

        self.forum_parser: Optional[ForumManager] = None

    def authenticate(self) -> MalSession:
        """
        This does the initial authentication with MyAnimeList using the API
        After a successful authentication, refresh should be called instead
        """
        if self.mal_session is not None:
            return self.mal_session
        client_info = self.localdir.load_or_prompt_mal_client_info()
        self.mal_session = MalSession(
            client_id=client_info["client_id"], localdir=self.localdir
        )
        self.mal_session.authenticate()
        return self.mal_session

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(localdir={self.localdir})"

    __str__ = __repr__

    @staticmethod
    def from_username(username: str) -> "Account":
        return Account(localdir=LocalDir.from_username(username=username))

    def update_lists(self) -> None:
        self.animelist.update_list()
        self.mangalist.update_list()

    def update_history(self) -> None:
        self.authenticate()

        self.anime_episode_history = HistoryManager(
            list_type=ListType.ANIME, localdir=self.localdir
        )
        self.manga_episode_history = HistoryManager(
            list_type=ListType.MANGA, localdir=self.localdir
        )
        self.anime_episode_history.update_history()
        self.manga_episode_history.update_history()

    def update_forum_posts(self) -> None:
        self.authenticate()
        assert self.mal_session is not None
        self.forum_manager = ForumManager(
            localdir=self.localdir, mal_session=self.mal_session
        )
        self.forum_manager.update_forum_index()
        self.forum_manager.update_changed_forum_posts()
