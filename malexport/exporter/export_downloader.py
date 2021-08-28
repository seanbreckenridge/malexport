import os
import time
import tempfile
import shutil
from typing import List

from selenium.webdriver.support.ui import WebDriverWait  # type: ignore[import]
from selenium.webdriver.common.by import By  # type: ignore[import]
from selenium.webdriver.support import expected_conditions as EC  # type: ignore[import]
from pyunpack import Archive  # type: ignore[import]

from .driver import driver, driver_login, wait, TEMP_DOWNLOAD_DIR
from .list_type import ListType
from ..paths import LocalDir
from ..log import logger

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

    def authenticate(self) -> None:
        driver_login(self.localdir)

    def export_lists(self) -> None:
        self.authenticate()
        self.export_list(ListType.ANIME)
        self.export_list(ListType.MANGA)
        self.extract_gz_files()

    def export_list(self, list_type: ListType) -> None:
        d = driver()
        time.sleep(1)
        logger.info(f"Downloading {list_type.value} export")
        d.get(EXPORT_PAGE)
        export_button_selector = tuple([By.CSS_SELECTOR, EXPORT_BUTTON_CSS])
        WebDriverWait(d, 10).until(
            EC.visibility_of_element_located(export_button_selector)
        )
        if list_type == ListType.MANGA:
            d.execute_script("""$("#dialog select.inputtext").val(2)""")
        d.find_element_by_css_selector(EXPORT_BUTTON_CSS).click()
        WebDriverWait(d, 10).until(EC.alert_is_present())
        alert = d.switch_to.alert
        alert.accept()
        download_button_selector = tuple([By.CSS_SELECTOR, DOWNLOAD_BUTTON])
        WebDriverWait(d, 10).until(EC.element_to_be_clickable(download_button_selector))
        d.find_element_by_css_selector(DOWNLOAD_BUTTON).click()
        wait()

    def _list_files(self, path: str = TEMP_DOWNLOAD_DIR) -> List[str]:
        files = os.listdir(path)
        animelist_gzs = [f for f in files if f.startswith("animelist_")]
        mangalist_gzs = [f for f in files if f.startswith("mangalist_")]
        for search_results in (animelist_gzs, mangalist_gzs):
            if len(search_results) != 1:
                logger.warning(f"Found more than 1 matching file {search_results}")
        return animelist_gzs + mangalist_gzs

    def extract_gz_files(self) -> None:
        while len(self._list_files()) != 2:
            logger.info(
                f"Waiting till 2 list files exist, currently {os.listdir(TEMP_DOWNLOAD_DIR)}"
            )
            time.sleep(0.5)

        with tempfile.TemporaryDirectory() as td:
            # extract each file into the temporary directory
            for archive_name in self._list_files():
                Archive(os.path.join(TEMP_DOWNLOAD_DIR, archive_name)).extractall(td)
            # list files in the temporary directory and move them
            for (extracted_xml_name, target) in zip(
                self._list_files(td), [self.animelist_path, self.mangalist_path]
            ):
                from_ = os.path.join(td, extracted_xml_name)
                to_ = str(target)
                logger.info(f"Moving extracted file {from_} to {to_}")
                shutil.move(from_, to_)
