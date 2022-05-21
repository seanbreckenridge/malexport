"""
Maintains an authenticated session with MAL
"""

import os
import re
import json
import base64
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs
from typing import Dict, Any, cast, Iterator

import requests
import click

from ..common import safe_request
from ..log import logger
from ..paths import LocalDir


def _create_pkce_verifier() -> str:
    """
    Creates a random PKCE compliant string. MAL uses a simple method,
    we dont need to create a challenge string
    """
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
    return code_verifier


MALEXPORT_REDIRECT_URI = os.environ.get("MALEXPORT_REDIRECT_URI", "http://localhost")
MALEXPORT_STATE = "malexport"

LOGIN_BASE = "https://myanimelist.net/v1"


class MalSession:
    """Class to handle requests to MAL"""

    def __init__(self, client_id: str, localdir: LocalDir):
        """
        Creates a new instance of an authenticated MalSession
        """
        self.client_id = client_id
        self.localdir = localdir
        self.session = requests.Session()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(username={self.localdir.username}, client_id={self.client_id})"

    __str__ = __repr__

    def authenticate(self) -> None:
        """
        Update the request Session to include the Bearer token as a header.
        If that doesn't exist, it starts the token auth flow to create one
        """
        refresh_info = self.refresh_info()
        access_token = refresh_info["access_token"]
        logger.debug(f"Access Token: {access_token}")
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    def refresh_info(self) -> Dict[str, str]:
        """
        Load or run the OAuth flow to get an access_token for the MAL API
        """
        if self.localdir.refresh_info.exists():
            try:
                return cast(
                    Dict[str, str], json.loads(self.localdir.refresh_info.read_text())
                )
            except json.JSONDecodeError:
                pass
        return self.oauth_flow()

    def oauth_flow(self) -> Dict[str, str]:
        """
        Run the OAuth flow for MALs API
        """
        logger.info("Logging in to MAL...")

        # get a 'code', may need to open a URL to let the user login in the browser
        # and approve their application
        code_verifier = _create_pkce_verifier()
        url = (
            LOGIN_BASE
            + "/oauth2/authorize?"
            + urlencode(
                {
                    "response_type": "code",
                    "client_id": self.client_id,
                    "state": MALEXPORT_STATE,
                    "redirect_uri": MALEXPORT_REDIRECT_URI,
                    "code_challenge": code_verifier,
                    "code_challenge_method": "plain",
                }
            )
        )
        webbrowser.open_new_tab(url)
        click.echo(f"If the URL didn't open automatically, go to\n\n{url}\n")
        redirected_uri = click.prompt(
            "Approve the application, and paste the whole URL it redirects you back here"
        )
        code: str = parse_qs(urlparse(redirected_uri).query)["code"][0]
        logger.debug(f"parsed code: {code}")

        # make the request with HTTP Basic Authentication
        refresh_req = self.session.post(
            LOGIN_BASE + "/oauth2/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": self.client_id,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": MALEXPORT_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
            auth=(self.client_id, ""),  # leave client secret empty
        )
        refresh_info: Dict[str, str] = refresh_req.json()
        logger.debug(refresh_info)
        if refresh_req.status_code != 200:
            raise RuntimeError(f"Error: {refresh_info}")
        logger.info(f"Saving refresh information to {self.localdir.refresh_info}")
        self.localdir.refresh_info.write_text(refresh_req.text)
        return refresh_info

    def refresh_token(self) -> None:
        old_refresh_info = json.loads(self.localdir.refresh_info.read_text())
        refresh_req = self.session.post(
            LOGIN_BASE + "/oauth2/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "refresh_token": old_refresh_info["refresh_token"],
                "grant_type": "refresh_token",
            },
            auth=(self.client_id, ""),  # leave client secret empty
        )
        if refresh_req.status_code != 200:
            raise RuntimeError(f"Error: {refresh_req.json()}")
        refresh_req.raise_for_status()
        self.localdir.refresh_info.write_text(refresh_req.text)
        logger.debug(refresh_req.json())
        self.authenticate()  # re-authenticate to attach the new access_token

    def refresh_token_if_expired(self, req: requests.Response) -> None:
        """
        Passed to safe_json_request as the error handler, refreshes the token
        if its expired. Currently that lasts for a month
        """
        if req.status_code == 401:
            logger.info("Refreshing token...")
            self.refresh_token()

    def paginate_all_data(self, url: str) -> Iterator[Any]:
        """
        Generic function that works with any MAL url which supports pagination
        Supply limit elsewhere since it may vary per request
        """
        while True:
            resp = self.safe_json_request(url)
            yield resp["data"]
            if "paging" in resp and "next" in resp["paging"]:
                url = resp["paging"]["next"]
            else:
                break

    def safe_request(self, url: str, **kwargs: Any) -> requests.Response:
        """
        A wrapper for the safe_request function -- makes an authenticated request
        to the MAL API
        """
        r: requests.Response = safe_request(
            url,
            session=self.session,
            on_error=self.refresh_token_if_expired,
            wait_time=1,
            **kwargs,
        )
        return r

    def safe_json_request(self, url: str, **kwargs: Any) -> Dict[str, Any]:
        """
        A wrapper for the safe_json_request -- makes an authenticated request
        to the MAL API, waits a bit, parses it to JSON
        """
        return cast(Dict[str, Any], self.safe_request(url, **kwargs).json())
