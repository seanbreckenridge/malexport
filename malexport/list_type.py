from enum import Enum


class ListType(Enum):
    """
    Basic Enum to avoid passing around the strings 'anime' and 'manga' everywhere
    """

    ANIME = "anime"
    MANGA = "manga"
