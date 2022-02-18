"""
Requests MAL Lists (animelist/mangalist) for a user, using MAL API
"""

import json
from typing import List
from pathlib import Path

from ..list_type import ListType
from ..common import Json
from ..paths import LocalDir
from .mal_session import MalSession

BASE_URL = "https://api.myanimelist.net/v2/users/{username}/{list_type}list?limit=100&offset=0&nsfw=true&fields=id,title,main_picture,alternative_titles,start_date,end_date,synopsis,mean,rank,popularity,num_list_users,num_scoring_users,nsfw,created_at,updated_at,media_type,status,genres,my_list_status,num_episodes,start_season,broadcast,source,average_episode_duration,rating,pictures,background,related_anime,related_manga,recommendations,studios,statistics"


class APIList:
    """
    Requests/Updates the users data using the MAL API
    """

    def __init__(
        self, list_type: ListType, localdir: LocalDir, mal_session: MalSession
    ) -> None:
        self.localdir = localdir
        self.list_type = list_type
        self.mal_session = mal_session
        self.mal_session.authenticate()

    @property
    def list_path(self) -> Path:
        return self.localdir.data_dir / f"{self.list_type.value}list_api.json"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(list_type={self.list_type}, localdir={self.localdir})"

    __str__ = __repr__

    def update_list(self) -> None:
        """
        Paginate through all the data from the MAL API
        """
        first_url = BASE_URL.format(
            list_type=self.list_type.value,
            username=self.localdir.username,
        )
        data: List[Json] = []
        for resp in self.mal_session.paginate_all_data(first_url):
            for entry in resp:
                data.append(entry["node"])
        encoded_data = json.dumps(data)
        self.list_path.write_text(encoded_data)
