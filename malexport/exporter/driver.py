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
from typing import Optional, Dict, Any, Union

from selenium import webdriver as sel
from selenium.webdriver.common.by import By

from selenium.webdriver.firefox.webdriver import WebDriver as Firefox  # type: ignore[import]


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


BrowserType = str

Browser = Union[sel.Chrome, Firefox]


@lru_cache(maxsize=12)
def webdriver(browser_type: str) -> Union[sel.Chrome, sel.Firefox]:
    bt = browser_type.casefold()
    assert bt in {"chrome", "firefox"}
    if bt == "chrome":
        options = sel.ChromeOptions()
        if HIDDEN_CHROMEDRIVER:
            options.add_argument("headless")  # type: ignore[no-untyped-call]
            options.add_argument("window-size=1920x1080")  # type: ignore[no-untyped-call]
            options.add_argument("disable-gpu")  # type: ignore[no-untyped-call]
        if CHROME_LOCATION is not None:
            CHROME_KWARGS["executable_path"] = CHROME_LOCATION
        else:
            CHROME_KWARGS["executable_path"] = "chromedriver"
        options.add_experimental_option(
            "prefs", {"download.default_directory": str(TEMP_DOWNLOAD_DIR)}
        )
        driver = sel.Chrome(chrome_options=options, **CHROME_KWARGS)
        # quit when python exits to avoid hanging browsers
        atexit.register(lambda: driver.quit())  # type: ignore[no-any-return]
        return driver
    else:
        # mostly added to get around this bug https://github.com/SeleniumHQ/selenium/issues/10799
        # which seems to happen on chromedriver 103 while fetching history
        # hmm -- why is mypy complaining untyped? LSP seems to take me to webdriver definition
        ff = Firefox(  # type: ignore[no-untyped-call]
            service_log_path=os.path.join(tempfile.gettempdir(), "geckodriver.log")
        )
        atexit.register(lambda: ff.quit())
        return ff


LOGIN_PAGE = "https://myanimelist.net/login.php"

LOGIN_ID = "loginUserName"
PASSWORD_ID = "login-password"
LOGIN_BUTTON_CSS = ".inputButton.btn-form-submit[value='Login']"


def driver_login(webdriver: Browser, localdir: LocalDir) -> None:
    """
    Login using the users MAL username and password
    """
    if hasattr(webdriver, "_malexport_logged_in"):
        return
    creds = localdir.load_or_prompt_credentials()
    time.sleep(1)
    webdriver.get(LOGIN_PAGE)
    time.sleep(1)
    webdriver.find_element(By.ID, LOGIN_ID).send_keys(creds["username"])
    time.sleep(1)
    webdriver.find_element(By.ID, PASSWORD_ID).send_keys(creds["password"])
    time.sleep(1)
    # use script to login incase window is too small to be clickable
    webdriver.execute_script(f"""document.querySelector("{LOGIN_BUTTON_CSS}").click()""")  # type: ignore[no-untyped-call]
    # set marker value on this instance to confirm user has logged in
    setattr(webdriver, "_malexport_logged_in", True)


# wait a random amount of time to be nice to MAL servers
def wait() -> None:
    time.sleep(REQUEST_WAIT_TIME + random.random() * 4 - 1)
