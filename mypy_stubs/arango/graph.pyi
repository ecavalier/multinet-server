from typing import Dict, List, Optional, Any
from arango.collection import EdgeCollection, VertexCollection  # type: ignore

class Graph:
    def edge_collection(self, name: str) -> EdgeCollection: ...
    def vertex_collection(self, name: str) -> VertexCollection: ...
    def vertex_collections(self) -> List[str]: ...
    def edge_definitions(self) -> List[Dict]: ...
    def vertex(
        self, vertex: Any, rev: Optional[Any] = ..., check_rev: bool = ...
    ) -> Dict: ...
