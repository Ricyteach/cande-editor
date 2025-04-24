"""
Main model class for CANDE Input File Editor.
"""
import re
from typing import Dict, List, Set, Tuple, Optional, cast
import logging

from models.node import Node
from models.element import BaseElement, Element, Element1D, Element2D
from utils.constants import (
    MATERIAL_START_POS, MATERIAL_END_POS, MATERIAL_FIELD_WIDTH,
    STEP_START_POS, STEP_END_POS, STEP_FIELD_WIDTH
)

# Configure logging
logger = logging.getLogger(__name__)

ELEMENT_TYPE_DICT = {
    2: Element1D,
    3: Element2D,
    4: Element2D,  # 4-node elements are also 2D elements
}


class CandeModel:
    """Model class that handles CANDE data and operations."""

    def __init__(self) -> None:
        """Initialize the CANDE model."""
        self.filepath: Optional[str] = None
        self.nodes: Dict[int, Node] = {}
        self.elements: Dict[int, BaseElement] = {}
        self.selected_elements: Set[int] = set()
        self.file_content: List[str] = []

        # Model dimensions
        self.model_min_x: float = 0.0
        self.model_min_y: float = 0.0
        self.model_max_x: float = 0.0
        self.model_max_y: float = 0.0

        # Material/step max values for color mapping
        self.max_material: int = 1
        self.max_step: int = 1

    def load_file(self, filepath: str) -> bool:
        """
        Load and parse a CANDE input file.

        Args:
            filepath: Path to the CANDE input file

        Returns:
            True if file was loaded successfully, False otherwise
        """
        try:
            with open(filepath, 'r') as file:
                self.file_content = file.readlines()

            self.filepath = filepath
            self.parse_cande_file()
            self.calculate_model_extents()
            self.selected_elements.clear()
            logger.info(f"Successfully loaded {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error loading file: {str(e)}")
            return False

    def parse_cande_file(self) -> None:
        """Parse the CANDE input file to extract nodes and elements."""
        self.nodes.clear()
        self.elements.clear()

        # More general patterns to catch nodes and elements
        # Node pattern - match any line with node ID followed by X and Y coordinates
        node_pattern = re.compile(r'^\s*C-3\.L3!![ L]+(\d+)\s+\w+\s+(-?[\d\.]+)\s+(-?[\d\.]+)')

        # Element pattern - more flexible to catch all element types
        # Look for lines that have the C-4.L3!! marker (or similar) and extract all numbers
        element_pattern = re.compile(r'^\s*C-4\.L3!![ L]+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)')

        for line_num, line in enumerate(self.file_content):
            # Check if this is a node line
            node_match = node_pattern.match(line)
            if node_match:
                node_id = int(node_match.group(1))
                x = float(node_match.group(2))
                y = float(node_match.group(3))

                self.nodes[node_id] = Node(
                    node_id=node_id,
                    x=x,
                    y=y,
                    line_number=line_num,
                    line_content=line
                )
                continue

            # Check if this is an element line
            element_match = element_pattern.match(line)
            if element_match:
                element_id = int(element_match.group(1))
                node1 = int(element_match.group(2))
                node2 = int(element_match.group(3))
                node3 = int(element_match.group(4))
                node4 = int(element_match.group(5))
                material = int(element_match.group(6))
                step = int(element_match.group(7))

                # Count actual nodes (non-zero)
                node_ids = [n for n in [node1, node2, node3, node4] if n != 0]
                node_count = len(node_ids)

                # Create appropriate element type based on node count
                # Now include 1D (2-node) elements
                if node_count in ELEMENT_TYPE_DICT:
                    element_type = ELEMENT_TYPE_DICT[node_count]
                    self.elements[element_id] = element_type(
                        element_id=element_id,
                        nodes=node_ids,
                        material=material,
                        step=step,
                        line_number=line_num,
                        line_content=line,
                    )

                    # Update max material and step numbers
                    self.max_material = max(self.max_material, material)
                    self.max_step = max(self.max_step, step)

        logger.info(f"Loaded {len(self.nodes)} nodes and {len(self.elements)} elements")

    def calculate_model_extents(self) -> None:
        """Calculate the extents of the model for zooming."""
        if not self.nodes:
            return

        # Initialize with the first node
        first_node = next(iter(self.nodes.values()))
        self.model_min_x = first_node.x
        self.model_max_x = first_node.x
        self.model_min_y = first_node.y
        self.model_max_y = first_node.y

        # Check all nodes
        for node in self.nodes.values():
            self.model_min_x = min(self.model_min_x, node.x)
            self.model_max_x = max(self.model_max_x, node.x)
            self.model_min_y = min(self.model_min_y, node.y)
            self.model_max_y = max(self.model_max_y, node.y)

    def save_file(self, save_path: str) -> bool:
        """
        Save the modified CANDE input file.

        Args:
            save_path: Path to save the file to

        Returns:
            True if file was saved successfully, False otherwise
        """
        if not self.file_content:
            logger.warning("No file content to save")
            return False

        try:
            with open(save_path, 'w') as file:
                file.writelines(self.file_content)

            logger.info(f"File saved successfully to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return False

    def select_elements_by_material(self, material: int) -> int:
        """
        Select elements with the specified material number.

        Args:
            material: Material number to select

        Returns:
            Number of elements selected
        """
        count = 0
        for element_id, element in self.elements.items():
            if element.material == material:
                self.selected_elements.add(element_id)
                count += 1
        return count

    def select_elements_by_step(self, step: int) -> int:
        """
        Select elements with the specified step number.

        Args:
            step: Step number to select

        Returns:
            Number of elements selected
        """
        count = 0
        for element_id, element in self.elements.items():
            if element.step == step:
                self.selected_elements.add(element_id)
                count += 1
        return count

    def select_elements_by_type(self, element_type: str) -> int:
        """
        Select elements by their type.

        Args:
            element_type: Type of element to select ("1D" or "2D")

        Returns:
            Number of elements selected
        """
        count = 0
        for element_id, element in self.elements.items():
            if (element_type == "1D" and isinstance(element, Element1D)) or \
                    (element_type == "2D" and isinstance(element, Element2D)):
                self.selected_elements.add(element_id)
                count += 1
        return count

    def update_elements(self, material: Optional[int] = None, step: Optional[int] = None) -> None:
        """
        Update the material and/or step of selected elements.

        Args:
            material: New material number (optional)
            step: New step number (optional)
        """
        if not self.file_content:
            logger.warning("No file content to update")
            return

        for element_id in self.selected_elements:
            element = self.elements.get(element_id)
            if not element:
                continue

            # Update element in memory
            if material is not None:
                element.material = material
            if step is not None:
                element.step = step

            # Get the line to modify
            line = self.file_content[element.line_number]

            # For CANDE input files, we need to preserve the exact format
            # The materials and steps are at positions defined by global constants

            # Material field
            if material is not None:
                # Right-align within the field width
                material_str = str(material).rjust(MATERIAL_FIELD_WIDTH)
                # Make sure we have the right length field
                if len(material_str) > MATERIAL_FIELD_WIDTH:
                    material_str = material_str[-MATERIAL_FIELD_WIDTH:]  # Take only last chars if too long

                # Get the parts before and after the field we're modifying
                prefix = line[:MATERIAL_START_POS] if len(line) > MATERIAL_START_POS else line
                # Make sure we don't go past the end of the line
                suffix = line[MATERIAL_END_POS:] if len(line) > MATERIAL_END_POS else ""
                line = prefix + material_str + suffix

            # Step field
            if step is not None:
                # Right-align within the field width
                step_str = str(step).rjust(STEP_FIELD_WIDTH)
                # Make sure we have the right length field
                if len(step_str) > STEP_FIELD_WIDTH:
                    step_str = step_str[-STEP_FIELD_WIDTH:]  # Take only last chars if too long

                # Get the parts before and after the field we're modifying
                prefix = line[:STEP_START_POS] if len(line) > STEP_START_POS else line
                # Make sure we don't go past the end of the line
                suffix = line[STEP_END_POS:] if len(line) > STEP_END_POS else ""
                line = prefix + step_str + suffix

            # Update the line in the file
            self.file_content[element.line_number] = line
            element.line_content = line

    def clear_selection(self) -> None:
        """Clear the current element selection."""
        self.selected_elements.clear()
