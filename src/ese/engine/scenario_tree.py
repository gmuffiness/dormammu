"""DFS scenario tree for Dormammu.

The scenario tree represents the branching space of possible futures that
the simulation explores via depth-first search. Each node is a distinct
world timeline; child nodes are hypothesis-driven branches from the parent.

Terminology
-----------
- Node:      A single scenario branch (a timeline segment).
- Depth:     How many branch points deep we are from the root.
- Leaf node: A node at max_depth that is fully simulated.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator


class NodeStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    PRUNED = "pruned"


@dataclass
class ScenarioNode:
    """A single node in the DFS scenario tree.

    Each node holds a hypothesis (what diverges here from the parent),
    the world state at entry, and pointers to its children.
    """

    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    simulation_id: str = ""
    parent_id: str | None = None
    depth: int = 0

    hypothesis: str = ""
    """The divergent assumption that distinguishes this branch."""

    status: NodeStatus = NodeStatus.PENDING

    children: list[str] = field(default_factory=list)
    """child node_ids"""

    entry_world_state_id: str = ""
    exit_world_state_id: str = ""

    turns_simulated: int = 0
    years_simulated: int = 0

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "simulation_id": self.simulation_id,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "hypothesis": self.hypothesis,
            "status": self.status.value,
            "children": self.children,
            "entry_world_state_id": self.entry_world_state_id,
            "exit_world_state_id": self.exit_world_state_id,
            "turns_simulated": self.turns_simulated,
            "years_simulated": self.years_simulated,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioNode":
        data = dict(data)
        data["status"] = NodeStatus(data.get("status", "pending"))
        return cls(**data)


class ScenarioTree:
    """Manages the DFS traversal of the scenario tree.

    The tree is stored as a flat dict of nodes keyed by node_id.
    DFS traversal is lazy: nodes are expanded only when visited.
    """

    def __init__(self, simulation_id: str, max_depth: int = 5) -> None:
        self.simulation_id = simulation_id
        self.max_depth = max_depth
        self._nodes: dict[str, ScenarioNode] = {}
        self._root_id: str | None = None

    # ------------------------------------------------------------------ #
    # Tree construction
    # ------------------------------------------------------------------ #

    def create_root(self, hypothesis: str = "genesis") -> ScenarioNode:
        """Create and register the root node."""
        root = ScenarioNode(
            simulation_id=self.simulation_id,
            parent_id=None,
            depth=0,
            hypothesis=hypothesis,
        )
        self._nodes[root.node_id] = root
        self._root_id = root.node_id
        return root

    def add_child(self, parent_id: str, hypothesis: str) -> ScenarioNode:
        """Add a child node under parent_id with the given hypothesis."""
        parent = self._nodes[parent_id]
        child = ScenarioNode(
            simulation_id=self.simulation_id,
            parent_id=parent_id,
            depth=parent.depth + 1,
            hypothesis=hypothesis,
        )
        self._nodes[child.node_id] = child
        parent.children.append(child.node_id)
        return child

    # ------------------------------------------------------------------ #
    # DFS traversal
    # ------------------------------------------------------------------ #

    def dfs(self) -> Iterator[ScenarioNode]:
        """Yield nodes in DFS order, skipping pruned branches."""
        if self._root_id is None:
            return
        yield from self._dfs_from(self._root_id)

    def _dfs_from(self, node_id: str) -> Iterator[ScenarioNode]:
        node = self._nodes[node_id]
        if node.status == NodeStatus.PRUNED:
            return
        yield node
        for child_id in node.children:
            yield from self._dfs_from(child_id)

    def next_pending(self) -> ScenarioNode | None:
        """Return the next PENDING node in DFS order, or None if done."""
        for node in self.dfs():
            if node.status == NodeStatus.PENDING:
                return node
        return None

    def is_leaf(self, node: ScenarioNode) -> bool:
        """True if this node is at max depth or has no children."""
        return node.depth >= self.max_depth

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #

    def get_node(self, node_id: str) -> ScenarioNode | None:
        return self._nodes.get(node_id)

    def node_count(self) -> int:
        return len(self._nodes)

    def complete_count(self) -> int:
        return sum(1 for n in self._nodes.values() if n.status == NodeStatus.COMPLETE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "max_depth": self.max_depth,
            "root_id": self._root_id,
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioTree":
        tree = cls(
            simulation_id=data["simulation_id"],
            max_depth=data["max_depth"],
        )
        tree._root_id = data.get("root_id")
        tree._nodes = {
            nid: ScenarioNode.from_dict(nd)
            for nid, nd in data.get("nodes", {}).items()
        }
        return tree
