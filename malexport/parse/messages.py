import json
from pathlib import Path
from datetime import datetime, timezone
from typing import NamedTuple, List, Iterator, Optional, Dict, Any

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
        yield _parse_thread(file)


def _parse_thread(thread_file: Path) -> Thread:
    thread_id = thread_file.stem
    assert (
        thread_id.isnumeric()
    ), f"Expected thread JSON file where name includes ID, found {thread_file}"
    data = json.loads(thread_file.read_text())
    messages = _parse_messages(data["messages"])
    return Thread(
        thread_id=int(thread_id), messages=list(messages), subject=data["subject"]
    )


def _parse_messages(message_data: List[Dict[str, Any]]) -> Iterator[Message]:
    for msg_data in message_data:
        yield Message(
            at=(
                datetime.fromtimestamp(msg_data["dt"], tz=timezone.utc)
                if msg_data["dt"] is not None
                else None
            ),
            username=msg_data["username"],
            content=msg_data["content"],
        )
