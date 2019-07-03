from multinet import db
from multinet.types import Graph, Table


# get a list of workspaces a user has access to.
def workspaces(root, info, name=""):
    return [workspace for workspace in db.get_workspaces(name) if not name or workspace == name]


# get a list of graphs in a workspace
def graphs(root, info, workspace, name=""):
    return [
        Graph(workspace, graph)
        for graph in db.workspace_graphs(workspace)
        if not name or graph == name
    ]


# get a single graph by workspace/name
def graph(root, info, workspace, name):
    return Graph(workspace, name) if db.workspace_graph(workspace, name) else None


# get a list of tables in a workspace
def tables(root, info, workspace, name=""):
    return [
        Table(workspace, table)
        for table in db.workspace_tables(workspace)
        if not name or table == name
    ]


def table(root, info, workspace, name):
    return Table(workspace, name) if db.workspace_table(workspace, name) else None


def add_resolvers(schema):
    fields = schema.get_type('Query').fields
    fields['workspaces'].resolver = workspaces
    fields['graphs'].resolver = graphs
    fields['graph'].resolver = graph
    fields['tables'].resolver = tables
    fields['table'].resolver = table
