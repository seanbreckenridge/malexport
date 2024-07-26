from typing import Optional, Union, Literal

from ..paths import LocalDir
from ..list_type import ListType
from .mal_list import MalList
from .api_list import APIList
from .mal_session import MalSession
from .history import HistoryManager
from .forum import ForumManager
from .export_downloader import ExportDownloader
from .friends import FriendDownloader
from .messages import MessageDownloader
from .driver import Browser


class Account:
    """
    This encapsulates everything with regards to exporting data from MAL
    """

    def __init__(
        self,
        localdir: LocalDir,
        driver_type: Optional[Literal["chrome", "firefox"]] = None,
    ):
        self.localdir = localdir
        self.animelist = MalList(list_type=ListType.ANIME, localdir=self.localdir)
        self.mangalist = MalList(list_type=ListType.MANGA, localdir=self.localdir)
        self.animelist_api: Optional[APIList] = None
        self.mangalist_api: Optional[APIList] = None
        self.mal_session: Optional[MalSession] = None
        self.anime_episode_history: Optional[HistoryManager] = None
        self.manga_chapter_history: Optional[HistoryManager] = None
        self.forum_manager: Optional[ForumManager] = None
        self.export_downloader: Optional[ExportDownloader] = None
        self.friend_downloader: Optional[FriendDownloader] = None
        self.message_manager: Optional[MessageDownloader] = None
        self.driver_type: Literal["chrome", "firefox"] = driver_type or "chrome"
        self._shared_driver: Optional[Browser] = None

    @property
    def shared_driver(self) -> Union[Browser, None]:
        if self._shared_driver is None:
            return None
        return self._shared_driver

    @shared_driver.setter
    def shared_driver(self, driver: Union[Browser, None]) -> None:
        # dont overwrite if already set
        if driver is None or self._shared_driver is not None:
            return
        self._shared_driver = driver

    def mal_api_authenticate(self) -> MalSession:
        """
        This authenticates the mal_session using the API
        If never done before, runs the OAuth flow. Else loads
        the access token from the config file
        """
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
        """Alternate constructor to create an account from MAL username"""
        return Account(localdir=LocalDir.from_username(username))

    def update_lists(self, only: Optional[ListType] = None) -> None:
        """
        Uses the load.json endpoint to request anime/manga lists.
        Does not require any authentication
        """
        if only == ListType.ANIME or only is None:
            self.animelist.update_list()
        if only == ListType.MANGA or only is None:
            self.mangalist.update_list()

    def update_api_lists(self, only: Optional[ListType] = None) -> None:
        """
        Uses MALs API to request anime/manga lists
        Requires authentication, but includes more data than load.json
        """
        self.mal_api_authenticate()
        assert self.mal_session is not None
        if self.animelist_api is None:
            self.animelist_api = APIList(
                list_type=ListType.ANIME,
                localdir=self.localdir,
                mal_session=self.mal_session,
            )
        if self.mangalist_api is None:
            self.mangalist_api = APIList(
                list_type=ListType.MANGA,
                localdir=self.localdir,
                mal_session=self.mal_session,
            )
        if only == ListType.ANIME or only is None:
            self.animelist_api.update_list()
        if only == ListType.MANGA or only is None:
            self.mangalist_api.update_list()

    def update_exports(self) -> None:
        """
        Uses selenium to export/extract the XML files from MAL.
        Requires authentication (MAL Username/Password)
        """
        if self.export_downloader is None:
            self.export_downloader = ExportDownloader(
                self.localdir, driver_type=self.driver_type
            )
            breakpoint()
        # if driver is already set, use it
        if self.shared_driver is not None:
            self.export_downloader._driver = self.shared_driver
        self.export_downloader.export_lists()
        # run setter to save the authd driver if not already set
        self.shared_driver = self.export_downloader._driver

    def update_history(
        self,
        only: Optional[ListType] = None,
        count: Optional[int] = None,
        driver_type: Optional[str] = None,
        use_merged_file: bool = False,
    ) -> None:
        """
        Uses selenium to download episode/chapter history one entry at a time.

        This takes quite a while, and requires authentication (MAL Username/Password)
        If count is specified, only requests the first 'count' IDs found in your history
        """
        if self.anime_episode_history is None:
            self.anime_episode_history = HistoryManager(
                list_type=ListType.ANIME,
                localdir=self.localdir,
                driver_type=driver_type or self.driver_type,
                use_merged_file=use_merged_file,
            )
        if self.manga_chapter_history is None:
            self.manga_chapter_history = HistoryManager(
                list_type=ListType.MANGA,
                localdir=self.localdir,
                driver_type=driver_type or self.driver_type,
                use_merged_file=use_merged_file,
            )
        # if we have an authenticated driver already, use it
        if self.shared_driver is not None:
            self.anime_episode_history._driver = self.shared_driver
            self.manga_chapter_history._driver = self.shared_driver
        if only == ListType.ANIME or only is None:
            self.anime_episode_history.update_history(count=count)
        if only == ListType.MANGA or only is None:
            self.manga_chapter_history.update_history(count=count)
        # if driver was set here, save it
        self.shared_driver = self.anime_episode_history._driver
        self.shared_driver = self.manga_chapter_history._driver

    def update_messages(
        self, start_page: int = 1, thread_count: Optional[int] = None
    ) -> None:
        """
        Download/Update DMs for your account
        """
        if self.message_manager is None:
            self.message_manager = MessageDownloader(
                self.localdir,
                till_same_limit=thread_count,
            )
        self.message_manager.update_messages(start_page=start_page)

    def update_forum_posts(self) -> None:
        """
        Uses the MAL API to download any forum posts which you've created/commented on

        Requires you to go to https://myanimelist.net/apiconfig and create a Client. You can
        use any App Type other than Web, this doesn't use a Client Secret

        You can use http://localhost as the App Redirect URL
        """
        self.mal_api_authenticate()
        assert self.mal_session is not None
        if self.forum_manager is None:
            self.forum_manager = ForumManager(
                localdir=self.localdir, mal_session=self.mal_session
            )
        self.forum_manager.update_forum_index()
        self.forum_manager.update_changed_forum_posts()

    def update_friends(self) -> None:
        """
        Uses Jikan to download your friends from MAL
        """
        if self.friend_downloader is None:
            self.friend_downloader = FriendDownloader(localdir=self.localdir)
        self.friend_downloader.update_friend_index()
