from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime;

@dataclass
class Post:
    title: str
    path: Path
    postedAt: datetime

    def to_json(self) -> Dict[str, Any]: 
        return {
           "title": self.title,
           "path": str(self.path),
           "postedAt": self.postedAt.isoformat(timespec="seconds"),
        }

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> Optional[Post]:
        try:
            title = str(json["title"])
            path = Path(str(json["path"]))
            postedAt = datetime.fromisoformat(json["postedAt"])

            return cls(title, path, postedAt)
        except KeyError:
            return None


@dataclass
class State:
    posts: List[Post]
