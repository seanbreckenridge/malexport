import json
from typing import NamedTuple, Union, List, Optional, TypeVar, Iterator
from datetime import date

from .common import strtobool, parse_short_date
from ..list_type import ListType
from ..common import Json
from ..paths import PathIsh, _expand_file

T = TypeVar("T")


def filter_none(lst: List[Optional[T]]) -> List[T]:
    lst_new: List[T] = []
    for x in lst:
        if x is not None:
            lst_new.append(x)
    return lst_new


class IdInfo(NamedTuple):
    id: int
    name: str

    @staticmethod
    def _parse(data: Optional[Json]) -> Optional["IdInfo"]:
        if isinstance(data, dict) and "id" in data and "name" in data:
            return IdInfo(id=data["id"], name=data["name"])
        else:
            return None

    @classmethod
    def _parse_id_list(cls, el: Json, key: str) -> List["IdInfo"]:
        return filter_none([cls._parse(e) for e in list(el.get(key) or [])])


class Season(NamedTuple):
    year: int
    season: str

    @staticmethod
    def _parse(season_data: Optional[Json]) -> Optional["Season"]:
        if (
            isinstance(season_data, dict)
            and "year" in season_data
            and "season" in season_data
        ):
            return Season(year=season_data["year"], season=season_data["season"])
        else:
            return None


ANIME_STATUS_MAP = {
    1: "Currently Watching",
    2: "Completed",
    3: "On Hold",
    4: "Dropped",
    6: "Plan to Watch",
}

MANGA_STATUS_MAP = {
    1: "Currently Reading",
    2: "Completed",
    3: "On Hold",
    4: "Dropped",
    6: "Plan to Read",
}

ANIME_AIRING_STATUS_MAP = {
    1: "Currently Airing",
    2: "Finished Airing",
    3: "Not Yet Aired",
}

MANGA_PUBLISHING_STATUS_MAP = {
    1: "Currently Publishing",
    2: "Finished Publishing",
    3: "Not Yet Published",
    4: "On Hiatus",
    5: "Discontinued",
}


class AnimeEntry(NamedTuple):
    status: str
    score: int
    tags: str
    rewatching: bool
    watched_episodes: int
    title: str
    episodes: int
    airing_status: str
    id: int
    studios: List[IdInfo]
    licensors: List[IdInfo]
    genres: List[IdInfo]
    demographics: List[IdInfo]
    season: Optional[Season]
    has_episode_video: bool
    has_promotion_video: bool
    has_video: bool
    video_url: str
    url: str
    image_path: str
    is_added_to_list: bool
    media_type: str
    rating: str
    start_date: Optional[date]
    finish_date: Optional[date]
    air_start_date: Optional[date]
    air_end_date: Optional[date]
    days: Optional[int]
    storage: str
    priority: str

    @classmethod
    def _parse(cls, el: Json) -> "AnimeEntry":
        return cls(
            status=ANIME_STATUS_MAP[el["status"]],
            score=el["score"],
            tags=el["tags"],
            rewatching=strtobool(el["is_rewatching"]),
            watched_episodes=el["num_watched_episodes"],
            title=el["anime_title"],
            episodes=el["anime_num_episodes"],
            airing_status=ANIME_AIRING_STATUS_MAP[el["anime_airing_status"]],
            id=el["anime_id"],
            studios=IdInfo._parse_id_list(el, "anime_studios"),
            licensors=IdInfo._parse_id_list(el, "anime_licensors"),
            genres=IdInfo._parse_id_list(el, "genres"),
            demographics=IdInfo._parse_id_list(el, "demographics"),
            season=Season._parse(el["anime_season"]),
            has_video=el["has_video"],
            video_url=el["video_url"],
            has_episode_video=el["has_episode_video"],
            has_promotion_video=el["has_promotion_video"],
            url=el["anime_url"],
            image_path=el["anime_image_path"],
            is_added_to_list=el["is_added_to_list"],
            media_type=el["anime_media_type_string"],
            rating=el["anime_mpaa_rating_string"],
            start_date=parse_short_date(el["start_date_string"] or ""),
            finish_date=parse_short_date(el["finish_date_string"] or ""),
            air_start_date=parse_short_date(el["anime_start_date_string"]),
            air_end_date=parse_short_date(el["anime_end_date_string"]),
            days=el["days_string"],
            storage=el["storage_string"],
            priority=el["priority_string"],
        )


class MangaEntry(NamedTuple):
    status: str
    score: int
    tags: str
    rereading: bool
    read_chapters: int
    read_volumes: int
    title: str
    chapters: int
    volumes: int
    publishing_status: str
    id: int
    genres: List[IdInfo]
    demographics: List[IdInfo]
    manga_magazines: List[IdInfo]
    url: str
    image_path: str
    is_added_to_list: bool
    media_type: str
    start_date: Optional[date]
    finish_date: Optional[date]
    publish_start_date: Optional[date]
    publish_end_date: Optional[date]
    days: Optional[int]
    retail: str
    priority: str

    @classmethod
    def _parse(cls, el: Json) -> "MangaEntry":
        return cls(
            status=MANGA_STATUS_MAP[el["status"]],
            score=el["score"],
            tags=el["tags"],
            rereading=strtobool(el["is_rereading"]),
            read_chapters=el["num_read_chapters"],
            read_volumes=el["num_read_volumes"],
            title=el["manga_title"],
            chapters=el["manga_num_chapters"],
            volumes=el["manga_num_volumes"],
            publishing_status=MANGA_PUBLISHING_STATUS_MAP[
                el["manga_publishing_status"]
            ],
            id=el["manga_id"],
            manga_magazines=IdInfo._parse_id_list(el, "manga_magazines"),
            genres=IdInfo._parse_id_list(el, "genres"),
            demographics=IdInfo._parse_id_list(el, "demographics"),
            url=el["manga_url"],
            image_path=el["manga_image_path"],
            is_added_to_list=el["is_added_to_list"],
            media_type=el["manga_media_type_string"],
            start_date=parse_short_date(el["start_date_string"] or ""),
            finish_date=parse_short_date(el["finish_date_string"] or ""),
            publish_start_date=parse_short_date(el["manga_start_date_string"]),
            publish_end_date=parse_short_date(el["manga_end_date_string"]),
            days=el["days_string"],
            retail=el["retail_string"],
            priority=el["priority_string"],
        )


Entry = Union[AnimeEntry, MangaEntry]


def iter_user_list(json_file: str, list_type: ListType) -> Iterator[Entry]:
    with open(json_file) as f:
        data = json.load(f)
    if list_type == ListType.ANIME:
        for el in data:
            yield AnimeEntry._parse(el)
    else:
        for el in data:
            yield MangaEntry._parse(el)


def parse_file(json_file: PathIsh, list_type: ListType) -> Iterator[Entry]:
    yield from iter_user_list(str(_expand_file(json_file)), list_type)
