import json
from pathlib import Path
from datetime import datetime, timezone
from typing import NamedTuple, List, Iterator, TextIO, Optional

from ..paths import LocalDir


class Message(NamedTuple):
    at: Optional[datetime]
    username: str
    content: str


class Thread(NamedTuple):
    thread_id: int
    subject: str
    messages: List[Message]

    @property
    def url(self) -> str:
        raise NotImplementedError


def iter_user_threads(username: str) -> Iterator[Thread]:
    localdir = LocalDir.from_username(username)
    msg_dir = localdir.data_dir / "messages"
    for file in msg_dir.glob("*.json"):
        yield parse_thread(file)


def parse_thread(thread_file: Path) -> Thread:
    assert (
        thread_file.stem.isnumeric()
    ), f"Expected thread JSON file, found {thread_file}"
    with open(thread_file) as f:
        return _parse_thread(thread_data=f, thread_id=int(thread_file.stem))


def _parse_thread(thread_data: TextIO, thread_id: int) -> Thread:
    data = json.load(thread_data)
    messages: List[Message] = []
    for msg_data in data["messages"]:
        messages.append(
            Message(
                at=datetime.fromtimestamp(msg_data["dt"], tz=timezone.utc)
                if msg_data["dt"] is not None
                else None,
                username=msg_data["username"],
                content=msg_data["content"],
            )
        )
    return Thread(
        thread_id=thread_id,
        messages=messages,
        subject=data["subject"],
    )
