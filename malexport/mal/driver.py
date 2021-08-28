import os
import time
import tempfile
import random
import atexit
from pathlib import Path
from functools import lru_cache
from typing import Optional, Dict, Any

from selenium.webdriver import Chrome, ChromeOptions  # type: ignore[import]

from ..paths import LocalDir, _expand_path
from ..common import REQUEST_WAIT_TIME

HIDDEN_CHROMEDRIVER = bool(int(os.environ.get("MALEXPORT_CHROMEDRIVER_HIDDEN", 0)))
CHROME_LOCATION: Optional[str] = os.environ.get("MALEXPORT_CHROMEDRIVER_LOCATION")

# location for chromedriver to download files to
TEMP_DOWNLOAD_BASE = os.environ.get("MALEXPORT_TEMPDIR", tempfile.gettempdir())
TEMP_DOWNLOAD_DIR = _expand_path(
    Path(TEMP_DOWNLOAD_BASE) / "malexport_driver_downloads"
)

# global so user can edit before a driver is created if they want
CHROME_KWARGS: Dict[str, Any] = {}


@lru_cache(maxsize=1)
def driver() -> Chrome:
    options = ChromeOptions()
    if HIDDEN_CHROMEDRIVER:
        options.add_argument("headless")
        options.add_argument("window-size=1920x1080")
        options.add_argument("disable-gpu")
    if CHROME_LOCATION is not None:
        CHROME_KWARGS["executable_path"] = CHROME_LOCATION
    options.add_experimental_option(
        "prefs", {"download.default_directory": str(TEMP_DOWNLOAD_DIR)}
    )
    driver = Chrome("chromedriver", chrome_options=options, **CHROME_KWARGS)
    # quit when python exits to avoid hanging browsers
    atexit.register(lambda: driver.quit())
    return driver


IS_LOGGED_IN: bool = False


def driver_login(localdir: LocalDir) -> None:
    """
    Login using the users MAL username and password
    """
    global IS_LOGGED_IN
    d = driver()  # same instance as any other function which has called this
    if IS_LOGGED_IN:
        return
    creds = localdir.load_or_prompt_credentials()
    d.get("https://myanimelist.net/login.php")
    d.find_element_by_id("loginUserName").send_keys(creds["username"])
    time.sleep(2)
    d.find_element_by_id("login-password").send_keys(creds["password"])
    time.sleep(2)
    d.find_element_by_css_selector(
        ".inputButton.btn-form-submit[value='Login']"
    ).click()
    IS_LOGGED_IN = True


def wait() -> None:
    time.sleep(REQUEST_WAIT_TIME + random.random() * 4 - 1)
