import os
import time
import warnings
import datetime
from typing import Any, Generator, Optional, Callable, Type, cast, Sequence

import requests
import backoff  # type: ignore[import]
import simplejson

from .list_type import ListType

Json = Any

from malexport.log import logger

REQUEST_WAIT_TIME: int = int(os.environ.get("MALEXPORT_REQUEST_WAIT_TIME", 10))


def fibo_backoff() -> Generator[float, None, None]:
    """
    Fibonacci backoff, with the first 7 elements consumed.
    In other words, this starts at 13, 21, ....
    """
    fib = backoff.fibo()
    for _ in range(7):
        next(fib)
    for n in fib:
        yield float(n)


def backoff_hdlr(details: Any) -> None:
    warning_msg = "Backing off {wait:0.1f} seconds after {tries} tries with {args} {kwargs}".format(
        **details
    )
    warnings.warn(warning_msg)


@backoff.on_exception(
    fibo_backoff,
    cast(Sequence[Type[Exception]], (requests.RequestException,)),
    max_tries=3,
    on_backoff=backoff_hdlr,
)
def safe_request(
    url: str,
    *,
    method: str = "GET",
    session: Optional[requests.Session] = None,
    on_error: Optional[Callable[[requests.Response], Any]] = None,
    wait_time: int = REQUEST_WAIT_TIME,
    **kwargs: Any,
) -> requests.Response:
    """
    Sleep for a while, make a request, and retry 3 times if the request fails
    Can supply an on_error function to do some custom behaviour if theres an HTTP error
    """
    time.sleep(wait_time)
    sess: requests.Session
    if session is not None:
        sess = session
    else:
        sess = requests.Session()
    logger.info(f"Requesting {url}...")
    kwargs.setdefault("allow_redirects", True)
    r = sess.request(method, url, **kwargs)
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
    return safe_request(url, session=session, **kwargs).json()


def default_encoder(o: Any) -> Any:
    if isinstance(o, ListType):
        return o.value
    if isinstance(o, datetime.datetime):
        return str(o)
    elif isinstance(o, datetime.date):
        return str(o)
    raise TypeError(f"{o} of type {type(o)} is not serializable")


def serialize(data: Any) -> str:
    return simplejson.dumps(
        data,
        default=default_encoder,
        namedtuple_as_object=True,
    )
