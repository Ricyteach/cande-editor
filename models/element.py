"""
Element models for CANDE Input File Editor.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class BaseElement:
    """Base class for CANDE elements."""
    element_id: int
    nodes: List[int]  # List of node IDs
    material: int
    step: int
    line_number: int
    line_content: str

    def __post_init__(self):
        """Validate element data after initialization."""
        if not isinstance(self.element_id, int) or self.element_id <= 0:
            raise ValueError("Element ID must be a positive integer")
        if not isinstance(self.nodes, list) or len(self.nodes) < 2:
            raise ValueError("Element must have at least 2 nodes")
        if not all(isinstance(node_id, int) and node_id > 0 for node_id in self.nodes):
            raise ValueError("Node IDs must be positive integers")
        if not isinstance(self.material, int) or self.material <= 0:
            raise ValueError("Material number must be a positive integer")
        if not isinstance(self.step, int) or self.step <= 0:
            raise ValueError("Step number must be a positive integer")


@dataclass
class Element(BaseElement):
    """Represents an element in the CANDE model."""
    node_count: int  # 2 for beams, 3 for triangles, 4 for quads

    def __post_init__(self):
        """Validate element data after initialization."""
        super().__post_init__()
        if not isinstance(self.node_count, int) or self.node_count < 2 or self.node_count > 4:
            raise ValueError("Node count must be between 2 and 4")
        if len(self.nodes) != self.node_count:
            raise ValueError(f"Expected {self.node_count} nodes, got {len(self.nodes)}")


@dataclass
class Element1D(BaseElement):
    """Represents a 1D element in the CANDE model."""
    # Add any 2D-specific attributes here as needed
    pass


@dataclass
class Element2D(BaseElement):
    """Represents a 2D element in the CANDE model."""
    # Add any 2D-specific attributes here as needed
    pass
