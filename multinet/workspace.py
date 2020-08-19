"""Operations that deal with workspaces."""
from __future__ import annotations  # noqa: T484

from dataclasses import dataclass, asdict, field
from arango.database import StandardDatabase
from arango.exceptions import DatabaseCreateError

from multinet.db import workspace_mapping, workspace_mapping_collection, db, system_db
from multinet.types import WorkspaceDocument, Workspace as WorkspaceDict
from multinet.errors import (
    AlreadyExists,
    InternalServerError,
    WorkspaceNotFound,
    BadQueryArgument,
    GraphNotFound,
)
from multinet.util import generate_arango_workspace_name
from multinet.user import User
from multinet.graph import Graph
from multinet.table import Table

from typing import Optional, List, Dict, Generator, Callable, Any


@dataclass
class WorkspacePermissions:
    """The permissions on a workspace."""

    # TODO: Change str to User once updating permissions storage
    owner: str
    maintainers: List[str] = field(default_factory=lambda: [])
    writers: List[str] = field(default_factory=lambda: [])
    readers: List[str] = field(default_factory=lambda: [])
    public: bool = False


class Workspace:
    """Workspace."""

    # Keys that aren't saved to the database
    exclude_keys = {"handle", "readonly_handle", "readonly"}

    def __init__(self, name: str, readonly: bool = True, **kwargs):
        """Create a Workspace Object."""
        self.name = name
        self.readonly = readonly

        # TODO: Don't access database right away
        doc = self.get_metadata()
        name = doc["internal"]

        self.internal: str = name
        self.permissions: WorkspacePermissions = WorkspacePermissions(
            **doc["permissions"]
        )

        self.readonly_handle = db(name)
        self.handle = db(name, readonly=False)

    @staticmethod
    def exists(name: str) -> bool:
        """Return if this workspace exists or not."""
        return bool(workspace_mapping(name))

    @staticmethod
    def create(name: str, owner: User):
        """Create a workspace, owned by `owner`."""
        if Workspace.exists(name):
            raise AlreadyExists("Workspace", name)

        workspace = Workspace(
            name,
            False,
            internal=generate_arango_workspace_name(),
            permissions=WorkspacePermissions(owner.sub),
        )

        try:
            db("_system").create_database(workspace.internal)
        except DatabaseCreateError:
            # Could only happen if there's a name collision
            raise InternalServerError()

        coll = workspace_mapping_collection()
        coll.insert(asdict(workspace))

    @staticmethod
    def list_all() -> Generator[str, None, None]:
        """Return a list of all workspace names."""
        coll = workspace_mapping_collection()
        return (doc["name"] for doc in coll.all())

    @staticmethod
    def from_dict(d: Dict, readonly: bool = True) -> Workspace:
        workspace = Workspace(name=d["name"], readonly=readonly)

        internal = d.get("internal")
        if internal:
            workspace.internal = internal

        permissions = d.get("permissions")
        if permissions:
            workspace.permissions = WorkspacePermissions(**permissions)

        return workspace

    def save(self):
        """Save this workspace to the database."""
        doc = self.get_metadata()
        instance_dict = self.asdict()

        doc.update(instance_dict)

        coll = workspace_mapping_collection()
        coll.update(doc)

    def get_permissions(self) -> WorkspacePermissions:
        doc = self.get_metadata()

        self.permissions = self.permissions or doc["permissions"]
        self.internal = self.internal or doc["internal"]

        return WorkspacePermissions(**doc["permissions"])

    def set_permissions(self, permissions: WorkspacePermissions):
        # doc = workspace_mapping(self.name)
        # if doc is None:
        #     raise WorkspaceNotFound

        # self.permissions = self.permissions or doc["permissions"]
        # self.internal = self.internal or doc["internal"]

        # return WorkspacePermissions(**doc["permissions"])
        pass

    def asdict(self) -> Dict:
        filtered = {
            k: v for k, v in self.__dict__.items() if k not in Workspace.exclude_keys
        }
        filtered["permissions"] = self.permissions.__dict__

        return filtered

    def rename(self):
        pass

    def delete(self):
        pass

    def get_metadata(self) -> Dict:
        doc = workspace_mapping(self.name)
        if not doc:
            raise WorkspaceNotFound

        return doc

    def graphs(self) -> List[Dict]:
        return self.handle.graphs()

    def graph(self, name: str) -> Graph:
        """Return Graph Class"""
        if not self.handle.has_graph(name):
            raise GraphNotFound(self.name, name)

        return Graph(name, self.name, self.handle.graph(name), self.handle)

    def tables(self, table_type: str = "all") -> Generator[str, None, None]:
        def pass_all(x: Dict[str, Any]) -> bool:
            return True

        def is_edge(x: Dict[str, Any]) -> bool:
            return x["edge"]

        def is_node(x: Dict[str, Any]) -> bool:
            return not x["edge"]

        if table_type == "all":
            desired_type = pass_all
        elif table_type == "node":
            desired_type = is_node
        elif table_type == "edge":
            desired_type = is_edge
        else:
            raise BadQueryArgument("type", table_type, ["all", "node", "edge"])

        tables = (
            table["name"]
            for table in self.handle.collections()
            if not table["system"]
            and desired_type(self.handle.collection(table["name"]).properties())
        )

        return tables

    def table(self, name: str) -> Table:
        """Return Table Class"""
        return Table(name, self.handle.collection(name))
