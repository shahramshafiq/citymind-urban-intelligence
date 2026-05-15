# Shared CityGraph — single source of truth, observer pattern for change notifications
import math
import random
from enum import Enum


class LocationType(Enum):
    EMPTY = "E"
    RESIDENTIAL = "R"
    HOSPITAL = "H"
    SCHOOL = "S"
    INDUSTRIAL = "I"
    POWER_PLANT = "P"
    AMBU_DEPOT = "D"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Higher risk means travelling into that node becomes more expensive.
RISK_MULTIPLIERS = { RiskLevel.LOW: 1.0, RiskLevel.MEDIUM: 1.2, RiskLevel.HIGH: 1.5, }


class Node:
    def __init__(self, node_id: int, row: int, col: int):
        self.node_id = node_id
        self.row = row
        self.col = col
        self.location_type = LocationType.EMPTY
        self.population_density = random.uniform(0.1, 1.0)
        self.risk_index = 0.0
        self.accessible = True
        self.crime_risk_level = RiskLevel.LOW
        self.risk_multiplier = 1.0

    def __repr__(self):
        return f"Node({self.row}, {self.col} | {self.location_type.value})"


class Edge:
    def __init__(self, start_node: int, end_node: int, base_cost: float = 1.0):
        self.u = start_node
        self.v = end_node
        self.base_cost = base_cost
        self.blocked = False

    def effective_cost(self, destination_node: Node) -> float:
        if self.blocked:
            return float("inf")
        return self.base_cost * destination_node.risk_multiplier

    def __repr__(self):
        if self.blocked:
            status = "BLOCKED"
        else:
            status = "open"
        return f"Edge({self.u} -> {self.v}, cost={self.base_cost}, {status})"


