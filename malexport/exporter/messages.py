"""
Requests messages (DMs)

This requires authentication (username/password) and selenium, since
this info isn't accessible from the API
"""

import os
import json
import time
from pathlib import Path
from typing import List, Optional, Dict, Iterator, Any, Tuple, Union

import dateparser
import more_itertools
from lxml import html as ht, etree  # type: ignore[import]
from selenium.webdriver.common.by import By  # type: ignore[import]

from .driver import webdriver, driver_login, wait
from ..log import logger
from ..paths import LocalDir, _expand_path
from ..common import Json, extract_query_value, serialize


# if we hit these many recently updated entries which
# are the same as the previous then stop requesting
TILL_SAME_LIMIT = int(os.environ.get("MALEXPORT_THREAD_LIMIT", 10))


def dateparse_to_epoch(datestr: str) -> Optional[int]:
    val = dateparser.parse(datestr.strip())
    if val:
        return int(val.timestamp())
    return None


class MessageDownloader:
    def __init__(
        self,
        localdir: LocalDir,
        driver_type: str = "chrome",
        till_same_limit: Optional[int] = None,
    ) -> None:
        self.localdir = localdir
        # if we request this many items and there is no difference
        # in any of the responses to the previously saved entries,
        # stop requesting
        self.till_same_limit: int = int(till_same_limit or TILL_SAME_LIMIT)
        self.message_base_path: Path = _expand_path(self.localdir.data_dir / "messages")
        self.msg_to_thread: Dict[int, int] = {}

        self.driver_type = driver_type
        self.driver = webdriver(self.driver_type)

    def authenticate(self) -> None:
        """Logs in to MAL using your MAL username/password"""
        driver_login(webdriver=self.driver, localdir=self.localdir)

    def entry_path(self, thread_id: int) -> Path:
        """Location of the JSON file for this thread"""
        return self.message_base_path / f"{thread_id}.json"

    def _fix_subject(self, subject: str) -> str:
        s = subject.strip()
        if s.startswith("re:"):
            s = s[len("re:") :]
        return s.strip()

    def _extract_details(self, html_details: Union[str, None]) -> Json:
        """
        Given the HTML div which contains the container for messages,
        parse it into JSON

        """
        assert html_details is not None, "html_details for thread is None"
        hx = ht.fromstring(html_details)
        table = hx.cssselect("table.pmessage-message-history")[0]
        subject = hx.cssselect(".dialog-text .mb4")[-1]
        data: Dict[str, Any] = {
            "messages": [],
            "subject": self._fix_subject(subject.text_content()),  # type: ignore[attr-defined]
        }
        for row in table.cssselect("tr"):
            date_td = row.cssselect("td.date")[0]
            username_td = row.cssselect("td.name")[0]
            content_td = row.cssselect("td.subject")[0]
            assert date_td is not None, "date_td is None"
            assert username_td is not None, "username_td is None"
            assert content_td is not None, "content_td is None"
            data["messages"].append(
                {
                    "username": username_td.text_content().strip(),  # type: ignore[attr-defined]
                    "dt": dateparse_to_epoch(date_td.text_content()),  # type: ignore[attr-defined]
                    "content": etree.tostring(content_td).decode("utf-8").strip(),
                }
            )
        logger.debug(data)
        return data

    def message_ids_for_page(self, page: int = 1, sent: bool = False) -> List[int]:
        """
        Goes to the message ids for a particular page of your messages
        """
        logger.info(
            f"Downloading page {page} of your {'sent ' if sent else ''}messages"
        )
        time.sleep(1)
        offset = (page - 1) * 20
        message_url = f"https://myanimelist.net/mymessages.php?go={'sent' if sent else ''}&show={offset}"
        self.driver.get(message_url)
        wait()
        # extract id=349234 from each message URL
        return [
            int(str(extract_query_value(a.get_attribute("href"), "id")))
            for a in self.driver.find_elements(By.CSS_SELECTOR, "a.subject-link")
        ]

    def iter_message_ids(self, start_page: int = 1) -> Iterator[Tuple[bool, int]]:
        """
        lazily retrieves new messages IDs for your user
        swaps between received messages and sent messages, so that
        this roughly grabs messages from the same time frame at the same time
        """
        page = int(start_page)
        while True:
            message_ids: List[int] = self.message_ids_for_page(page)
            sent_ids: List[int] = self.message_ids_for_page(page, sent=True)
            tagged_msg_id = [(False, mid) for mid in message_ids]
            tagged_sent_ids = [(True, mid) for mid in sent_ids]
            for sent, msg_id in more_itertools.interleave_longest(
                tagged_msg_id, tagged_sent_ids
            ):
                yield sent, msg_id
            if len(message_ids) == 0 and len(sent_ids) == 0:
                return
            page += 1

    def _resolve_message_to_thread_id(self, message_id: int, sent: bool) -> int:
        """
        goes to a message ID page and clicks the 'view message history' button
        returns the thread ID this corresponds to
        """
        time.sleep(1)
        url: str = (
            f"https://myanimelist.net/mymessages.php?go=read&id={message_id}{'&f=1' if sent else ''}"
        )
        logger.debug(f"Resolving message ID {message_id} to thread...")
        logger.debug(f"Navigating to '{url}'")
        self.driver.get(url)
        wait()
        thread_link = self.driver.find_element(
            By.PARTIAL_LINK_TEXT, "View Message History"
        )
        thread_url = thread_link.get_attribute("href")
        logger.debug(f"Thread URL is {thread_url}")
        assert thread_url is not None, "Could not find thread URL"
        self.driver.get(thread_url)
        wait()
        return int(str(extract_query_value(thread_url, "threadid")))

    def update_thread_data(self, thread_id: int) -> bool:
        """
        This returns a bool which signifies if data was changed
        If any data was changed/this is new, this returns True
        If data was the same as last time, it returns False
        """
        if thread_id in self.msg_to_thread.values():
            logger.debug(f"thread {thread_id} has already been requested, skipping...")
            return False
        p = self.entry_path(thread_id)
        # at this point, we're already on the thread page
        thread_content = self.driver.find_element(By.ID, "content")
        assert thread_content is not None, "Could not find thread div with ID 'content'"
        new_data = self._extract_details(thread_content.get_attribute("innerHTML"))
        # assume this is new data
        has_new_data = True
        if p.exists():
            old_data = json.loads(p.read_text())
            # if these aren't the same, the data has changed,
            # we should keep searching for more threads
            has_new_data = old_data != new_data
        new_data_json = serialize(new_data)
        p.write_text(new_data_json)
        return has_new_data

    def update_messages(
        self, start_page: int = 1, thread_count: Optional[int] = None
    ) -> None:
        self.authenticate()

        # if user supplied with CLI flag use that, else use envvar/default
        till_base = (
            int(self.till_same_limit) if thread_count is None else int(thread_count)
        )
        till = int(till_base)

        for sent, message_id in self.iter_message_ids(start_page=start_page):
            if till <= 0:
                break
            # resolve message ID to thread, which is what we download
            thread_id: int = self._resolve_message_to_thread_id(message_id, sent=sent)
            logger.info(f"msg {message_id} -> thread {thread_id}")
            # keep track of if this is a new thread, so we can decrement the 'till same' counter
            new_thread_id: bool = thread_id not in self.msg_to_thread.values()
            if self.update_thread_data(thread_id):
                logger.debug(
                    f"msg id {message_id}, thread {thread_id} had new data, resetting..."
                )
                till = int(till_base)
            else:
                if new_thread_id:
                    logger.debug(
                        f"msg id {message_id} thread {thread_id} matched old data, decrementing..."
                    )
                    till -= 1
            logger.info(f"requesting {till} more threads...")
            # save thread id so subsequent iterations dont repeat
            self.msg_to_thread[message_id] = thread_id
