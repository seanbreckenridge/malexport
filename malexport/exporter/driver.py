"""
Selenium singleton and functionality to login to MAL using a chromedriver
"""

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

# environment variables to overwrite the location of the chromedriver
# typically this just uses the 'chromedriver' binary,
# as long as thats on your $PATH
HIDDEN_CHROMEDRIVER = bool(int(os.environ.get("MALEXPORT_CHROMEDRIVER_HIDDEN", 0)))
CHROME_LOCATION: Optional[str] = os.environ.get("MALEXPORT_CHROMEDRIVER_LOCATION")

# location for chromedriver to download files to
TEMP_DOWNLOAD_BASE = os.environ.get("MALEXPORT_TEMPDIR", tempfile.gettempdir())

# unique location so we don't use old data
TEMP_DOWNLOAD_DIR = tempfile.mkdtemp(
    dir=_expand_path(Path(TEMP_DOWNLOAD_BASE) / "malexport_driver_downloads")
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


# If the user has been logged in using the MAL Username/Password using selenium
# This is set in driver_login
IS_LOGGED_IN: bool = False
LOGIN_PAGE = "https://myanimelist.net/login.php"

LOGIN_ID = "loginUserName"
PASSWORD_ID = "login-password"
LOGIN_BUTTON_CSS = ".inputButton.btn-form-submit[value='Login']"


def driver_login(localdir: LocalDir) -> None:
    """
    Login using the users MAL username and password
    """
    global IS_LOGGED_IN
    d = driver()  # same instance as any other function which has called this
    if IS_LOGGED_IN:
        return
    creds = localdir.load_or_prompt_credentials()
    time.sleep(1)
    d.get(LOGIN_PAGE)
    time.sleep(1)
    d.find_element_by_id(LOGIN_ID).send_keys(creds["username"])
    time.sleep(1)
    d.find_element_by_id(PASSWORD_ID).send_keys(creds["password"])
    time.sleep(1)
    # use script to login incase window is too small to be clickable
    d.execute_script(f"""document.querySelector("{LOGIN_BUTTON_CSS}").click()""")
    IS_LOGGED_IN = True


# wait a random amount of time to be nice to MAL servers
def wait() -> None:
    time.sleep(REQUEST_WAIT_TIME + random.random() * 4 - 1)