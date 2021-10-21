"""
A helper module to combine data from the list,
export and history modules into data I find useful
"""

import os
from typing import Any, Dict, List, NamedTuple, Optional, TypeVar, Tuple, Union, Set
from datetime import date

from ..list_type import ListType
from ..log import logger
from ..paths import LocalDir
from .common import split_tags
from .history import History, HistoryEntry, iter_user_history
from .mal_list import (
    AnimeEntry,
    MangaEntry,
    parse_file as parse_user_history,
    IdInfo,
    Season,
)
from .xml import AnimeXML, MangaXML, parse_xml


T = TypeVar("T")

FILTER_TAGS = "MALEXPORT_COMBINED_FILTER_TAGS"


class AnimeData(NamedTuple):
    username: str
    # items from the xml
    id: int
    title: str
    media_type: str
    episodes: int
    watched_episodes: int
    start_date: Optional[date]
    finish_date: Optional[date]
    score: int
    status: str
    times_watched: int
    tags: str
    rewatching: bool
    rewatching_ep: int
    # history
    history: List[HistoryEntry]
    # items from the load.json
    airing_status: Optional[str]
    studios: List[IdInfo]
    licensors: List[IdInfo]
    genres: List[IdInfo]
    demographics: List[IdInfo]
    season: Optional[Season]
    url: Optional[str]
    image_path: Optional[str]
    air_start_date: Optional[date]
    air_end_date: Optional[date]
    rating: Optional[str]

    @property
    def tags_list(self) -> List[str]:
        return split_tags(self.tags)


class MangaData(NamedTuple):
    # items from the xml
    username: str
    id: int
    title: str
    volumes: int
    chapters: int
    read_volumes: int
    read_chapters: int
    start_date: Optional[date]
    finish_date: Optional[date]
    score: int
    status: str
    times_read: int
    tags: str
    rereading: bool
    # history
    history: List[HistoryEntry]
    # items from the load.json
    publishing_status: Optional[str]
    manga_magazines: List[IdInfo]
    genres: List[IdInfo]
    demographics: List[IdInfo]
    url: Optional[str]
    image_path: Optional[str]
    media_type: Optional[str]
    publish_start_date: Optional[date]
    publish_end_date: Optional[date]

    @property
    def tags_list(self) -> List[str]:
        return split_tags(self.tags)


# helper to extract optional data from json data
def _extract(json: Dict[str, Any], key: str, default: Optional[T]) -> Optional[T]:
    d = json.get(key)
    if d:
        return d  # type: ignore
    else:
        return default