class CityGraph:
    def __init__(self, rows: int = 10, cols: int = 10):
        self.rows = rows
        self.cols = cols

        self._nodes: dict[int, Node] = {}
        self._edges: dict[tuple, Edge] = {}
        self._adj: dict[int, list[int]] = {}
        self._observers: list = []

        self._build_grid()

    def _build_grid(self):
        for row in range(self.rows):
            for col in range(self.cols):
                node_id = self._rc_to_id(row, col)
                self._nodes[node_id] = Node(node_id, row, col)
                self._adj[node_id] = []

        for row in range(self.rows):
            for col in range(self.cols):
                node_id = self._rc_to_id(row, col)
                if col + 1 < self.cols:
                    right_node = self._rc_to_id(row, col + 1)
                    self._connect(node_id, right_node)
                if row + 1 < self.rows:
                    bottom_node = self._rc_to_id(row + 1, col)
                    self._connect(node_id, bottom_node)

    def _connect(self, node_a: int, node_b: int):
        edge_key = self._edge_key(node_a, node_b)
        first_node = self._nodes[node_a]
        second_node = self._nodes[node_b]
        # residential-to-residential roads cost 0.8 instead of 1.0 — per project specification
        if (
            first_node.location_type == LocationType.RESIDENTIAL
            and second_node.location_type == LocationType.RESIDENTIAL
        ):
            base_cost = 0.8
        else:
            base_cost = 1.0
        self._edges[edge_key] = Edge(node_a, node_b, base_cost)
        self._adj[node_a].append(node_b)
        self._adj[node_b].append(node_a)

    def _rc_to_id(self, row: int, col: int) -> int:
        return row * self.cols + col

    def _id_to_rc(self, node_id: int) -> tuple[int, int]:
        return divmod(node_id, self.cols)

    def _edge_key(self, node_a: int, node_b: int) -> tuple:
        return (min(node_a, node_b), max(node_a, node_b))

    def register_observer(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def _notify(self, event_type: str, data: dict):
        for observer in self._observers:
            try:
                observer.on_graph_event(event_type, data)
            except Exception as error:
                print(f"[CityGraph] Observer error: {error}")

    def block_edge(self, node_a: int, node_b: int):
        edge_key = self._edge_key(node_a, node_b)
        if edge_key in self._edges:
            self._edges[edge_key].blocked = True
            self._notify("EDGE_BLOCKED", {"u": node_a, "v": node_b})

    def unblock_edge(self, node_a: int, node_b: int):
        edge_key = self._edge_key(node_a, node_b)
        if edge_key in self._edges:
            self._edges[edge_key].blocked = False
            self._notify("EDGE_UNBLOCKED", {"u": node_a, "v": node_b})

    def update_risk(self, node_id: int, risk_level: RiskLevel):
        node = self._nodes.get(node_id)
        if node:
            node.crime_risk_level = risk_level
            node.risk_multiplier = RISK_MULTIPLIERS[risk_level]
            if risk_level == RiskLevel.LOW:
                node.risk_index = 0.2
            elif risk_level == RiskLevel.MEDIUM:
                node.risk_index = 0.5
            else:
                node.risk_index = 0.9
            self._notify(
                "RISK_UPDATED",
                {
                    "node_id": node_id,
                    "level": risk_level.value
                }
            )

    def add_location(self, node_id: int, location_type: LocationType):
        node = self._nodes.get(node_id)
        if node:
            node.location_type = location_type
            # update road costs around this node - residential-to-residential roads are cheaper
            for neighbor_id in self._adj[node_id]:
                edge_key = self._edge_key(node_id, neighbor_id)
                if edge_key in self._edges:
                    neighbor_node = self._nodes[neighbor_id]
                    if (
                        location_type == LocationType.RESIDENTIAL
                        and neighbor_node.location_type == LocationType.RESIDENTIAL
                    ):
                        self._edges[edge_key].base_cost = 0.8
                    else:
                        self._edges[edge_key].base_cost = 1.0
            self._notify(
                "LOCATION_SET",
                {
                    "node_id": node_id,
                    "type": location_type.value
                }
            )

    def get_neighbors(self, node_id: int) -> list[tuple[int, float]]:
        neighbors = []
        for neighbor_id in self._adj.get(node_id, []):
            edge_key = self._edge_key(node_id, neighbor_id)
            edge = self._edges.get(edge_key)
            if edge and not edge.blocked:
                cost = edge.effective_cost(self._nodes[neighbor_id])
                neighbors.append((neighbor_id, cost))
        return neighbors

    def get_all_nodes(self) -> list[Node]:
        return list(self._nodes.values())

    def get_node(self, node_id: int) -> Node:
        return self._nodes.get(node_id)

    def get_node_by_rc(self, row: int, col: int) -> Node:
        return self._nodes.get(self._rc_to_id(row, col))

    def get_all_edges(self) -> list[Edge]:
        return list(self._edges.values())

    def get_blocked_edges(self) -> list[Edge]:
        blocked_edges = []
        for edge in self._edges.values():
            if edge.blocked:
                blocked_edges.append(edge)
        return blocked_edges

    def node_id(self, row: int, col: int) -> int:
        return self._rc_to_id(row, col)

    def rc(self, node_id: int) -> tuple[int, int]:
        return self._id_to_rc(node_id)

    def node_count(self) -> int:
        return len(self._nodes)

    def shortest_path(self, source: int, destination: int) -> tuple[list[int], float]:
        try:
            from challenges.challenge4_astar import astar
            return astar(self, source, destination)
        except (ImportError, NotImplementedError):
            return self._bfs_fallback(source, destination)

    def _bfs_fallback(self, source: int, destination: int) -> tuple[list[int], float]:
        # only used if A* is unavailable; BFS doesn't account for variable edge weights
        from collections import deque
        queue = deque()
        queue.append((source, [source], 0.0))
        visited = {source}
        while queue:
            current_node, path, total_cost = queue.popleft()
            if current_node == destination:
                return path, total_cost
            for neighbor_id, cost in self.get_neighbors(current_node):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    new_path = path + [neighbor_id]
                    new_cost = total_cost + cost
                    queue.append((neighbor_id, new_path, new_cost))
        return [], float("inf")

    def euclidean_distance(self, node_a: int, node_b: int) -> float:
        row_a, col_a = self._id_to_rc(node_a)
        row_b, col_b = self._id_to_rc(node_b)
        row_difference = row_a - row_b
        col_difference = col_a - col_b
        return math.sqrt(row_difference ** 2 + col_difference ** 2)

    def manhattan_distance(self, node_a: int, node_b: int) -> float:
        row_a, col_a = self._id_to_rc(node_a)
        row_b, col_b = self._id_to_rc(node_b)
        return abs(row_a - row_b) + abs(col_a - col_b)
