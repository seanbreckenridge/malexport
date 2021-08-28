"""
Requests history (episode/chapter) for an anime/manga entry

This requires authentication (username/password) and selenium, since
this info isn't accessible from the API
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime

from .list_type import ListType
from .mal_list import MalList
from .mal_session import MalSession
from .driver import driver, driver_login, wait
from ..log import logger
from ..paths import LocalDir, _expand_path
from ..common import Json

from lxml import html as ht  # type: ignore[import]
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore[import]
from selenium.webdriver.common.by import By  # type: ignore[import]
from selenium.webdriver.support import expected_conditions as EC  # type: ignore[import]

HISTORY_URL = "https://myanimelist.net/ajaxtb.php?keepThis=true&detailed{list_type_letter}id={entry_id}&TB_iframe=true&height=420&width=390"

EPDETAILS_ID = "epdetails"


def history_url(list_type: ListType, entry_id: int) -> str:
    return HISTORY_URL.format(
        list_type_letter=list_type.value[0].casefold(), entry_id=entry_id
    )


# if we hit these many recently updated entries which
# are the same as the previous then stop requesting
TILL_SAME_LIMIT = int(os.environ.get("MALEXPORT_EPISODE_LIMIT", 15))

EPISODE_COL_REGEX = re.compile(
    "Ep (\d+), watched on (\d+)\/(\d+)\/(\d+) at (\d+):(\d+)"
)


def _extract_episode_data(episode_col_text: str) -> Tuple[int, int]:
    """
    Returns the episode number and the date as epoch time
    """
    m = EPISODE_COL_REGEX.match(episode_col_text)
    if not m:
        raise RuntimeError(
            f"Could not match episode/date of out text {episode_col_text}"
        )
    (episode_count, month, day, year, hour, minute) = m.groups()
    # uses local time, so just create a naive datetime and convert
    when = datetime(
        year=int(year),
        month=int(month),
        day=int(day),
        hour=int(hour),
        minute=int(minute),
        second=0,
    )
    return int(episode_count), int(when.timestamp())


def _extract_episode_history(episode_details: str) -> Json:
    x = ht.fromstring(episode_details)
    # parse the header
    header = x.xpath('.//div[contains(text(), "Episode Details")]')
    assert (
        len(header) == 1
    ), "Found multiple elements while searching for header, expected 1"
    # parse episodes
    episode_elements = x.xpath('.//div[contains(text(), "watched on")]')
    data = {"title": header[0].text.strip().replace("Episode Details", "").strip()}
    # fine even if there are no episode elements
    episodes = [_extract_episode_data(ep.text) for ep in episode_elements]
    # sort by date, most recent first
    episodes.sort(key=lambda tup: tup[1], reverse=True)
    data["episodes"] = episodes
    return data


class HistoryManager:
    """
    Uses the MalList module to request/save recently
    updated anime/manga entries

    If data doesn't exist at all for an entry, this requests
    info. Then, after that, this employs two strategies to update history data
        - request items that were recently updated (using &order=5
          on the [anime/manga]list) till we hit
          some limit of unchanged data
        - use the history page for the user to update
          items that have been watched in the last 3 weeks
    """

    def __init__(
        self,
        list_type: ListType,
        localdir: LocalDir,
        till_same_limit: int = TILL_SAME_LIMIT,
    ):
        """
        Assumes the MalSession has already
        been authenticated; is logged in
        """
        self.list_type = list_type
        self.localdir = localdir
        # if we request this many items and there is no difference
        # in any of the responses to the previously saved entries,
        # stop requesting
        self.till_same_limit = till_same_limit
        self.history_base_path: Path = _expand_path(
            self.localdir.data_dir / "history" / self.list_type.value
        )
        self.driver = None

    def authenticate(self) -> None:
        self.driver = driver()
        driver_login(localdir=self.localdir)

    def entry_path(self, entry_id: int) -> Path:
        return self.history_base_path / f"{entry_id}.json"

    def download_data(self, entry_id: int) -> Json:
        d = driver()
        url: str = history_url(self.list_type, entry_id)
        wait()
        logger.info(f"Requesting history data for {self.list_type.value} {entry_id}")
        d.get(url)
        # sanity check to make sure data is present on the page
        WebDriverWait(d, 10).until(
            EC.text_to_be_present_in_element(
                (
                    By.ID,
                    EPDETAILS_ID,
                ),
                "Episode Details",
            )
        )
        episode_details = d.find_element_by_id(EPDETAILS_ID)
        assert (
            episode_details is not None
        ), f"Couldn't find episode details div for {self.list_type.value} {entry_id} {url}"
        new_data = _extract_episode_history(episode_details.get_attribute("innerHTML"))
        return new_data

    def update_if_expired(self, entry_id: int) -> bool:
        """
        This returns a bool which signifies if data was changed
        If any data was changed/this is new, this returns True
        If data was the same as last time, it returns False
        """
        p = self.entry_path(entry_id)
        new_data = self.download_data(entry_id)
        # assume this is new data
        has_new_data = True
        if p.exists():
            old_data = json.loads(p.read_text())
            # if these arent the same, the data has changed,
            # we should keep searching for new episode information
            has_new_data = old_data != new_data
        new_data_json = json.dumps(new_data)
        p.write_text(new_data_json)
        return has_new_data

    def update_history(self) -> None:
        self.authenticate()
        # this saves even if there is no episode history, so we can compare
        m = MalList(self.list_type, localdir=self.localdir)
        mlist = m.load_list()
        for entry_data in mlist:
            mal_id = entry_data[f"{self.list_type.value}_id"]
            p = self.entry_path(mal_id)
            # If data doesn't exist for an item, request it
            # this doesn't impact the other strategies and will likely run when
            # you first add an item or when this is first run and is caching your entire list
            if not p.exists():
                self.update_if_expired(mal_id)
