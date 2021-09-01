from typing import NamedTuple, Optional, Union, Any, Dict, List
from datetime import date


import lxml.etree as ET  # type: ignore[import]

from ..paths import _expand_file, PathIsh
from ..list_type import ListType
from .common import parse_date_safe, strtobool

# hmm.. cant figure out the types for this
XMLElement = Any

Info = Dict[str, Union[int, str]]


# TODO: some of these are None if the text is empty, not sure how to mark those
class AnimeXML(NamedTuple):
    anime_id: int
    title: str
    media_type: str
    episodes: int
    my_id: int
    watched_episodes: int
    start_date: Optional[date]
    finish_date: Optional[date]
    rated: str
    score: int
    storage: str
    storage_value: float
    status: str
    comments: str
    times_watched: int
    rewatch_value: str
    priority: str
    tags: str
    rewatching: bool
    rewatching_ep: int
    discuss: bool
    sns: str
    update_on_import: bool

    @property
    def id(self) -> int:
        return self.anime_id

    @classmethod
    def _parse(cls, anime_el: XMLElement) -> "AnimeXML":
        return cls(
            anime_id=int(anime_el.find("series_animedb_id").text),
            title=anime_el.find("series_title").text,
            media_type=anime_el.find("series_type").text,
            episodes=int(anime_el.find("series_episodes").text),
            my_id=int(anime_el.find("my_id").text),
            watched_episodes=int(anime_el.find("my_watched_episodes").text),
            start_date=parse_date_safe(anime_el.find("my_start_date").text),
            finish_date=parse_date_safe(anime_el.find("my_finish_date").text),
            rated=anime_el.find("my_rated").text,
            score=int(anime_el.find("my_score").text),
            storage=anime_el.find("my_storage").text,
            storage_value=float(anime_el.find("my_storage_value").text),
            status=anime_el.find("my_status").text,
            comments=anime_el.find("my_comments").text,
            times_watched=int(anime_el.find("my_times_watched").text),
            rewatch_value=anime_el.find("my_rewatch_value").text,
            priority=anime_el.find("my_priority").text,
            tags=anime_el.find("my_tags").text,
            rewatching=strtobool(anime_el.find("my_rewatching").text.lower()),
            rewatching_ep=int(anime_el.find("my_rewatching_ep").text),
            discuss=strtobool(anime_el.find("my_discuss").text.lower()),
            sns=anime_el.find("my_sns").text,
            update_on_import=strtobool(anime_el.find("update_on_import").text),
        )


class MangaXML(NamedTuple):
    manga_id: int
    title: str
    volumes: int
    chapters: int
    my_id: int
    read_volumes: int
    read_chapters: int
    start_date: Optional[date]
    finish_date: Optional[date]
    scanlation_group: str
    score: int
    storage: str
    retail_volumes: int
    status: str
    comments: str
    times_read: int
    tags: str
    priority: str
    reread_value: str
    rereading: bool
    discuss: bool
    sns: str
    update_on_import: bool

    @property
    def id(self) -> int:
        return self.manga_id

    @classmethod
    def _parse(cls, manga_el: XMLElement) -> "MangaXML":
        return cls(
            manga_id=int(manga_el.find("manga_mangadb_id").text),
            title=manga_el.find("manga_title").text,
            volumes=int(manga_el.find("manga_volumes").text),
            chapters=int(manga_el.find("manga_chapters").text),
            my_id=int(manga_el.find("my_id").text),
            read_volumes=int(manga_el.find("my_read_volumes").text),
            read_chapters=int(manga_el.find("my_read_chapters").text),
            start_date=parse_date_safe(manga_el.find("my_start_date").text),
            finish_date=parse_date_safe(manga_el.find("my_finish_date").text),
            scanlation_group=manga_el.find("my_scanalation_group").text,
            score=int(manga_el.find("my_score").text),
            storage=manga_el.find("my_storage").text,
            retail_volumes=int(manga_el.find("my_retail_volumes").text),
            status=manga_el.find("my_status").text,
            comments=manga_el.find("my_comments").text,
            times_read=int(manga_el.find("my_times_read").text),
            tags=manga_el.find("my_tags").text,
            priority=manga_el.find("my_priority").text,
            reread_value=manga_el.find("my_reread_value").text,
            rereading=strtobool(manga_el.find("my_rereading").text.lower()),
            discuss=strtobool(manga_el.find("my_discuss").text.lower()),
            sns=manga_el.find("my_sns").text,
            update_on_import=strtobool(manga_el.find("update_on_import").text),
        )


Entry = Union[AnimeXML, MangaXML]


class XMLExport(NamedTuple):
    list_type: str
    info: Info
    entries: List[Entry]

    @staticmethod
    def _parse_info(info: XMLElement) -> Info:
        data: Info = {}
        for el in list(info):
            if str(el.text).isdigit():
                data[el.tag] = int(el.text)
            else:
                data[el.tag] = str(el.text)
        return data

    @classmethod
    def parse(cls, xml_file: str) -> "XMLExport":
        tree = ET.parse(xml_file)
        root = tree.getroot()
        info = cls._parse_info(root.find("myinfo"))
        export_type = int(info["user_export_type"])
        list_type: ListType
        entries: List[Entry] = []
        if export_type == 1:
            list_type = ListType.ANIME
            entries = [AnimeXML._parse(el) for el in root.findall("anime")]
        else:
            list_type = ListType.MANGA
            entries = [MangaXML._parse(el) for el in root.findall("manga")]

        return cls(info=info, entries=entries, list_type=list_type.value.lower())


def parse_xml(xml_file: PathIsh) -> XMLExport:
    return XMLExport.parse(str(_expand_file(xml_file)))
