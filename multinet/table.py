"""Operations that deal with tables."""
from __future__ import annotations  # noqa: T484
from arango.collection import StandardCollection
from arango.aql import AQL

from typing import List, Dict, Iterable, Optional


class Table:
    """Table."""

    def __init__(self, name: str, workspace: str, handle: StandardCollection, aql: AQL):
        """Init Table class."""
        self.edge = False
        self.name = name
        self.workspace = workspace
        self.handle = handle
        self.aql = aql

    def rows(self, offset: Optional[int] = None, limit: Optional[int] = None) -> Dict:
        """Return the desired rows in a table."""
        rows = self.handle.find({}, skip=offset, limit=limit)
        count = self.handle.all().count()

        return {"count": count, "rows": list(rows)}

    def row_count(self) -> int:
        """Return the number of rows in a table."""
        return self.handle.count()

    def keys(self) -> Iterable[str]:
        """Return all the keys in a table."""
        return self.handle.keys()

    def rename(self, new_name: str):
        """Rename a table."""
        self.handle.rename(new_name)
        self.name = new_name

    def insert(self, rows: List[Dict]):
        """Insert rows into this table."""
        pass