def combine(username: str) -> Tuple[List[AnimeData], List[MangaData]]:
    acc = LocalDir.from_username(username)
    d = acc.data_dir

    # read history
    history = list(iter_user_history(username=username))
    anime_history: Dict[int, History] = {}
    manga_history: Dict[int, History] = {}
    for h in history:
        if h.list_type == "anime":
            # should never overwrite stuff by mistake
            assert h.mal_id not in anime_history
            anime_history[h.mal_id] = h
        else:
            assert h.mal_id not in manga_history
            manga_history[h.mal_id] = h

    # theres a possibility that the JSON exports don't
    # exist, because of private lists
    animelist_json_data: Dict[int, AnimeEntry] = {}
    mangalist_json_data: Dict[int, MangaEntry] = {}
    if (d / "animelist.json").exists():
        animelist_json_data = {
            el.id: el  # type: ignore[union-attr,misc]
            for el in parse_user_history(
                json_file=str(d / "animelist.json"), list_type=ListType.ANIME
            )
        }
    if (d / "mangalist.json").exists():
        mangalist_json_data = {
            el.id: el  # type: ignore[union-attr,misc]
            for el in parse_user_history(
                json_file=str(d / "mangalist.json"), list_type=ListType.MANGA
            )
        }

    # xml exports should always exist
    animelist_xml_data: Dict[int, AnimeXML] = {
        el.id: el  # type: ignore[union-attr,misc]
        for el in parse_xml(str(d / "animelist.xml")).entries
    }
    mangalist_xml_data: Dict[int, MangaXML] = {
        el.id: el  # type: ignore[union-attr,misc]
        for el in parse_xml(str(d / "mangalist.xml")).entries
    }

    anime_combined_data: Dict[int, AnimeData] = {}

    # combine anime data
    for mal_id, anime_xml in animelist_xml_data.items():

        anime_blob: Optional[AnimeEntry] = animelist_json_data.pop(mal_id, None)
        anime_dict: Dict[str, Any] = {}
        if anime_blob is not None:
            anime_dict = anime_blob._asdict()

        anime_hist: List[HistoryEntry] = []
        if mal_id in anime_history:
            anime_hist = anime_history[mal_id].entries
            anime_history.pop(mal_id)  # remove from anime history dict

        anime_combined_data[mal_id] = AnimeData(
            username=username,
            id=anime_xml.anime_id,
            title=anime_xml.title,
            media_type=anime_xml.media_type,
            episodes=anime_xml.episodes,
            watched_episodes=anime_xml.watched_episodes,
            start_date=anime_xml.start_date,
            finish_date=anime_xml.finish_date,
            score=anime_xml.score,
            status=anime_xml.status,
            times_watched=anime_xml.times_watched,
            tags=anime_xml.tags,
            rewatching=anime_xml.rewatching,
            rewatching_ep=anime_xml.rewatching_ep,
            history=anime_hist,
            airing_status=_extract(anime_dict, "airing_status", None),
            studios=anime_dict.get("studios") or [],
            licensors=anime_dict.get("licensors") or [],
            genres=anime_dict.get("genres") or [],
            demographics=anime_dict.get("demographics") or [],
            season=_extract(anime_dict, "season", None),
            url=_extract(anime_dict, "url", None),
            image_path=_extract(anime_dict, "image_path", None),
            air_start_date=_extract(anime_dict, "air_start_date", None),
            air_end_date=_extract(anime_dict, "air_end_date", None),
            rating=_extract(anime_dict, "rating", None),
        )

    manga_combined_data: Dict[int, MangaData] = {}
    for mal_id, manga_xml in mangalist_xml_data.items():

        manga_blob: Optional[MangaEntry] = mangalist_json_data.pop(mal_id, None)
        manga_dict: Dict[str, Any] = {}
        if manga_blob is not None:
            manga_dict = manga_blob._asdict()

        manga_hist: List[HistoryEntry] = []
        if mal_id in manga_history:
            manga_hist = manga_history[mal_id].entries
            manga_history.pop(mal_id)  # remove from manga history dict

        manga_combined_data[mal_id] = MangaData(
            username=username,
            id=manga_xml.manga_id,
            title=manga_xml.title,
            volumes=manga_xml.volumes,
            chapters=manga_xml.chapters,
            read_volumes=manga_xml.read_volumes,
            read_chapters=manga_xml.read_chapters,
            start_date=manga_xml.start_date,
            finish_date=manga_xml.finish_date,
            score=manga_xml.score,
            status=manga_xml.status,
            times_read=manga_xml.times_read,
            tags=manga_xml.tags,
            rereading=manga_xml.rereading,
            publishing_status=_extract(manga_dict, "publishing_status", None),
            manga_magazines=manga_dict.get("manga_magazines") or [],
            genres=manga_dict.get("genres") or [],
            demographics=manga_dict.get("demographics") or [],
            url=_extract(manga_dict, "url", None),
            image_path=_extract(manga_dict, "image_path", None),
            media_type=_extract(manga_dict, "media_type", None),
            publish_start_date=_extract(manga_dict, "publish_start_date", None),
            publish_end_date=_extract(manga_dict, "publish_end_date", None),
            history=manga_hist,
        )

    # while parsing, items were removed when they were merged into
    # the combined data. if anything still exists here, then warn
    if len(animelist_json_data) > 0:
        logger.warning(
            f"animelist_json_data entries left over: {len(animelist_json_data)}"
        )
    if len(mangalist_json_data) > 0:
        logger.warning(
            f"mangalist_json_data entries left over: {len(mangalist_json_data)}"
        )
    # shouldn't be warned for -- if you delete something off your list the
    # local history files still remain -- not sure if the should be deleted
    #
    # if len(anime_history) > 0:
    #    logger.warning(f"anime_history entries left over: {len(anime_history)}")
    # if len(manga_history) > 0:
    #    logger.warning(f"manga_history entries left over: {len(manga_history)}")

    anime_combined = list(anime_combined_data.values())
    manga_combined = list(manga_combined_data.values())

    # e.g. if you had MALEXPORT_COMBINED_FILTER_TAGS="no source,no raws"
    # anything which has those tags would be removed
    # from the results here
    if FILTER_TAGS in os.environ:
        filter_by_tags: List[str] = os.environ[FILTER_TAGS].split(",")

        def filter_func(e: Union[AnimeData, MangaData]) -> bool:
            tags: Set[str] = set(e.tags_list)
            for t in filter_by_tags:
                if t in tags:
                    return False
            return True

        anime_combined = list(filter(filter_func, anime_combined))
        manga_combined = list(filter(filter_func, manga_combined))

    return anime_combined, manga_combined
