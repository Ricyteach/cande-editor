"""
Node model for CANDE Input File Editor.
"""
from dataclasses import dataclass


@dataclass
class Node:
    """Represents a node in the CANDE model."""
    node_id: int
    x: float
    y: float
    line_number: int
    line_content: str

    def __post_init__(self):
        """Validate node data after initialization."""
        if not isinstance(self.node_id, int) or self.node_id <= 0:
            raise ValueError("Node ID must be a positive integer")
        if not isinstance(self.x, (int, float)):
            raise ValueError("X coordinate must be a number")
        if not isinstance(self.y, (int, float)):
            raise ValueError("Y coordinate must be a number")
