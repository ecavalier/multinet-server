"""Operations that deal with graphs."""

from arango.database import StandardDatabase
from arango.graph import Graph as ArangoGraph
from arango.cursor import Cursor
from arango.exceptions import DocumentGetError

from multinet import workspace
from multinet.table import Table
from multinet.types import EdgeDirection
from multinet.errors import TableNotFound, NodeNotFound

from typing import Any, List, Dict, Iterable, Optional


edge_direction_map = {"all": "any", "incoming": "inbound", "outgoing": "outbound"}


class Graph:
    """Graph."""

    def __init__(
        self,
        name: str,
        workspace_name: str,
        handle: ArangoGraph,
        workspace_handle: StandardDatabase,
    ):
        self.name = name
        self.workspace_name = workspace_name
        self.handle = handle
        self.workspace_handle = workspace_handle

    def nodes(
        self, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        coll_names = self.handle.vertex_collections()

        result_set_size = 0
        query_size = 0
        total_nodes = []

        for coll_name in coll_names:
            coll = self.handle.vertex_collection(coll_name)
            result_set_size += coll.all().count()

            if limit is None or query_size < limit:
                remaining_limit = min(limit, limit - query_size) if limit else None
                cur = coll.all(skip=offset, limit=remaining_limit)

                query_size += cur.count()
                total_nodes.extend(list(cur))

        # Because we're embedding a list in a dictionary, we can't take full advantage
        # of cursors. If this isn't required in the future, this may be more efficient
        return {"count": result_set_size, "nodes": list(total_nodes)}

    def node_tables(self) -> Iterable[Table]:
        return self.handle.vertex_collections()

    def edge_table(self) -> Table:
        edge_defs = self.handle.edge_definitions()

        # Currently assume one edge definition per graph
        return edge_defs[0]["edge_collection"]

    def node_attributes(self, table: str, node: str):
        node_id = f"{table}/{node}"

        try:
            res = self.handle.vertex(node_id)
        except DocumentGetError:
            raise TableNotFound(self.workspace_name, table)

        if res is None:
            raise NodeNotFound(table, node)

        if "_rev" in res:
            del res["_rev"]

        return res

    def node_edges(
        self,
        table: str,
        node: str,
        direction: EdgeDirection = "all",
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """Return the edges of the node `node` from table `table`."""
        node_id = f"{table}/{node}"
        edge_table = self.edge_table()

        query_direction = edge_direction_map[direction]
        query_filter = f'e._from == "{node_id}" || e._to == "{node_id}"'
        if query_direction == "inbound":
            query_filter = f'e._to == "{node_id}"'
        elif query_direction == "outbound":
            query_filter = f'e._from == "{node_id}"'

        query = f"""
        FOR e IN {edge_table}
            FILTER {query_filter}
            LIMIT {offset}, {limit}
            RETURN {{
                "edge": e._id,
                "from": e._from,
                "to": e._to
            }}
        """

        count_query = f"""
        FOR e IN {edge_table}
            FILTER {query_filter}
            COLLECT WITH COUNT INTO count
            RETURN count
        """

        query_cur = self.workspace_handle.aql.execute(query)
        count_cur = self.workspace_handle.aql.execute(count_query)

        return {"count": next(count_cur), "edges": list(query_cur)}
