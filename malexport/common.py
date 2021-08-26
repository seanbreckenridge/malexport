import os
import time
import warnings
from typing import Any, Iterator, Dict, Optional

import requests
import backoff  # type: ignore[import]

Json = Any

from malexport.log import logger

REQUEST_WAIT_TIME: int = int(os.environ.get("MALEXPORT_REQUEST_WAIT_TIME", 8))


def fibo_backoff() -> Iterator[int]:
    """
    Fibonacci backoff, with the first 6 elements consumed.
    In other words, this starts at 13, 21, ....
    """
    fib = backoff.fibo()
    for _ in range(6):
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
    url: str, session: Optional[requests.Session] = None, **kwargs: Any
) -> requests.Response:
    time.sleep(REQUEST_WAIT_TIME)
    if session is None:
        session = requests.Session()
    logger.info(f"Requesting {url}...")
    resp = session.get(url, **kwargs)
    resp.raise_for_status()
    return resp


def safe_request_json(
    url: str, session: Optional[requests.Session] = None, **kwargs: Any
) -> Any:
    return safe_request(url, session, **kwargs).json()
