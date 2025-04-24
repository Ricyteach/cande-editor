"""
Main model class for CANDE Input File Editor.
"""
import re
from typing import Dict, List, Set, Tuple, Optional, cast
import logging

from models.node import Node
from models.element import BaseElement, Element, Element1D, Element2D, InterfaceElement
from utils.constants import (
    MATERIAL_START_POS, MATERIAL_END_POS, MATERIAL_FIELD_WIDTH,
    STEP_START_POS, STEP_END_POS, STEP_FIELD_WIDTH
)

# Configure logging
logger = logging.getLogger(__name__)

ELEMENT_CLASS_DICT = {
    0: None,  # Default element type (not needed but for clarity)
    1: InterfaceElement,  # Interface elements
}

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
        element_pattern = re.compile(r'^\s*C-4\.L3!![ L]+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?')

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
                element_class = int(element_match.group(8))

                # Count actual nodes (non-zero)
                node_ids = [n for n in [node1, node2, node3, node4] if n != 0]
                node_count = len(node_ids)

                # Create appropriate element type based on element class and node count
                # Now include 1D (2-node) elements and interface elements
                if ELEMENT_CLASS_DICT[element_class] is InterfaceElement:
                    element_type = InterfaceElement
                elif node_count in ELEMENT_TYPE_DICT:
                    element_type = ELEMENT_TYPE_DICT[node_count]
                else:
                    logger.warning(
                        f"Unknown element type: ID={element_id}, node_count={node_count}, class={element_class}")
                    continue  # Skip this element

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
        Save the modified CANDE input file with any new nodes and interface elements.

        Args:
            save_path: Path to save the file to

        Returns:
            True if file was saved successfully, False otherwise
        """
        if not self.file_content:
            return False

        # Copy file content for modification
        new_file_content = list(self.file_content)

        # Add new nodes (those with line_number == -1)
        new_node_lines = []
        for node_id, node in self.nodes.items():
            if node.line_number == -1:
                # Generate node line in CANDE format
                node_line = self._generate_node_line(node)
                new_node_lines.append(node_line)

        # Add new elements (those with line_number == -1)
        new_element_lines = []
        for element_id, element in self.elements.items():
            if element.line_number == -1:
                # Generate element line in CANDE format
                element_line = self._generate_element_line(element)
                new_element_lines.append(element_line)

        # Find appropriate insertion points and insert the new lines
        if new_node_lines or new_element_lines:
            # Find the last node line to determine where to insert new nodes
            # Note the last node line is supposed to have "L" directly after "!!"
            last_node_line = -1
            node_pattern = re.compile(r'^\s*C-3\.L3!!L')

            # Find the last element line to determine where to insert new elements
            # Note the last element line is supposed to have "L" directly after "!!"
            last_element_line = -1
            element_pattern = re.compile(r'^\s*C-4\.L3!!L')

            for i, line in enumerate(new_file_content):
                if node_pattern.match(line):
                    last_node_line = i
                    continue
                if element_pattern.match(line):
                    last_element_line = i
                    break

            # Insert new nodes after the last node line
            if new_node_lines and last_node_line >= 0:
                # remove "!!L" from previous last node line and replace with "!! "
                new_file_content[last_node_line] = new_file_content[last_node_line].replace('!!L', '!! ')
                for i, line in enumerate(new_node_lines):
                    new_file_content.insert(last_node_line + 1 + i, line)
                else:
                    # Update the last element line index since we inserted nodes
                    last_element_line += len(new_node_lines)
                    # also remove "!! " from last line and replace with "!!L"
                    new_file_content[last_node_line + len(new_node_lines)] = (
                        new_file_content[last_node_line + len(new_node_lines)].replace('!! ', '!!L')
                    )

            # Insert new elements after the last element line
            if new_element_lines and last_element_line >= 0:
                # remove "!!L" from previous last element line and replace with "!! "
                new_file_content[last_element_line] = new_file_content[last_element_line].replace('!!L', '!! ')
                for i, line in enumerate(new_element_lines):
                    new_file_content.insert(last_element_line + 1 + i, line)

                # Remove "!! " from last line and replace with "!!L" since we inserted elements
                new_file_content[last_element_line + len(new_element_lines)] = (
                    new_file_content[last_element_line + len(new_element_lines)].replace('!! ', '!!L')
                )

        # Save the modified content
        try:
            with open(save_path, 'w') as file:
                file.writelines(new_file_content)
            return True
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return False

    def element_matches_filter(self, element: BaseElement, element_type_filter: Optional[str]) -> bool:
        """
        Check if an element matches the current type filter.

        Args:
            element: The element to check
            element_type_filter: The current element type filter ("1D", "2D", "Interface", or None)

        Returns:
            True if the element matches the filter or if there is no filter
        """
        if element_type_filter is None:
            return True
        elif element_type_filter == "1D" and isinstance(element, Element1D):
            return True
        elif element_type_filter == "2D" and isinstance(element, Element2D):
            return True
        elif element_type_filter == "Interface" and isinstance(element, InterfaceElement):
            return True
        return False

    def select_elements_by_material(self, material: int, element_type_filter: Optional[str] = None) -> int:
        """
        Select elements with the specified material number.

        Args:
            material: Material number to select
            element_type_filter: Optional filter for element type ("1D", "2D", or None)

        Returns:
            Number of elements selected
        """
        count = 0
        for element_id, element in self.elements.items():
            # Skip elements that don't match the filter
            if not self.element_matches_filter(element, element_type_filter):
                continue

            if element.material == material:
                self.selected_elements.add(element_id)
                count += 1
        return count

    def select_elements_by_step(self, step: int, element_type_filter: Optional[str] = None) -> int:
        """
        Select elements with the specified step number.

        Args:
            step: Step number to select
            element_type_filter: Optional filter for element type ("1D", "2D", or None)

        Returns:
            Number of elements selected
        """
        count = 0
        for element_id, element in self.elements.items():
            # Skip elements that don't match the filter
            if not self.element_matches_filter(element, element_type_filter):
                continue

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

    def update_elements(self, material: Optional[int] = None, step: Optional[int] = None,
                        element_type_filter: Optional[str] = None) -> int:
        """
        Update the material and/or step of selected elements.

        Args:
            material: New material number (optional)
            step: New step number (optional)
            element_type_filter: Optional filter for element type ("1D", "2D", or None)

        Returns:
            Number of elements updated
        """
        if not self.file_content:
            logger.warning("No file content to update")
            return 0

        updated_count = 0

        for element_id in self.selected_elements:
            element = self.elements.get(element_id)
            if not element:
                continue

            # Skip elements that don't match the filter
            if not self.element_matches_filter(element, element_type_filter):
                continue

            # Update element in memory
            if material is not None:
                element.material = material
            if step is not None:
                element.step = step

            updated_count += 1

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

        return updated_count

    def create_interfaces(self) -> int:
        """
        Automatically creates interface elements between beam elements and 2D elements.

        Returns:
            Number of interface elements created
        """
        if not self.nodes or not self.elements:
            return 0

        # Find nodes shared between beam elements (that are also shared by 2D elements)
        shared_nodes = self._find_shared_beam_nodes()

        # Track new nodes and elements created
        interface_count = 0
        max_node_id = max(self.nodes.keys()) if self.nodes else 0
        max_element_id = max(self.elements.keys()) if self.elements else 0

        # For each shared node
        for node_id in shared_nodes:
            # Create new I (inside) node
            i_node_id = max_node_id + 1
            max_node_id += 1

            # Create new K (dummy) node with ID > both I and J
            k_node_id = max_node_id + 1
            max_node_id += 1

            # Original node becomes J (outside)
            j_node_id = node_id

            # Copy coordinates from original node
            original_node = self.nodes[node_id]

            # Create new nodes with same coordinates
            self.nodes[i_node_id] = Node(
                node_id=i_node_id,
                x=original_node.x,
                y=original_node.y,
                line_number=-1,  # Will be assigned when saving
                line_content=""  # Will be generated when saving
            )

            self.nodes[k_node_id] = Node(
                node_id=k_node_id,
                x=original_node.x,
                y=original_node.y,
                line_number=-1,
                line_content=""
            )

            # Create interface element
            interface_element_id = max_element_id + 1
            max_element_id += 1

            self.elements[interface_element_id] = InterfaceElement(
                element_id=interface_element_id,
                nodes=[i_node_id, j_node_id, k_node_id],
                material=1,  # Default material
                step=1,  # Default step
                line_number=-1,
                line_content=""
            )

            interface_count += 1

            # Update beam elements to use the new I node instead of original
            self._update_beam_elements_for_interface(node_id, i_node_id)

        return interface_count

    def _find_shared_beam_nodes(self) -> Set[int]:
        """
        Find nodes that are shared between multiple beam elements and also connected to 2D elements.

        Returns:
            Set of node IDs that are eligible for interface creation
        """
        # Track nodes used by beam elements
        beam_nodes = {}
        # Track nodes used by 2D elements
        element2d_nodes = set()

        # Collect nodes by element type
        for element_id, element in self.elements.items():
            if isinstance(element, Element1D):
                # For beam elements, count the occurrences of each node
                for node_id in element.nodes:
                    beam_nodes[node_id] = beam_nodes.get(node_id, 0) + 1
            elif isinstance(element, Element2D):
                # For 2D elements, just track which nodes are used
                element2d_nodes.update(element.nodes)

        # Find nodes that are used by multiple beam elements AND by at least one 2D element
        shared_nodes = {
            node_id for node_id, count in beam_nodes.items()
            if count >= 2 and node_id in element2d_nodes
        }

        # Log what we found for debugging
        logger.info(f"Found {len(beam_nodes)} nodes used by beam elements")
        logger.info(f"Found {len(element2d_nodes)} nodes used by 2D elements")
        logger.info(f"Found {len(shared_nodes)} nodes shared between beam elements and 2D elements")

        return shared_nodes

    def _update_beam_elements_for_interface(self, old_node_id: int, new_node_id: int) -> None:
        """
        Update beam elements to use the new inside node instead of the original shared node.

        Args:
            old_node_id: Original node ID
            new_node_id: New inside node ID
        """
        for element_id, element in self.elements.items():
            if isinstance(element, Element1D):
                # Check if the element uses the old node
                if old_node_id in element.nodes:
                    # Replace the old node with the new one
                    new_nodes = [new_node_id if n == old_node_id else n for n in element.nodes]
                    element.nodes = new_nodes

    def clear_selection(self) -> None:
        """Clear the current element selection."""
        self.selected_elements.clear()

    def _generate_node_line(self, node: Node) -> str:
        """
        Generate a CANDE node line for a new node.

        Args:
            node: The node to generate a line for

        Returns:
            CANDE format node line
        """
        # Format for C-3.L3!! node line (following the pattern in existing file)
        # Adjust format based on your CANDE file format
        return f"                   C-3.L3!! {node.node_id:4d}  000{node.x:10.3f}{node.y:10.3f}\n"

    def _generate_element_line(self, element: BaseElement) -> str:
        """
        Generate a CANDE element line for a new element.

        Args:
            element: The element to generate a line for

        Returns:
            CANDE format element line
        """
        # Get element type code
        element_type = 0
        if isinstance(element, InterfaceElement):
            element_type = 1

        # Get up to 4 node IDs, using 0 for missing nodes
        node_ids = element.nodes + [0] * (4 - len(element.nodes))

        # Format for C-4.L3!! element line
        # Adjust format based on your CANDE file format
        return (f"                   C-4.L3!! {element.element_id:4d}{node_ids[0]:5d}{node_ids[1]:5d}{node_ids[2]:5d}"
                f"{node_ids[3]:5d}{element.material:5d}{element.step:5d}{element_type:5d}\n")
