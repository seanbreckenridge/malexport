import sys
import json
from typing import List, Set, NamedTuple, Callable, Tuple
from pathlib import Path

from git.repo.base import Repo  # type: ignore[import]
from git.cmd import Git  # type: ignore[import]

from .combine import combine, CombineResults, AnimeData, MangaData
from ..paths import mal_id_cache_dir
from ..log import logger

repo_dir = Path(mal_id_cache_dir)


class Approved(NamedTuple):
    """
    Uses https://github.com/seanbreckenridge/mal-id-cache to fetch a list
    of approved MAL IDs
    """

    anime: Set[int]
    manga: Set[int]

    @staticmethod
    def git_clone() -> Repo:
        """
        Clone or return if .git repo already exists
        """
        if not repo_dir.parent.exists():
            repo_dir.parent.mkdir(exist_ok=True, parents=True)

        if repo_dir.exists():
            assert (
                repo_dir / ".git"
            ).exists(), f"{repo_dir} exists but {repo_dir}/.git does not"
            return Repo(mal_id_cache_dir)

        else:
            return Repo.clone_from(
                "https://github.com/seanbreckenridge/mal-id-cache", repo_dir
            )

    @classmethod
    def git_pull(cls) -> None:
        cls.git_clone()
        gg = Git(repo_dir)
        # TODO: add try/except incase theres no internet
        gg.pull()
        commit_id = gg.log().splitlines()[0].split()[-1]
        logger.debug(f"mal-id-cache Commit ID: {commit_id}")

    @classmethod
    def create_if_doesnt_exist(cls) -> None:
        if not (repo_dir / ".git").exists():
            cls.git_pull()

    @classmethod
    def parse_from_git_dir(cls) -> "Approved":
        cls.create_if_doesnt_exist()
        anime_file = repo_dir / "cache" / "anime_cache.json"
        manga_file = repo_dir / "cache" / "manga_cache.json"
        anime = json.loads(anime_file.read_text())
        manga = json.loads(manga_file.read_text())
        return Approved(
            anime=set(anime["sfw"] + anime["nsfw"]),
            manga=set(manga["sfw"] + manga["nsfw"]),
        )


def _default_parse_func(backup_dir: Path, username: str) -> CombineResults:
    return combine(username, data_dir=backup_dir)


def recover_deleted_single(
    *,
    approved: Approved,
    from_backup_dir: Path,
    username: str,
    parse_func: Callable[[Path, str], CombineResults] = _default_parse_func,
) -> CombineResults:
    """
    returns any data from a backup that is not in the approved list
    """

    assert from_backup_dir.exists(), f"Backup dir {from_backup_dir} does not exist"

    new_anime, new_manga = parse_func(from_backup_dir, username)

    return (
        [new for new in new_anime if new.id not in approved.anime],
        [new for new in new_manga if new.id not in approved.manga],
    )


def recover_deleted(
    *,
    approved: Approved,
    backups: List[Path],
    username: str,
    parse_func: Callable[[Path, str], CombineResults] = _default_parse_func,
) -> CombineResults:
    """
    parses each backup in reverse order using parse_func, and returns the
    most recent data for each deleted entry
    """

    try:
        import my.core.structure
    except ImportError as e:
        logger.error(
            f"my.core.structure not found, cannot parse backups, install by running `{sys.executable} -m pip install hpi`",
            exc_info=e,
        )
        sys.exit(1)
    else:

        def _parse_func(backup_dir: Path, username: str) -> CombineResults:
            with my.core.structure.match_structure(
                backup_dir,
                (
                    "forum",
                    "messages",
                    "friends.json",
                    "animelist.json",
                    "mangalist.json",
                    "animelist.xml",
                    "mangalist.xml",
                    "animelist_api.json",
                    "mangalist_api.json",
                ),
                partial=True,
            ) as res:
                assert len(res) == 1, f"Expected 1 match, got {len(res)}: {res}"
                return combine(username, data_dir=res[0])

        assert _parse_func is not None
        parse_func = _parse_func

    emitted_entries: Set[Tuple[int, str]] = set()
    emit_anime: List[AnimeData] = []
    emit_manga: List[MangaData] = []

    for backup in reversed(backups):
        logger.debug(f"Recovering deleted entries from {backup}")
        anime, manga = recover_deleted_single(
            approved=approved,
            from_backup_dir=backup,
            username=username,
            parse_func=parse_func,
        )
        for a in anime:
            if (a.id, "anime") not in emitted_entries:
                emit_anime.append(a)
                emitted_entries.add((a.id, "anime"))
        for m in manga:
            if (m.id, "manga") not in emitted_entries:
                emit_manga.append(m)
                emitted_entries.add((m.id, "manga"))

    return emit_anime, emit_manga
