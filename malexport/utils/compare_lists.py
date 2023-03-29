#!/usr/bin/env python3

from typing import List, Callable

import click

from ..parse.mal_list import parse_file, PathIsh, Entry, ListType


def compare_lists(
    animelist1: PathIsh,
    animelist2: PathIsh,
    *,
    list_type: ListType,
    func1: Callable[[Entry], bool],
    func2: Callable[[Entry], bool],
    # todo: add more operations (difference, union, etc.)
    operation: str,
) -> List[Entry]:
    """
    Pass in two animelists and a function to filter the lists with.
    Once the lists are filtered, return

    """
    list1 = list(parse_file(animelist1, list_type=list_type))
    list2 = list(parse_file(animelist2, list_type=list_type))

    list1 = list(filter(func1, list1))
    list2 = list(filter(func2, list2))

    click.echo(f"List 1 filtered length: {len(list1)}", err=True)
    click.echo(f"List 2 filtered length: {len(list2)}", err=True)

    if operation == "intersection":
        intersection_ids = {e.id for e in list1} & {e.id for e in list2}
        return [e for e in list1 if e.id in intersection_ids]
    else:
        raise ValueError(f"Unknown operation {operation}")
