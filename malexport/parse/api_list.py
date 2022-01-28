import json
from typing import NamedTuple, List, Optional, TypeVar, Iterator, Dict, Any
from datetime import date, datetime

from .common import parse_date_safe
from ..list_type import ListType
from ..common import Json
from ..paths import PathIsh, _expand_file
from .mal_list import IdInfo, Season

T = TypeVar("T")


class Entry(NamedTuple):
    entry_type: ListType
    id: int
    title: str
    main_picture: Dict[str, str]
    alternative_titles: Dict[str, Any]
    start_date: Optional[date]
    end_date: Optional[date]
    synopsis: str
    mean: Optional[float]
    rank: Optional[int]
    popularity: int
    num_list_users: int
    num_scoring_users: int
    nsfw: str
    created_at: datetime
    updated_at: datetime
    media_type: str
    status: str
    genres: List[IdInfo]
    list_status: Dict[str, Any]
    episode_count: Optional[int]
    season: Optional[Season]
    source: Optional[str]
    average_episode_duration: Optional[int]
    rating: Optional[str]
    studios: List[IdInfo]

    @classmethod
    def _parse(cls, el: Json, list_type: ListType) -> "Entry":
        return cls(
            entry_type=list_type,
            id=int(el["id"]),
            title=el["title"],
            main_picture=el.get("main_picture", {}),
            alternative_titles=el["alternative_titles"],
            start_date=parse_date_safe(el.get("start_date")),
            end_date=parse_date_safe(el.get("end_date")),
            synopsis=el["synopsis"],
            mean=el.get("mean"),
            rank=el.get("rank"),
            popularity=int(el["popularity"]),
            num_list_users=int(el["num_list_users"]),
            num_scoring_users=int(el["num_scoring_users"]),
            nsfw=el["nsfw"],
            created_at=datetime.fromisoformat(el["created_at"]),
            updated_at=datetime.fromisoformat(el["updated_at"]),
            media_type=el["media_type"],
            status=el["status"],
            genres=IdInfo._parse_id_list(el, "genres"),
            list_status=el["my_list_status"],
            episode_count=el.get("num_episodes"),
            season=Season._parse(el.get("start_season")),
            source=el.get("source"),
            average_episode_duration=el.get("average_episode_duration"),
            rating=el.get("rating"),
            studios=IdInfo._parse_id_list(el, "studios"),
        )


def iter_api_list(json_file: PathIsh, list_type: ListType) -> Iterator[Entry]:
    data = json.loads(_expand_file(json_file).read_text())
    for el in data:
        yield Entry._parse(el, list_type)
