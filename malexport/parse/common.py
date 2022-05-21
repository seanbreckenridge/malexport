import os
import re
from typing import Optional, Union, List
from datetime import date

from distutils.util import strtobool as strtoint


def split_tags(tags: str) -> List[str]:
    return list(re.split(r"\s*,\s*", tags.strip()))


def parse_date_safe(d: Optional[str]) -> Optional[date]:
    if d is None:
        return None
    try:
        return date.fromisoformat(d)
    except ValueError:  # no date supplied, uses '0000-00-00'
        return None


# this maintains a buffer of 5 years into the future to account for
# entries which haven't yet been released
# i.e., if CUTOFF_DATE is 1930
# '29' parses to 2029
# '30' parses to 1930
# '31' parses to 1931
CUTOFF_DATE = int(os.environ.get("MALEXPORT_CUTOFF_DATE", date.today().year + 5))

DATE_REGEX = re.compile(r"(\d+)-(\d+)-(\d+)")


def parse_short_date(d: Optional[str]) -> Optional[date]:
    """
    Parses dates that look like '30-06-73' or '04-09-20'
    Is not always 100% accurate because '04-09-20'
    could mean 1920 or 2020
    """
    if d is None:
        return None
    short_cutoff = int(str(CUTOFF_DATE)[-2:])
    m = DATE_REGEX.match(d)
    if m:
        day, month, year_short = [int(k) for k in m.groups()]
        if year_short < short_cutoff:
            year = 2000 + year_short
        else:
            year = 1900 + year_short
        # set defaults for items which don't have months/days
        if day == 0:
            day = 1
        if month == 0:
            month = 1
        try:
            return date(year=year, month=month, day=day)
        except ValueError:
            return None
    else:
        return None


def strtobool(val: Union[str, int, bool]) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        val = str(val)
    return bool(strtoint(val.lower()))
