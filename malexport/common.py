import os
import time
import warnings
from typing import Any, Iterator, Dict, Optional, Callable

import requests
import backoff  # type: ignore[import]

Json = Any

from malexport.log import logger

REQUEST_WAIT_TIME: int = int(os.environ.get("MALEXPORT_REQUEST_WAIT_TIME", 10))


def fibo_backoff() -> Iterator[int]:
    """
    Fibonacci backoff, with the first 6 elements consumed.
    In other words, this starts at 13, 21, ....
    """
    fib = backoff.fibo()
    for _ in range(7):
        next(fib)
    yield from fib


def backoff_warn(details: Dict[str, Any]) -> None:
    warning_msg: str = "Backing off {wait:0.1f} seconds afters {tries} tries with {args} {kwargs}".format(
        **details
    )
    warnings.warn(warning_msg)


@backoff.on_exception(
    fibo_backoff, requests.RequestException, max_tries=3, on_backoff=backoff_warn
)
def safe_request(
    url: str,
    method: str = "GET",
    on_error: Optional[Callable[[requests.Response], Any]] = None,
    wait_time: int = REQUEST_WAIT_TIME,
    **kwargs: Any,
) -> requests.Response:
    """
    Sleep for a while, make a request, and retry 3 times if the request fails
    Can supply an on_error function to do some custom behaviour if theres an HTTP error
    """
    time.sleep(wait_time)
    session: requests.Session
    if "session" in kwargs:
        session = kwargs.pop("session")
    else:
        session = requests.Session()
    logger.info(f"Requesting {url}...")
    kwargs.setdefault("allow_redirects", True)
    r = session.request(method, url, **kwargs)
    try:
        r.raise_for_status()
    except requests.RequestException as e:
        if on_error is not None:
            on_error(r)  # do something, e.g. refresh a expired bearer token
        raise e  # raise anyways, so this request retries
    return r


def safe_request_json(
    url: str, session: Optional[requests.Session] = None, **kwargs: Any
) -> Any:
    """
    Run a safe_request, then parse the response to JSON
    """
    return safe_request(url, session, **kwargs).json()
