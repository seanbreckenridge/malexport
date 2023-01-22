import json
from typing import List, Set, NamedTuple
from pathlib import Path

from git.repo.base import Repo  # type: ignore[import]
from git.cmd import Git  # type: ignore[import]

from .combine import combine, CombineResults
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

    @staticmethod
    def parse_from_git_dir() -> "Approved":
        anime_file = repo_dir / "cache" / "anime_cache.json"
        manga_file = repo_dir / "cache" / "manga_cache.json"
        anime = json.loads(anime_file.read_text())
        manga = json.loads(manga_file.read_text())
        return Approved(
            anime=set(anime["sfw"] + anime["nsfw"]),
            manga=set(manga["sfw"] + manga["nsfw"]),
        )


def recover_deleted_single(
    *, current_state: CombineResults, from_backup_dir: Path, username: str
) -> CombineResults:
    assert from_backup_dir.exists(), f"Backup dir {from_backup_dir} does not exist"

    old_anime, old_manga = current_state
    old_anime_ids = set(old.id for old in old_anime)
    old_manga_ids = set(old.id for old in old_manga)

    new_anime, new_manga = combine(username, data_dir=from_backup_dir)

    return (
        [new for new in new_anime if new.id not in old_anime_ids],
        [new for new in new_manga if new.id not in old_manga_ids],
    )


def recover_deleted(
    *, current_state: CombineResults, backups: List[Path], username: str
) -> CombineResults:
    raise NotImplementedError("TODO: implement this")
