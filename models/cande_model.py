"""
Main model class for CANDE Input File Editor.
"""
import re
from typing import Dict, List, Set, Tuple, Optional, cast
import logging
import math

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

    def select_elements_by_material(self, material, element_type_filter=None) -> int:
        """
        Select elements with the specified material number.

        Args:
            material: Material number to select
            element_type_filter: Filter for element types, can be None, a string, or a list of strings

        Returns:
            Number of elements selected
        """
        count = 0
        for element_id, element in self.elements.items():
            # Handle both single filter string and list of filter strings
            if isinstance(element_type_filter, list):
                # Check if the element matches any filter in the list
                matches_filter = False
                for filter_type in element_type_filter:
                    if self.element_matches_filter(element, filter_type):
                        matches_filter = True
                        break

                if not matches_filter:
                    continue
            elif not self.element_matches_filter(element, element_type_filter):
                continue

            if element.material == material:
                self.selected_elements.add(element_id)
                count += 1
        return count

    def select_elements_by_step(self, step, element_type_filter=None) -> int:
        """
        Select elements with the specified step number.

        Args:
            step: Step number to select
            element_type_filter: Filter for element types, can be None, a string, or a list of strings

        Returns:
            Number of elements selected
        """
        count = 0
        for element_id, element in self.elements.items():
            # Handle both single filter string and list of filter strings
            if isinstance(element_type_filter, list):
                # Check if the element matches any filter in the list
                matches_filter = False
                for filter_type in element_type_filter:
                    if self.element_matches_filter(element, filter_type):
                        matches_filter = True
                        break

                if not matches_filter:
                    continue
            elif not self.element_matches_filter(element, element_type_filter):
                continue

            if element.step == step:
                self.selected_elements.add(element_id)
                count += 1
        return count

    def update_elements(self, material=None, step=None, element_type_filter=None) -> int:
        """
        Update the material and/or step of selected elements.

        Args:
            material: New material number (optional)
            step: New step number (optional)
            element_type_filter: Filter for element types, can be None, a string, or a list of strings

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

            # Handle both single filter string and list of filter strings
            if isinstance(element_type_filter, list):
                # Check if the element matches any filter in the list
                matches_filter = False
                for filter_type in element_type_filter:
                    if self.element_matches_filter(element, filter_type):
                        matches_filter = True
                        break

                if not matches_filter:
                    continue
            elif not self.element_matches_filter(element, element_type_filter):
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

    def create_interfaces(self, selected_elements: Set[int], friction: float = 0.3) -> int:
        """
        Automatically creates interface elements between beam elements and 2D elements.

        Args:
            selected_elements: The elements for which to apply the operation
            friction: Friction coefficient for the interface elements

        Returns:
            Number of interface elements created
        """
        if not self.nodes or not self.elements:
            return 0

        # Calculate angles for all shared nodes in beam structures from selected elements
        # Find beam elements
        beam_elements = {
            element_id: element for element_id in selected_elements
            if isinstance(element:=self.elements[element_id], Element1D)
        }

        node_angles = self._calculate_interface_angles(beam_elements)

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

            # Get the angle for this node (or default to 0 if not calculated)
            angle = node_angles.get(node_id, 0.0)

            # Create interface element
            interface_element_id = max_element_id + 1
            max_element_id += 1

            self.elements[interface_element_id] = InterfaceElement(
                element_id=interface_element_id,
                nodes=[i_node_id, j_node_id, k_node_id],
                material=1,  # Default material
                step=1,  # Default step
                friction=friction,  # User specified friction
                angle=angle,  # Calculated angle
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
        # Track nodes used by interface elements
        interface_nodes = set()

        # Collect nodes by element type
        for element_id, element in self.elements.items():
            if isinstance(element, Element1D):
                # For beam elements, count the occurrences of each node
                for node_id in element.nodes:
                    beam_nodes[node_id] = beam_nodes.get(node_id, 0) + 1
            elif isinstance(element, Element2D):
                # For 2D elements, just track which nodes are used
                element2d_nodes.update(element.nodes)
            elif isinstance(element, InterfaceElement):
                # For interface elements, track the nodes they use
                interface_nodes.update(element.nodes)

        # Find nodes that are used by multiple beam elements AND by at least one 2D element
        # AND are not already used by an interface element
        shared_nodes = {
            node_id for node_id, count in beam_nodes.items()
            if count >= 2 and node_id in element2d_nodes and node_id not in interface_nodes
        }

        # Log what we found for debugging
        logger.info(f"Found {len(beam_nodes)} nodes used by beam elements")
        logger.info(f"Found {len(element2d_nodes)} nodes used by 2D elements")
        logger.info(f"Found {len(interface_nodes)} nodes used by interface elements")
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

    def _calculate_interface_angles(self, beam_collection: Optional[Dict[int, Element1D]] = None) -> Dict[int, float]:
        """
        Calculate interface angles for shared nodes in beam structures.

        This method traces each continuous beam structure to determine the
        appropriate angle for interface elements at shared nodes. It starts
        at the beginning of each structure and follows through to the end.

        Args:
            beam_collection: Collection of beam elements to process, or None to use all 1D elements

        Returns:
            Dictionary mapping node IDs to calculated angles (in degrees)
        """
        # Use all 1D elements if no collection is provided
        if beam_collection is None:
            beam_dict = {
                element_id: element for element_id, element in self.elements.items()
                if isinstance(element, Element1D)
            }

        # Make a copy to avoid modifying the original collection
        remaining_beams = beam_collection.copy()

        # Dictionary to store node ID -> angle mappings
        node_angles = {}

        # Process structures until all beams are processed
        while remaining_beams:
            # Pick the first beam to start with
            start_element_id = next(iter(remaining_beams))
            start_element = remaining_beams[start_element_id]

            # Find the beginning node of this structure
            start_node_id, structure_beams = self._find_structure_start(start_element, remaining_beams)

            # Calculate angles for all nodes in this structure
            structure_angles = self._calculate_structure_angles(start_node_id, structure_beams)

            # Add to the overall angles dictionary
            node_angles.update(structure_angles)

            # Remove processed beams from the remaining collection
            for beam_id in structure_beams:
                if beam_id in remaining_beams:
                    del remaining_beams[beam_id]

        return node_angles

    def _find_structure_start(self, start_element,
                              beam_collection: Dict[int, Element1D]) -> Tuple[int, Dict[int, Element1D]]:
        """
        Find the starting node of a beam structure.

        This method traces a structure to find its beginning node, which is either
        a node that only appears in one beam (a terminal node) or, if the structure
        is continuous (forms a loop), an arbitrary node in the structure.

        Args:
            start_element: The element to start tracing from
            beam_collection: Collection of available beam elements

        Returns:
            Tuple of (starting_node_id, structure_beams_dict)
        """
        # Dictionary to keep track of which beams are part of this structure
        structure_beams = {start_element.element_id: start_element}

        # Count node occurrences in all beams in the collection
        node_occurrences = {}
        for element_id, element in beam_collection.items():
            for node_id in element.nodes:
                node_occurrences[node_id] = node_occurrences.get(node_id, 0) + 1

        # Check if the start element has a terminal node (appears only once)
        for node_id in start_element.nodes:
            if node_occurrences.get(node_id, 0) == 1:
                # Found a terminal node, use it as start
                return node_id, structure_beams

        # No terminal node found in the start element, trace the structure
        # to find a terminal node elsewhere or determine it's a loop

        # Start from first node in the element
        current_node_id = start_element.nodes[0]
        current_element = start_element
        visited_nodes = set()

        while True:
            visited_nodes.add(current_node_id)

            # Find the next node and element in the structure
            next_node_id, next_element = self._find_next_node_and_element(
                current_node_id, current_element, beam_collection, structure_beams
            )

            if next_node_id is None:
                # Reached a terminal node, this is our start
                return current_node_id, structure_beams

            if next_node_id in visited_nodes:
                # We've found a loop, use the original node as start
                return start_element.nodes[0], structure_beams

            # Continue tracing
            current_node_id = next_node_id
            current_element = next_element
            structure_beams[current_element.element_id] = current_element

    def _find_next_node_and_element(self, current_node_id, current_element,
                                    beam_collection, structure_beams) -> Tuple[Optional[int], Optional[Element1D]]:
        """
        Find the next node and element in a beam structure.

        Args:
            current_node_id: Current node being processed
            current_element: Current beam element
            beam_collection: All available beam elements
            structure_beams: Elements already identified as part of this structure

        Returns:
            Tuple of (next_node_id, next_element) or (None, None) if at a terminal node
        """
        # Get the other node in the current element
        other_node_id = None
        for node_id in current_element.nodes:
            if node_id != current_node_id:
                other_node_id = node_id
                break

        if other_node_id is None:
            return None, None  # This shouldn't happen with valid beam elements

        # Find elements that use this other node (excluding the current element)
        connected_elements = []
        for element_id, element in beam_collection.items():
            if (element_id != current_element.element_id and
                    other_node_id in element.nodes and
                    element_id not in structure_beams):
                connected_elements.append(element)

        if not connected_elements:
            # No other elements connect to this node, it's a terminal node
            return None, None

        # Take the first connected element
        next_element = connected_elements[0]

        # Get the next node (the one that's not the shared node)
        next_node_id = None
        for node_id in next_element.nodes:
            if node_id != other_node_id:
                next_node_id = node_id
                break

        return next_node_id, next_element

    def _calculate_structure_angles(self, start_node_id, structure_beams) -> Dict[int, float]:
        """
        Calculate interface angles for all shared nodes in a beam structure.

        This method traces through a structure starting from the beginning node
        and calculates appropriate angles for each shared node.

        Args:
            start_node_id: Starting node ID for the structure
            structure_beams: Dictionary of beam elements in this structure

        Returns:
            Dictionary mapping node IDs to angles
        """
        node_angles = {}

        # Create a graph representation of the structure
        graph = {}
        for element in structure_beams.values():
            n1, n2 = element.nodes
            if n1 not in graph:
                graph[n1] = []
            if n2 not in graph:
                graph[n2] = []
            graph[n1].append(n2)
            graph[n2].append(n1)

        # Find all shared nodes (nodes that appear in multiple beams)
        shared_nodes = set()
        for node_id, neighbors in graph.items():
            if len(neighbors) >= 2:
                shared_nodes.add(node_id)

        # Calculate angle for each shared node
        for node_id in shared_nodes:
            if node_id not in self.nodes:
                continue

            current_node = self.nodes[node_id]
            neighbors = graph[node_id]

            # Get coordinates of all neighboring nodes
            neighbor_coords = []
            for neighbor_id in neighbors:
                if neighbor_id in self.nodes:
                    neighbor_node = self.nodes[neighbor_id]
                    neighbor_coords.append((neighbor_node.x, neighbor_node.y))

            if not neighbor_coords:
                continue

            # Calculate tangent direction
            sum_dx = 0.0
            sum_dy = 0.0

            for nx, ny in neighbor_coords:
                # Vector from current node to neighbor
                dx = nx - current_node.x
                dy = ny - current_node.y

                # Normalize the vector
                length = math.sqrt(dx ** 2 + dy ** 2)
                if length > 0:
                    sum_dx += dx / length
                    sum_dy += dy / length

            # Average tangent direction
            tangent_magnitude = math.sqrt(sum_dx ** 2 + sum_dy ** 2)
            if tangent_magnitude > 0:
                # Normalize tangent vector
                tangent_dx = sum_dx / tangent_magnitude
                tangent_dy = sum_dy / tangent_magnitude

                # Calculate tangent angle (in radians)
                tangent_angle = math.atan2(tangent_dy, tangent_dx)

                # Calculate normal angle (perpendicular to tangent)
                normal_angle = math.degrees(tangent_angle) + 90.0

                # Normalize to 0-360 range
                while normal_angle < 0:
                    normal_angle += 360.0
                while normal_angle >= 360.0:
                    normal_angle -= 360.0

                # Store the angle
                node_angles[node_id] = normal_angle

        return node_angles

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
