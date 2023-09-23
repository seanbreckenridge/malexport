"""
Requests history (episode/chapter) for an anime/manga entry

This requires authentication (username/password) and selenium, since
this info isn't accessible from the API
"""

import os
import re
import json
import time
import atexit
from itertools import islice
from pathlib import Path
from typing import Tuple, List, Optional, Iterable, Dict, Any, Union, Set
from datetime import datetime

from lxml import html as ht  # type: ignore[import]
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore[import]
from selenium.webdriver.common.by import By  # type: ignore[import]
from selenium.webdriver.support import expected_conditions as EC  # type: ignore[import]

from ..list_type import ListType
from .mal_list import MalList
from .driver import webdriver, driver_login, wait, Browser
from .export_downloader import ExportDownloader
from ..log import logger
from ..paths import LocalDir, _expand_path
from ..common import Json, extract_query_value, serialize
from ..parse.xml import parse_xml


HISTORY_URL = "https://myanimelist.net/ajaxtb.php?keepThis=true&detailed{list_type_letter}id={entry_id}&TB_iframe=true&height=420&width=390"


def history_url(list_type: ListType, entry_id: int) -> str:
    """
    Creates the History URL for a particular type/ID
    """
    return HISTORY_URL.format(
        list_type_letter=list_type.value[0].casefold(), entry_id=entry_id
    )


# if we hit these many recently updated entries which
# are the same as the previous then stop requesting
TILL_SAME_LIMIT = int(os.environ.get("MALEXPORT_EPISODE_LIMIT", 5))

EPISODE_COL_REGEX = re.compile(
    r"Ep (\d+), watched on (\d+)\/(\d+)\/(\d+) at (\d+):(\d+)"
)

CHAPTER_COL_REGEX = re.compile(
    r"Chapter (\d+), read on (\d+)\/(\d+)\/(\d+) at (\d+):(\d+)"
)


def _extract_column_data(
    col_html: Union[str, None, Any], list_type: ListType
) -> Tuple[int, int]:
    """
    Returns the episode/chapter number and the date as epoch time
    """
    assert isinstance(col_html, str), f"Expected string, got {type(col_html)}"
    chosen_regex = (
        EPISODE_COL_REGEX if list_type == ListType.ANIME else CHAPTER_COL_REGEX
    )
    m = chosen_regex.match(col_html)
    if not m:
        raise RuntimeError(
            f"Could not match episode/chapter/date of out text {col_html}"
        )
    (count, month, day, year, hour, minute) = m.groups()
    # uses local time, so just create a naive datetime and convert
    when = datetime(
        year=int(year),
        month=int(month),
        day=int(day),
        hour=int(hour),
        minute=int(minute),
        second=0,
    )
    return int(count), int(when.timestamp())


