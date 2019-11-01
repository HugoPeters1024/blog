from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime


@dataclass
class Post:
    number: int
    title: str
    postedAt: datetime

    def to_json(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "postedAt": self.postedAt.isoformat(timespec="seconds"),
        }

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> Optional[Post]:
        try:
            number = int(json["number"])
            title = str(json["title"])
            postedAt = datetime.fromisoformat(json["postedAt"])

            return cls(number, title, postedAt)
        except KeyError:
            return None


@dataclass
class State:
    posts: List[Post]

    def to_json(self) -> Dict[str, Any]:
        return {"posts": list(map(Post.to_json, self.posts))}

    @classmethod
    def from_json(cls, json: Dict[str, Any]) -> Optional[State]:
        try:
            posts = list([Post.from_json(x) for x in json["posts"]])
            return cls([x for x in posts if x is not None])
        except KeyError:
            return None
