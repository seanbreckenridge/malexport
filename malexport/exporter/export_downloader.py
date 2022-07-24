"""
Exports your list as XML from MAL using Selenium
"""

import os
import time
import shutil
import gzip
from typing import List, Optional

from selenium.webdriver.support.ui import WebDriverWait  # type: ignore[import]
from selenium.webdriver.common.by import By  # type: ignore[import]
from selenium.webdriver.support import expected_conditions as EC  # type: ignore[import]
from selenium.common.exceptions import TimeoutException, WebDriverException  # type: ignore[import]

from .driver import webdriver, driver_login, wait, TEMP_DOWNLOAD_DIR
from ..list_type import ListType
from ..paths import LocalDir
from ..log import logger

TRY_EXPORT_TIMES = int(os.environ.get("MALEXPORT_EXPORT_TRIES", 3))

EXPORT_PAGE = "https://myanimelist.net/panel.php?go=export"
EXPORT_BUTTON_CSS = "input[value='Export My List']"
DOWNLOAD_BUTTON = ".goodresult>a"


class ExportDownloader:
    """
    Downloads the XML exports for your account
    """

    def __init__(self, localdir: LocalDir) -> None:
        self.localdir = localdir
        self.animelist_path = self.localdir.data_dir / "animelist.xml"
        self.mangalist_path = self.localdir.data_dir / "mangalist.xml"
        self.driver = webdriver(browser_type="chrome")

    def authenticate(self) -> None:
        """Logs in to MAL using your MAL username/password"""
        # requires chrome because uses experimental flag to save downloads to custom dir
        driver_login(self.driver, self.localdir)

    def export_lists(self) -> None:
        """Exports the anime/manga lists, then extracts the gz files into the data dir"""
        self.authenticate()
        self.export_with_retry(ListType.ANIME)
        self.export_with_retry(ListType.MANGA)
        self.extract_gz_files()

    def export_with_retry(self, list_type: ListType, *, times: int = 0) -> None:
        """
        If exporting a list fails, resets the browser and tries again
        """
        try:
            self.export_list(list_type)
        except WebDriverException as e:
            times += 1
            logger.exception(
                f"Failed to export {list_type.value}, retrying ({times} of {TRY_EXPORT_TIMES})",
                exc_info=e,
            )
            if times > TRY_EXPORT_TIMES:
                return
            self.authenticate()
            # if user manually accepted/a file already present, skip retry
            if len(self._list_files(list_type=list_type)) > 0:
                logger.info("Found downloaded file, skipping retry...")
                return
            self.export_with_retry(list_type, times=times)  # recursive call

    def export_list(self, list_type: ListType) -> None:
        """
        Exports a particular list types' XML file, waits a while so that it can finish downloading
        The only difference between anime and manga is what is selected in the dialog
        """
        time.sleep(1)
        logger.info(f"Downloading {list_type.value} export")
        self.driver.get(EXPORT_PAGE)
        export_button_selector = tuple([By.CSS_SELECTOR, EXPORT_BUTTON_CSS])
        WebDriverWait(self.driver, 15).until(  # type: ignore[no-untyped-call]
            EC.visibility_of_element_located(export_button_selector)  # type: ignore[no-untyped-call]
        )
        if list_type == ListType.MANGA:
            self.driver.execute_script("""$("#dialog select.inputtext").val(2)""")  # type: ignore[no-untyped-call]
        self.driver.find_element(By.CSS_SELECTOR, EXPORT_BUTTON_CSS).click()  # type: ignore[no-untyped-call]
        time.sleep(0.25)
        WebDriverWait(self.driver, 5).until(EC.alert_is_present())  # type: ignore[no-untyped-call]
        alert = self.driver.switch_to.alert
        time.sleep(0.25)
        alert.accept()  # type: ignore[no-untyped-call]
        time.sleep(0.25)
        download_button_selector = tuple([By.CSS_SELECTOR, DOWNLOAD_BUTTON])
        try:
            # hmm -- this page seems to be there sometimes, but not others?
            WebDriverWait(self.driver, 10).until(  # type: ignore[no-untyped-call]
                EC.element_to_be_clickable(download_button_selector)  # type: ignore[no-untyped-call]
            )
            self.driver.find_element(By.CSS_SELECTOR, DOWNLOAD_BUTTON).click()
        except TimeoutException:
            pass
        logger.debug("Waiting for download...")
        wait()

    def _list_files(
        self, path: str = TEMP_DOWNLOAD_DIR, list_type: Optional[ListType] = None
    ) -> List[str]:
        """
        List files in the temporary download directory, warn if there
        are multiple files/partially downloaded files
        """
        files = os.listdir(path)
        animelist_gzs = [f for f in files if f.startswith("animelist_")]
        mangalist_gzs = [f for f in files if f.startswith("mangalist_")]
        archive_files = animelist_gzs + mangalist_gzs
        if list_type == ListType.ANIME:
            archive_files = animelist_gzs
        elif list_type == ListType.MANGA:
            archive_files = mangalist_gzs
        logger.debug(archive_files)
        return archive_files

    def extract_gz_files(self) -> None:
        """
        Wait till two files (the anime/manga gz files) exist in the temporary download
        directory, then extract them to the data directory
        """
        while (
            len(self._list_files(list_type=ListType.ANIME)) < 1
            and len(self._list_files(list_type=ListType.MANGA)) < 1
        ):
            logger.info(
                f"Waiting till anime/manga list export files exist, currently {os.listdir(TEMP_DOWNLOAD_DIR)}"
            )
            time.sleep(0.5)

        for (archive_name, target) in zip(
            [
                self._list_files(list_type=ListType.ANIME)[0],
                self._list_files(list_type=ListType.MANGA)[0],
            ],
            [self.animelist_path, self.mangalist_path],
        ):
            archive_path = os.path.join(TEMP_DOWNLOAD_DIR, archive_name)
            logger.info(f"Extracting {archive_path} to {target}")
            with gzip.open(archive_path, "rb") as gz_in:
                with target.open("wb") as f:
                    shutil.copyfileobj(gz_in, f)
