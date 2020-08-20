"""Operations that deal with workspaces."""
from __future__ import annotations  # noqa: T484

from dataclasses import dataclass, field
from arango.exceptions import DatabaseCreateError
from arango.cursor import Cursor

from multinet.db import (
    workspace_mapping,
    workspace_mapping_collection,
    db,
    system_db,
    _run_aql_query,
)
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

from typing import Any, List, Dict, Generator, Optional


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

    def __init__(self, name: str):
        """Create a Workspace Object."""
        self.name = name

        # TODO: Don't access database right away
        doc = self.get_metadata()

        # Due to call above, doc is guaranteed to be valid
        self.internal: str = doc["internal"]
        self.permissions: WorkspacePermissions = WorkspacePermissions(
            **doc["permissions"]
        )

        self.readonly_handle = db(self.internal)
        self.handle = db(self.internal, readonly=False)

    @staticmethod
    def exists(name: str) -> bool:
        """Return if this workspace exists or not."""
        return bool(workspace_mapping(name))

    @staticmethod
    def create(name: str, owner: User):
        """Create a workspace, owned by `owner`."""
        if Workspace.exists(name):
            raise AlreadyExists("Workspace", name)

        internal = generate_arango_workspace_name()

        try:
            system_db(readonly=False).create_database(internal)
        except DatabaseCreateError:
            # Could only happen if there's a name collision
            raise InternalServerError("Error creating workspace")

        permissions = WorkspacePermissions(owner=owner.sub).__dict__
        workspace_dict = {
            "name": name,
            "internal": internal,
            "permissions": permissions,
        }

        coll = workspace_mapping_collection(readonly=False)
        coll.insert(workspace_dict, sync=True)
        workspace_mapping.cache_clear()

        return Workspace(name)

    @staticmethod
    def list_all() -> Generator[str, None, None]:
        """Return a list of all workspace names."""
        coll = workspace_mapping_collection()
        return (doc["name"] for doc in coll.all())

    @staticmethod
    def list_public() -> Generator[str, None, None]:
        """Return a list of all public workspace names."""
        coll = workspace_mapping_collection()
        return (doc["name"] for doc in coll.find({"permissions.public": True}))

    @staticmethod
    def from_dict(d: Dict) -> Workspace:
        """Construct a workspace from a dict."""
        workspace = Workspace(name=d["name"])

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
        """Fetch and return the permissions on this workspace."""
        doc = self.get_metadata()

        self.permissions = self.permissions or doc["permissions"]
        self.internal = self.internal or doc["internal"]

        return WorkspacePermissions(**doc["permissions"])

    def set_permissions(self, permissions: WorkspacePermissions):
        """Set the permissions on a workspace."""
        pass

    def asdict(self) -> Dict:
        """Return this workspace as a dictionary."""
        filtered = {
            k: v for k, v in self.__dict__.items() if k not in Workspace.exclude_keys
        }
        filtered["permissions"] = self.permissions.__dict__

        return filtered

    def rename(self):
        """Rename this workspace."""
        pass

    def delete(self):
        """Delete this workspace."""
        pass

    def get_metadata(self) -> Dict:
        """Fetch and return the metadata for this workspace."""
        doc = workspace_mapping(self.name)
        if not doc:
            raise WorkspaceNotFound(self.name)

        return doc

    def graphs(self) -> List[Dict]:
        """Return the graphs in this workspace."""
        return self.handle.graphs()

    def graph(self, name: str) -> Graph:
        """Return a specific graph."""
        if not self.handle.has_graph(name):
            raise GraphNotFound(self.name, name)

        return Graph(name, self.name, self.handle.graph(name), self.handle.aql)

    def tables(self, table_type: str = "all") -> Generator[str, None, None]:
        """Return all tables of the specified type."""

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
        """Return a specific table."""
        return Table(name, self.name, self.handle.collection(name), self.handle.aql)

    def run_query(self, query: str, bind_vars: Optional[Dict] = None) -> Cursor:
        """Run an aql query on this workspace."""
        return _run_aql_query(self.handle.aql, query, bind_vars=bind_vars)