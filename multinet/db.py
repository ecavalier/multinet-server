"""Low-level database operations."""
import os
from functools import lru_cache

from arango import ArangoClient
from arango.database import StandardDatabase
from arango.collection import StandardCollection
from arango.aql import AQL
from arango.cursor import Cursor

from arango.exceptions import AQLQueryValidateError, AQLQueryExecuteError
from requests.exceptions import ConnectionError

from typing import Any, List, Dict, Optional
from typing_extensions import TypedDict

from multinet.errors import AQLExecutionError, AQLValidationError


# Type definitions.
GraphSpec = TypedDict("GraphSpec", {"nodeTables": List[str], "edgeTable": str})
GraphNodesSpec = TypedDict("GraphNodesSpec", {"count": int, "nodes": List[str]})
GraphEdgesSpec = TypedDict("GraphEdgesSpec", {"count": int, "edges": List[str]})

arango = ArangoClient(
    host=os.environ.get("ARANGO_HOST", "localhost"),
    port=int(os.environ.get("ARANGO_PORT", "8529")),
    protocol=os.environ.get("ARANGO_PROTOCOL", "http"),
)
restricted_keys = {"_rev", "_id"}


def db(name: str, readonly: bool = True, immediate: bool = False) -> StandardDatabase:
    """Return a handle for Arango database `name`."""

    username = "readonly" if readonly else "root"
    password = (
        os.environ.get("ARANGO_READONLY_PASSWORD", "letmein")
        if readonly
        else os.environ.get("ARANGO_PASSWORD", "letmein")
    )

    return arango.db(name, username=username, password=password, verify=immediate)


@lru_cache()
def system_db(readonly: bool = True) -> StandardDatabase:
    """Return the singleton `_system` db handle."""
    return db("_system", readonly)


# TODO: Fix/remove this
def check_db() -> bool:
    """Check the database to see if it's alive."""
    try:
        system_db().has_database("test")
        return True
    except ConnectionError:
        return False


def register_legacy_workspaces() -> None:
    """Add legacy workspaces to the workspace mapping."""
    sysdb = system_db()
    coll = workspace_mapping_collection(readonly=False)

    databases = {name for name in sysdb.databases() if name != "_system"}
    registered = {doc["internal"] for doc in coll.all()}

    unregistered = databases - registered
    for workspace in unregistered:
        coll.insert({"name": workspace, "internal": workspace})


# Since this shouldn't ever change while running, this function becomes a singleton
@lru_cache(maxsize=1)
def workspace_mapping_collection(readonly: bool = True) -> StandardCollection:
    """Return the collection used for mapping external to internal workspace names."""
    sysdb = system_db(readonly=readonly)

    if not sysdb.has_collection("workspace_mapping"):
        sysdb.create_collection("workspace_mapping")

    return sysdb.collection("workspace_mapping")


# Caches the document that maps an external workspace name to it's internal one
@lru_cache()
def workspace_mapping(name: str) -> Optional[Dict]:
    """
    Get the document containing the workspace mapping for :name: (if it exists).

    Returns the document if found, otherwise returns None.
    """
    coll = workspace_mapping_collection()
    docs = list(coll.find({"name": name}, limit=1))

    if docs:
        return docs[0]

    return None


def user_collection() -> StandardCollection:
    """Return the collection that contains user documents."""
    sysdb = db("_system", readonly=False)

    if not sysdb.has_collection("users"):
        sysdb.create_collection("users")

    return sysdb.collection("users")


def search_user(query: str) -> Cursor:
    """Search for users given a partial string."""

    coll = user_collection()
    aql = db("_system").aql

    bind_vars = {"@users": coll.name, "query": query}
    query = """
        FOR doc in @@users
          FILTER CONTAINS(LOWER(doc.name), LOWER(@query))
            OR CONTAINS(LOWER(doc.email), LOWER(@query))

          LIMIT 50
          RETURN doc
    """

    return _run_aql_query(aql, query, bind_vars)


# def create_workspace(name: str, user: User) -> str:
#     """Create a new workspace named `name`, owned by `user`."""

#     # Bail out with a 409 if the workspace exists already.
#     if workspace_exists(name):
#         raise AlreadyExists("Workspace", name)

#     # Create a workspace mapping document to represent the new workspace. This
#     # document (1) sets the external name of the workspace to the requested
#     # name, (2) sets the internal name to a random string, and (3) makes the
#     # specified user the owner of the workspace.
#     ws_doc: Workspace = {
#         "name": name,
#         "internal": util.generate_arango_workspace_name(),
#         "permissions": {
#             "owner": user.sub,
#             "maintainers": [],
#             "writers": [],
#             "readers": [],
#             "public": False,
#         },
#     }

