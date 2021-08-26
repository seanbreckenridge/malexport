from ..paths import LocalDir
from .list_type import MalList, ListType


class Account:
    def __init__(self, localdir: LocalDir):
        self.localdir = localdir
        self.animelist = MalList(list_type=ListType.ANIME, localdir=self.localdir)
        self.mangalist = MalList(list_type=ListType.MANGA, localdir=self.localdir)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(localdir={self.localdir})"

    __str__ = __repr__

    @staticmethod
    def from_username(username: str) -> "Account":
        return Account(localdir=LocalDir.from_username(username=username))

    @property
    def has_auth(self) -> bool:
        """
        Whether or not this account has credentials -- if it doesn't we can only request the load_json endpoint
        """
        return self.localdir.credential_path.exists()

    def update_lists(self) -> None:
        self.animelist.update_list()
        self.mangalist.update_list()

    def update_history(self) -> None:
        pass

    def update_forum_posts(self) -> None:
        pass
