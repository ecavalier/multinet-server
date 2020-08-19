"""Operations that deal with tables."""
from __future__ import annotations  # noqa: T484
from arango.collection import StandardCollection

from multinet import workspace

from typing import List, Dict, Iterable, Optional


class Table:
    """Table."""

    def __init__(self, name: str, handle: StandardCollection):
        self.edge = False
        self.name = name
        self.handle = handle

    def rows(self, offset: Optional[int] = None, limit: Optional[int] = None):
        rows = self.handle.find({}, skip=offset, limit=limit)
        count = self.handle.all().count()

        return {"count": count, "rows": list(rows)}

    def row_count(self) -> int:
        return self.handle.count()

    def keys(self) -> Iterable[str]:
        return self.handle.keys()

    def rename(self, new_name: str):
        self.handle.rename(new_name)
        self.name = new_name

    def upload(self, rows: List[Dict]):
        pass