#     # Attempt to create an Arango database to serve as the workspace itself.
#     # There is an astronomically negligible chance that the internal name would
#     # clash with an existing internal name; in this case we go full UNIX and
#     # just bail out, rather than building in logic to catch it happening.
#     try:
#         system_db().create_database(ws_doc["internal"])
#     except DatabaseCreateError:
#         # Could only happen if there's a name collisison
#         raise InternalServerError()

#     # Retrieve the workspace mapping collection and log the workspace metadata
#     # record.
#     coll = workspace_mapping_collection()
#     coll.insert(ws_doc)

#     # Invalidate the cache for things changed by this function
#     workspace_mapping.cache_clear()
#     get_workspace_db.cache_clear()

#     return name


# def rename_workspace(old_name: str, new_name: str) -> None:
#     """Rename a workspace."""
#     doc = workspace_mapping(old_name)
#     if not doc:
#         raise WorkspaceNotFound(old_name)

#     if workspace_exists(new_name):
#         raise AlreadyExists("Workspace", new_name)

#     doc["name"] = new_name
#     coll = workspace_mapping_collection()
#     coll.update(doc)

#     # Invalidate the cache for things changed by this function
#     get_workspace_db.cache_clear()
#     workspace_mapping.cache_clear()


# def delete_workspace(name: str) -> None:
#     """Delete the workspace named `name`."""
#     doc = workspace_mapping(name)
#     if not doc:
#         raise WorkspaceNotFound(name)

#     sysdb = system_db()
#     coll = workspace_mapping_collection()

#     sysdb.delete_database(doc["internal"])
#     coll.delete(doc["_id"])

#     # Invalidate the cache for things changed by this function
#     get_workspace_db.cache_clear()
#     workspace_mapping.cache_clear()


# def set_workspace_permissions(
#     name: str, permissions: WorkspacePermissions
# ) -> WorkspacePermissions:
#     """Update the permissions for a given workspace."""
#     doc = copy.deepcopy(get_workspace_metadata(name))
#     if doc is None:
#         raise DatabaseCorrupted()

#     # TODO: Do user object validation once ORM is implemented

#     # Disallow changing workspace ownership through this function.
#     new_permissions = copy.deepcopy(permissions)
#     new_permissions["owner"] = doc["permissions"]["owner"]

#     doc["permissions"] = new_permissions
#     return_doc = workspace_mapping_collection().get(
#         workspace_mapping_collection().update(doc)
#     )["permissions"]

#     workspace_mapping.cache_clear()

#     return cast(WorkspacePermissions, return_doc)


# def create_aql_table(workspace: str, name: str, aql: str) -> str:
#     """Create a new table from an AQL query."""
#     db = get_workspace_db(workspace, readonly=True)

#     if db.has_collection(name):
#         raise AlreadyExists("table", name)

#     # In the future, the result of this validation can be
#     # used to determine dependencies in virtual tables
#     rows = list(_run_aql_query(db.aql, aql))
#     validate_csv(rows, "_key", False)

#     db = get_workspace_db(workspace, readonly=False)
#     coll = db.create_collection(name, sync=True)
#     coll.insert_many(rows)

#     return name


# def delete_table(workspace: str, table: str) -> str:
#     """Delete a table."""
#     space = get_workspace_db(workspace, readonly=False)
#     if space.has_collection(table):
#         space.delete_collection(table)

#     return table


def _run_aql_query(
    aql: AQL, query: str, bind_vars: Optional[Dict[str, Any]] = None
) -> Cursor:
    try:
        aql.validate(query)
        cursor = aql.execute(query, bind_vars=bind_vars)
    except AQLQueryValidateError as e:
        raise AQLValidationError(str(e))
    except AQLQueryExecuteError as e:
        raise AQLExecutionError(str(e))

    return cursor


# def aql_query(workspace: str, query: str) -> Cursor:
#     """Perform an AQL query in the given workspace."""
#     aql = get_workspace_db(workspace, readonly=True).aql
#     return _run_aql_query(aql, query)


# def create_graph(
#     workspace: str,
#     graph: str,
#     edge_table: str,
#     from_vertex_collections: Set[str],
#     to_vertex_collections: Set[str],
# ) -> bool:
#     """Create a graph named `graph`, defined by`node_tables` and `edge_table`."""
#     space = get_workspace_db(workspace, readonly=False)
#     if space.has_graph(graph):
#         return False

#     try:
#         space.create_graph(
#             graph,
#             edge_definitions=[
#                 {
#                     "edge_collection": edge_table,
#                     "from_vertex_collections": list(from_vertex_collections),
#                     "to_vertex_collections": list(to_vertex_collections),
#                 }
#             ],
#         )
#     except EdgeDefinitionCreateError as e:
#         raise GraphCreationError(str(e))

#     return True


# def delete_graph(workspace: str, graph: str) -> str:
#     """Delete graph `graph` from workspace `workspace`."""
#     space = get_workspace_db(workspace, readonly=False)
#     if space.has_graph(graph):
#         space.delete_graph(graph)

#     return graph