class HistoryManager:
    """
    Uses multiple strategies to update history data (episode/chapter watch dates)
    """

    def __init__(
        self,
        list_type: ListType,
        localdir: LocalDir,
        driver_type: str = "chrome",
        till_same_limit: int = TILL_SAME_LIMIT,
        use_merged_file: bool = False,
    ) -> None:
        self.list_type = list_type
        self.localdir = localdir
        # if we request this many items and there is no difference
        # in any of the responses to the previously saved entries,
        # stop requesting
        self.till_same_limit = till_same_limit
        self.use_merged_file = use_merged_file
        self.merged_data: Optional[Dict[str, Any]] = None

        self.history_path: Path
        if self.use_merged_file:
            logger.debug(f"Using merged file for {self.list_type.value}")
            self.history_path = _expand_path(
                self.localdir.data_dir / f"{self.list_type.value}_history.json",
                is_dir=False,
            )
            if self.history_path.exists():
                self.merged_data = json.loads(self.history_path.read_text())
            else:
                self.merged_data = {}
            _register_atexit(self.history_path, self)
        else:
            logger.debug("Using individual history files...")
            self.history_path = _expand_path(
                self.localdir.data_dir / "history" / self.list_type.value
            )

        # a list of IDs already requested by this instance, to avoid
        # duplicates across strategies
        self.already_requested: Set[int] = set()

        self.container_id = (
            "chapdetails" if self.list_type == ListType.MANGA else "epdetails"
        )
        self.idprefix = "chaprow" if self.list_type == ListType.MANGA else "eprow"
        self.driver_type = driver_type
        self._driver: Optional[Browser] = None

    @property
    def driver(self) -> Browser:
        if self._driver is None:
            self._driver = webdriver(self.driver_type)
        return self._driver

    def authenticate(self) -> None:
        """Logs in to MAL using your MAL username/password"""
        driver_login(webdriver=self.driver, localdir=self.localdir)

    def entry_path(self, entry_id: int) -> Path:
        """Location of the JSON file for this type/ID"""
        if self.use_merged_file:
            return self.history_path
        else:
            return self.history_path / f"{entry_id}.json"

    def has_data(self, entry_id: int) -> bool:
        if self.use_merged_file:
            assert self.merged_data is not None
            return str(entry_id) in self.merged_data
        else:
            return self.entry_path(entry_id).exists()

    def save_data(self, entry_id: int, new_data: Json) -> bool:
        """
        return True if data changed, False otherwise
        """
        if self.use_merged_file:
            logger.debug(f"Saving {entry_id} data to merged JSON...")
            assert self.merged_data is not None
            key = str(entry_id)
            has_new_data = True
            if key in self.merged_data:
                old_data = self.merged_data[str(entry_id)]
                has_new_data = old_data != new_data
            self.merged_data[str(entry_id)] = new_data
            return has_new_data
        else:
            has_new_data = True
            p = self.entry_path(entry_id)
            logger.debug(f"Saving {entry_id} to {p}...")
            if p.exists():
                old_data = json.loads(p.read_text())
                # if these aren't the same, the data has changed,
                # we should keep searching for new episode information
                has_new_data = old_data != new_data
            new_data_json = serialize(new_data)
            # this saves even if there is no episode history, so we can compare when updating
            p.write_text(new_data_json)
            return has_new_data

    def _save_merged_file(self) -> None:
        data = serialize(self.merged_data)
        assert self.merged_data is not None
        total_eps = sum(len(v.get("episodes", [])) for v in self.merged_data.values())
        logger.debug(
            f"Writing merged JSON file: {self.history_path}, total {'episode' if self.list_type == ListType.ANIME else 'chapter'} count: {total_eps}"
        )
        self.history_path.write_text(data)

    def _extract_details(self, html_details: str) -> Json:
        """
        Given the HTML div which contains the episode details from the page,
        extract the header (name of the entry) when each episode was watched

        This uses a list instead of an episode -> datetime mapping
        since its possible for you to mark episodes multiple times, e.g. if you're
        rewatching entries
        """
        x = ht.fromstring(html_details)
        # parse the header
        header = x.xpath('.//div[contains(text(), "Details")]')
        assert isinstance(header, list)
        assert (
            len(header) == 1
        ), f"Found {len(header)} elements while searching for header, expected 1"
        # split tokens and remove last two (Chapter Details or Episode Details)
        assert isinstance(header[0].text, str)  # type: ignore[union-attr]
        title = header[0].text.strip()  # type: ignore[union-attr]
        title = " ".join(title.split(" ")[:-2]).strip()
        data: Dict[str, Any] = {"title": title}
        # parse episodes/chapters; fine even if there are no episode/chapter elements
        episode_elements = x.xpath(f'.//div[starts-with(@id, "{self.idprefix}")]')
        assert isinstance(episode_elements, list)
        episodes = [
            list(_extract_column_data(ep.text, self.list_type))  # type: ignore[union-attr]
            for ep in episode_elements
        ]
        # sort by date, most recent first
        episodes.sort(key=lambda d: d[1], reverse=True)
        data["episodes"] = episodes
        logger.debug(data)
        return data

    def download_recent_user_history(self) -> List[int]:
        """
        Goes to the history page in the authenticated browser
        and grabs IDs for any items which were recently watched/read
        """
        logger.info(f"Downloading recent user {self.list_type.value} history")
        time.sleep(1)
        mal_username = self.localdir.load_or_prompt_credentials()["username"]
        history_url = (
            f"https://myanimelist.net/history/{mal_username}/{self.list_type.value}"
        )
        self.driver.get(history_url)
        wait()
        content_div = self.driver.find_element(By.CSS_SELECTOR, "div#content")
        content_div_html = content_div.get_attribute("innerHTML")
        assert isinstance(content_div_html, str)
        x = ht.fromstring(content_div_html)
        found_ids: List[int] = []
        hist_items = x.xpath(
            f'.//a[starts-with(@href, "/{self.list_type.value}.php?id=")]'
        )
        assert isinstance(hist_items, list)
        for el in hist_items:
            assert isinstance(el, ht.HtmlElement)
            new_id = int(extract_query_value(el.attrib["href"], "id"))
            if new_id not in found_ids:
                found_ids.append(new_id)
        return found_ids

    def download_history_for_entry(self, entry_id: int) -> Json:
        """
        Download the information for a particular type/ID
        """
        time.sleep(1)
        url: str = history_url(self.list_type, entry_id)
        logger.info(f"Requesting history data for {self.list_type.value} {entry_id}")
        self.driver.get(url)
        wait()
        # sanity check to make sure data is present on the page
        WebDriverWait(self.driver, 10).until(  # type: ignore[no-untyped-call]
            EC.text_to_be_present_in_element(  # type: ignore[no-untyped-call]
                (
                    By.ID,
                    self.container_id,
                ),
                "Details",
            )
        )
        details = self.driver.find_element(By.ID, self.container_id)
        assert (
            details is not None
        ), f"Couldn't find details (header) div for {self.list_type.value} {entry_id} {url}"
        innerHtml = details.get_attribute("innerHTML")
        assert innerHtml is not None, "Couldn't get innerHTML for details div"
        new_data = self._extract_details(innerHtml)
        return new_data

    def update_entry_data(self, entry_id: int) -> bool:
        """
        This returns a bool which signifies if data was changed
        If any data was changed/this is new, this returns True
        If data was the same as last time, it returns False
        """
        if entry_id in self.already_requested:
            logger.debug(f"{entry_id} has already been requested, skipping...")
            return False
        new_data = self.download_history_for_entry(entry_id)
        self.already_requested.add(entry_id)
        # if using merged file, save every 10 requests
        if (
            self.use_merged_file is True
            and len(self.already_requested) > 0
            and len(self.already_requested) % 10 == 0
        ):
            self._save_merged_file()
        return self.save_data(entry_id, new_data)

    def update_history(self, count: Optional[int] = None) -> None:
        """
        If data doesn't exist at all for an entry, this requests
        info. Then, after that, this employs two strategies to update history data
            - request items that were recently updated (using &order=5
              on the [anime/manga]list) till we hit
              some limit of unchanged data
            - use the history page (using Jikan) for the user to update
              items that have been watched in the last 3 weeks
        If count is specified, only requests the first 'count' entries
        """
        self.authenticate()

        m = MalList(self.list_type, localdir=self.localdir)
        exp = ExportDownloader(localdir=self.localdir)
        export_file = (
            exp.animelist_path
            if self.list_type == ListType.ANIME
            else exp.mangalist_path
        )
        mal_id: int
        logger.info("Requesting any items which don't exist in history...")
        updated = False
        if m.list_path.exists():
            updated = True
            mlist = m.load_list()
            for entry_data in mlist:
                mal_id = entry_data[f"{self.list_type.value}_id"]
                # If data doesn't exist for an item, request it
                # this doesn't impact the other strategies and will likely run when
                # you first add an item or when this is first run and is caching your entire list
                if not self.has_data(mal_id):
                    self.update_entry_data(mal_id)

            logger.info("Requesting items till we hit some amount of unchanged data...")
            # request some amount till we hit unchanged data
            till = int(self.till_same_limit)
            for entry_data in mlist:
                if till <= 0:
                    break
                logger.info(f"Requesting {till} more entries...")
                mal_id = entry_data[f"{self.list_type.value}_id"]
                if self.update_entry_data(mal_id):
                    logger.debug(
                        f"{self.list_type.value} {mal_id} had new data, resetting..."
                    )
                    till = int(self.till_same_limit)
                else:
                    logger.debug(
                        f"{self.list_type.value} {mal_id} matched old data, decrementing..."
                    )
                    till -= 1

        if export_file.exists():
            updated = True
            # use the XML file if that exists
            for el in parse_xml(str(export_file)).entries:
                if not self.has_data(el.id):
                    self.update_entry_data(el.id)
        if not updated:
            raise RuntimeError(
                f"Neither {m.list_path} (lists) or {export_file} (export) exist, need one to update history"
            )

        recent_history: Iterable[int] = iter(self.download_recent_user_history())
        if count is not None:
            logger.info(f"Requesting {count} first items from user history")
            recent_history = islice(recent_history, count)
        else:
            logger.info("Requesting all items from user history")
        # use selenium to go to users' history and update things watched within the last few weeks
        for mal_id in recent_history:
            self.update_entry_data(mal_id)
        self._save_merged_file()


REGISTERED: Set[Path] = set()


def _register_atexit(path: Path, manager: HistoryManager) -> None:
    if path in REGISTERED:
        logger.debug(f"Already registered {path} to write when exiting")
        return
    REGISTERED.add(path)
    logger.debug(f"Registering {path} for atexit")
    atexit.register(lambda: manager._save_merged_file())
