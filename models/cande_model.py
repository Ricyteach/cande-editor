"""
Main model class for CANDE Input File Editor.
"""
import re
from typing import Dict, List, Set, Optional, Tuple
import logging
import math

from models.node import Node
from models.element import BaseElement, Element1D, Element2D, InterfaceElement
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
        node_pattern = re.compile(r'^\s*C-3\.L3!![ L]+(\d+)\s+\w+\s+(-?[\d.]+)\s+(-?[\d.]+)')

        # Element pattern - more flexible to catch all element types
        # Look for lines that have the C-4.L3!! marker (or similar) and extract all numbers
        element_pattern = re.compile(
            r'^\s*C-4\.L3!![ L]+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?'
        )

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
                if isinstance(self.elements[element_id], Element2D):
                    self.ensure_valid_2d_element_ordering(self.elements[element_id])
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
        Save the modified CANDE input file with any new nodes, interface elements,
        and interface materials.

        Args:
            save_path: Path to save the file to

        Returns:
            True if file was saved successfully, False otherwise
        """
        if not self.file_content:
            return False

        # Copy file content for modification
        new_file_content = list(self.file_content)

        # Update existing elements' node references
        for element_id, element in self.elements.items():
            if element.line_number >= 0:  # Only update existing elements in the file
                # Check if we need to update the line (compare with original content)
                original_line = self.file_content[element.line_number]
                if original_line != element.line_content:
                    # Generate updated element line
                    pattern = re.compile(
                        r'^\s*C-4\.L3!![ L]+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?')
                    match = pattern.match(original_line)

                    if match:
                        # Extract element ID (group 1) and everything after the node IDs
                        element_id = match.group(1)
                        last_part = original_line[match.end(5):]  # Everything after last node ID

                        # Get up to 4 node IDs, using 0 for missing nodes
                        node_ids = element.nodes + [0] * (4 - len(element.nodes))

                        # Reconstruct the line with properly formatted element ID and node IDs
                        # This ensures consistent spacing regardless of what was in the original line
                        updated_line = f"                   C-4.L3!! {int(element_id):4d}"
                        for i, node_id in enumerate(node_ids):
                            updated_line += f"{node_id:5d}"
                        updated_line += last_part

                        # Update the line in the file content
                        new_file_content[element.line_number] = updated_line
                        element.line_content = updated_line

        # Add new nodes (those with line_number == -1)
        new_node_lines = []
        for node_id, node in self.nodes.items():
            if node.line_number == -1:
                # Generate node line in CANDE format
                node_line = self._generate_node_line(node)
                new_node_lines.append(node_line)

        # Find all interface elements in geometric order
        interface_elements = []
        for element_id, element in sorted(self.elements.items()):
            if isinstance(element, InterfaceElement) and element.line_number == -1:
                interface_elements.append((element_id, element))

        # Add new elements (including interface elements in geometric order)
        new_element_lines = []
        for element_id, element in self.elements.items():
            if element.line_number == -1 and not isinstance(element, InterfaceElement):
                # Generate element line in CANDE format (non-interface elements)
                element_line = self._generate_element_line(element)
                new_element_lines.append(element_line)

        # Interface material handling is similar to existing code, but ensures ordering is preserved
        interface_materials = {}  # Maps material_id to (friction, angle)
        interface_material_mapping = {}  # Maps element_id to material_id

        # Assign material numbers to interface elements in geometric order
        next_material_id = 1
        for element_id, element in interface_elements:
            # Create a unique material for each interface element to preserve ordering
            material_id = next_material_id
            interface_materials[material_id] = (element.friction, element.angle)
            next_material_id += 1

            # Map this element to the material and update element immediately
            interface_material_mapping[element_id] = material_id
            element.material = material_id  # Update material number in memory immediately

        # Generate D-1 and D-2 lines for interface materials
        interface_material_lines = []
        for i, (material_id, (friction, angle)) in enumerate(sorted(interface_materials.items())):
            # For the last material, use "L" in the first field, otherwise use " "
            is_last = (i == len(interface_materials) - 1)
            first_field = "L" if is_last else " "

            # Material name: "Inter #X" where X is the material ID
            material_name = f"Inter #{material_id}"

            # D-1 line
            d1_line = (f"                      D-1!!{first_field}{material_id:4d}{6:5d}"
                       f"{0:10d}{material_name:>20s}\n")

            # D-2 line
            d2_line = f"            D-2.Interface!!{angle:10.3f}{friction:10.3f}\n"

            interface_material_lines.append(d1_line)
            interface_material_lines.append(d2_line)

        # Update existing interface elements in the file with new material IDs
        for element_id, material_id in interface_material_mapping.items():
            if element_id in self.elements:
                element = self.elements[element_id]
                # Element material is already updated in memory above

                # If the element exists in the file already, update its line content
                if element.line_number >= 0:
                    # Update the material field in the file line
                    line = self.file_content[element.line_number]

                    # Right-align material number within the field width
                    material_str = str(material_id).rjust(MATERIAL_FIELD_WIDTH)
                    if len(material_str) > MATERIAL_FIELD_WIDTH:
                        material_str = material_str[-MATERIAL_FIELD_WIDTH:]  # Take only last chars if too long

                    # Get parts before and after the field we're modifying
                    prefix = line[:MATERIAL_START_POS] if len(line) > MATERIAL_START_POS else line
                    suffix = line[MATERIAL_END_POS:] if len(line) > MATERIAL_END_POS else ""

                    # Update the line
                    new_line = prefix + material_str + suffix
                    new_file_content[element.line_number] = new_line
                    element.line_content = new_line

        # Now add interface elements in geometric order (with their updated material numbers)
        for element_id, element in interface_elements:
            element_line = self._generate_element_line(element)  # Uses updated element.material
            new_element_lines.append(element_line)

        # Find appropriate insertion points and insert the new content
        # First, find insertion points for nodes and elements
        if new_node_lines or new_element_lines:
            # Code to insert nodes and elements
            last_node_line = -1
            node_pattern = re.compile(r'^\s*C-3\.L3!!L')

            # Element handling code...
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
                # Remove "!!L" from previous last node line and replace with "!! "
                new_file_content[last_node_line] = new_file_content[last_node_line].replace('!!L', '!! ')
                for i, line in enumerate(new_node_lines):
                    new_file_content.insert(last_node_line + 1 + i, line)
                else:
                    # Update the last element line index since we inserted nodes
                    last_element_line += len(new_node_lines)
                    # Also remove "!! " from last line and replace with "!!L"
                    new_file_content[last_node_line + len(new_node_lines)] = (
                        new_file_content[last_node_line + len(new_node_lines)].replace('!! ', '!!L')
                    )

            # Insert new elements after the last element line
            if new_element_lines and last_element_line >= 0:
                # Remove "!!L" from previous last element line and replace with "!! "
                new_file_content[last_element_line] = new_file_content[last_element_line].replace('!!L', '!! ')
                for i, line in enumerate(new_element_lines):
                    new_file_content.insert(last_element_line + 1 + i, line)

                # Remove "!! " from last line and replace with "!!L" since we inserted elements
                new_file_content[last_element_line + len(new_element_lines)] = (
                    new_file_content[last_element_line + len(new_element_lines)].replace('!! ', '!!L')
                )

        # Now handle the interface material lines insertion
        if interface_material_lines:
            # Find where to insert the interface material lines
            insertion_index = -1

            # 1. Try to find existing "D-1!!" lines
            existing_d1_line = -1
            existing_d_pattern = re.compile(r'^\s*D-\d+.*!!.')  # Match any D line with a character after !!

            for i, line in enumerate(new_file_content):
                if "D-1!!" in line:
                    existing_d1_line = i

                # Find the last D-n line to insert after it
                if existing_d_pattern.match(line):
                    insertion_index = i

            # 2. If no D lines found, find C-5 lines
            if insertion_index < 0:
                c5_pattern = re.compile(r'^\s*C-5.*!!L')
                for i, line in enumerate(new_file_content):
                    if c5_pattern.match(line):
                        insertion_index = i
                        break

            # 3. If no C-5 lines, find the last C-4 line
            if insertion_index < 0:
                c4_pattern = re.compile(r'^\s*C-4.*!!L')
                for i, line in enumerate(new_file_content):
                    if c4_pattern.match(line):
                        insertion_index = i
                        break

            if insertion_index >= 0:
                # If we found existing D-1 lines, update the last one to remove the "L"
                if existing_d1_line >= 0:
                    # Find all D-1 lines
                    d1_lines = [i for i, line in enumerate(new_file_content) if "D-1!!" in line]
                    if d1_lines:
                        # Update the last D-1 line to remove the "L" if it exists
                        last_d1_line = d1_lines[-1]
                        new_file_content[last_d1_line] = new_file_content[last_d1_line].replace('!!L', '!! ')

                # Insert the interface material lines
                for i, line in enumerate(interface_material_lines):
                    new_file_content.insert(insertion_index + 1 + i, line)

        # Update the C-2 line with current counts before saving
        new_file_content = self._update_c2_line(new_file_content)

        # Save the modified content
        try:
            with open(save_path, 'w') as file:
                file.writelines(new_file_content)
            return True
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return False

    def _update_c2_line(self, file_content: List[str]) -> List[str]:
        """
        Update the C-2 line with current counts of nodes, elements, and materials.

        Args:
            file_content: The current file content

        Returns:
            Updated file content with modified C-2 line
        """
        # First, find the C-1 line
        c1_index = -1
        for i, line in enumerate(file_content):
            if "C-1.L3!!" in line:
                c1_index = i
                break

        if c1_index == -1 or c1_index + 1 >= len(file_content):
            # Could not find C-1 line or there's no line after it
            return file_content

        # Get the C-2 line (immediately after C-1)
        c2_index = c1_index + 1
        c2_line = file_content[c2_index]

        # Check if this is actually a C-2 line
        if "C-2.L3!!" not in c2_line:
            logger.warning(f"Expected C-2 line after C-1, found: {c2_line}")
            return file_content

        # Find the position right after "C-2.L3!!"
        prefix_match = re.search(r'C-2\.L3!!', c2_line)
        if not prefix_match:
            logger.warning(f"Could not identify C-2.L3!! marker in line: {c2_line}")
            return file_content

        prefix_end = prefix_match.end()
        prefix = c2_line[:prefix_end]

        # Extract fields with fixed width of 5 chars each
        remaining = c2_line[prefix_end:]
        field_width = 5
        fields = []

        # Extract as many 5-character fields as possible
        for i in range(0, len(remaining), field_width):
            if i + field_width <= len(remaining):
                field = remaining[i:i + field_width].strip()
                if field.isdigit():
                    fields.append(int(field))
                else:
                    fields.append(field)

        # We need at least 10 numeric fields (0-9)
        if len(fields) < 10:
            logger.warning(f"Not enough fields in C-2 line: {c2_line}")
            return file_content

        # Update the fields according to requirements
        # 0: max load steps
        max_step = max((element.step for element in self.elements.values()), default=1)
        fields[0] = max(fields[0], max_step)

        # 5: total number of nodes
        fields[5] = len(self.nodes)

        # 6: total number of elements
        fields[6] = len(self.elements)

        # 8: total number of soil materials
        soil_materials = max(
            (element.material for element_id, element in self.elements.items()
             if not isinstance(element, InterfaceElement)),
            default=0
        )
        fields[8] = max(fields[8], soil_materials)

        # 9: total number of interface materials
        interface_materials = max(
            (element.material for element_id, element in self.elements.items()
             if isinstance(element, InterfaceElement)),
            default=0
        )
        fields[9] = max(fields[9], interface_materials)

        # Reconstruct the C-2 line
        new_c2_line = prefix

        # Add each field with proper spacing (5 chars each, right-aligned)
        for field in fields:
            if isinstance(field, int):
                new_c2_line += f"{field:5d}"
            else:
                new_c2_line += f"{field:5s}"

        # CRITICAL: Preserve line ending
        # Check if the original line has a newline character
        if c2_line.endswith('\n'):
            new_c2_line += '\n'
        elif c2_line.endswith('\r\n'):
            new_c2_line += '\r\n'

        # Update the line in the file content
        file_content[c2_index] = new_c2_line

        return file_content

    # In CandeModel class, add a method to get color index for friction value

    def get_friction_color_index(self, friction: float) -> int:
        """
        Get a consistent color index for a friction value.

        Args:
            friction: The friction coefficient value

        Returns:
            An index into the CANDE_COLORS list
        """
        # Initialize friction color map if it doesn't exist
        if not hasattr(self, 'friction_color_map'):
            self.friction_color_map = {}

        # Round friction to 2 decimal places for consistent grouping
        rounded_friction = round(friction, 2)

        # If this friction value isn't in our map yet, add it
        if rounded_friction not in self.friction_color_map:
            # Assign the next available color index
            self.friction_color_map[rounded_friction] = len(self.friction_color_map)

        # Return the color index
        return self.friction_color_map[rounded_friction]

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

    def create_interfaces(self, selected_elements: Set[int] = None, friction: float = 0.3) -> Tuple[int, bool]:
        """
        Automatically creates interface elements between beam elements and 2D elements,
        avoiding creating duplicates where interfaces already exist.

        Args:
            selected_elements: The elements for which to apply the operation (required)
            friction: Friction coefficient for the interface elements

        Returns:
            Tuple of (number of interface elements created, all_nodes_have_interfaces flag)
        """
        if not self.nodes or not self.elements:
            return 0, False

        # Require a selection
        if selected_elements is None or len(selected_elements) == 0:
            return 0, False

        # Find beam elements FROM THE SELECTION
        beam_elements = {
            element_id: element for element_id in selected_elements
            if element_id in self.elements and isinstance(element := self.elements[element_id], Element1D)
        }

        # Only proceed if we have beam elements
        if not beam_elements:
            return 0, False

        # Find nodes shared between multiple beam elements and also connected to 2D elements
        shared_nodes = self._find_shared_beam_nodes()

        # First pass: identify all nodes that could potentially be shared
        all_shared_nodes = set()
        for element_id, element in beam_elements.items():
            for node_id in element.nodes:
                all_shared_nodes.add(node_id)

        # Filter to only include nodes that are actually shared between beams
        all_shared_nodes = {node_id for node_id in all_shared_nodes
                            if sum(1 for element in beam_elements.values()
                                   if node_id in element.nodes) > 1}

        logger.info(f"Found {len(all_shared_nodes)} total shared nodes between beam elements")
        logger.info(f"Found {len(shared_nodes)} eligible shared nodes for interfaces")

        # Check if we have any eligible nodes
        if not shared_nodes:
            if all_shared_nodes:
                # We found shared nodes, but they all have interfaces already
                logger.info("All shared nodes already have interfaces attached")
                return 0, True  # Return 0 and True to indicate no interfaces were created but all nodes have interfaces
            elif beam_elements:
                # We have beam elements, but no shared nodes were found
                logger.info("No shared nodes found in the selected beam elements")
                return 0, False
            else:
                # No beam elements selected
                logger.info("No beam elements found in the selection")
                return 0, False

        # Calculate angles
        node_angles = self._calculate_beam_angles(beam_elements)

        # Find connected beam chains to preserve geometric ordering
        beam_chains = self._find_beam_chains(beam_elements)

        # Track new nodes and elements created
        interface_count = 0
        max_node_id = max(self.nodes.keys()) if self.nodes else 0
        max_element_id = max(self.elements.keys()) if self.elements else 0

        # Process each beam chain to create interface elements in geometric order
        for chain in beam_chains:
            # Skip chains with only one beam (no shared nodes)
            if len(chain) <= 1:
                continue

            # Extract the shared nodes from the chain
            chain_shared_nodes = self._extract_shared_nodes_from_chain(chain, beam_elements)

            # Filter to only include nodes that are eligible for interfaces
            chain_shared_nodes = [node_id for node_id in chain_shared_nodes if node_id in shared_nodes]

            # For each shared node in the chain (in geometric order)
            for node_id in chain_shared_nodes:
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

                # Get the angle for this node (with default value of 0.0 if not found)
                angle = node_angles.get(node_id, 0.0)

                # Create interface element
                interface_element_id = max_element_id + 1
                max_element_id += 1

                self.elements[interface_element_id] = InterfaceElement(
                    element_id=interface_element_id,
                    nodes=[i_node_id, j_node_id, k_node_id],
                    material=1,  # Default material, will be updated by save_file
                    step=1,  # Default step
                    friction=friction,  # User specified friction
                    angle=angle,  # Calculated angle
                    line_number=-1,
                    line_content=""
                )

                interface_count += 1

                # Update beam elements to use the new I node instead of original
                # ONLY UPDATE BEAM ELEMENTS IN THE SELECTION
                self._update_beam_elements_for_interface(node_id, i_node_id, beam_elements.keys())

        # At the end, return the count of created interfaces and False since some nodes were eligible
        return interface_count, False

    def _find_shared_beam_nodes(self, beam_collection=None) -> Set[int]:
        """
        Find nodes that are shared between multiple beam elements and also connected to 2D elements,
        excluding nodes that already have interface elements.

        Args:
            beam_collection: Optional dictionary of beam elements to consider, if None uses all beams

        Returns:
            Set of node IDs that are eligible for interface creation
        """
        # Track nodes used by beam elements
        beam_nodes = {}

        # If no specific collection provided, use all beam elements
        if beam_collection is None:
            beam_elements = {
                element_id: element for element_id, element in self.elements.items()
                if isinstance(element, Element1D)
            }
        else:
            beam_elements = beam_collection

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
        logger.info(
            f"Found {len(shared_nodes)} nodes shared between beam elements and 2D elements that don't have interfaces")

        return shared_nodes

    def _update_beam_elements_for_interface(self, old_node_id: int, new_node_id: int,
                                            element_ids_to_update=None) -> None:
        """
        Update beam elements to use the new inside node instead of the original shared node.
        Enhanced version with better logging and validation.

        Args:
            old_node_id: Original node ID
            new_node_id: New inside node ID
            element_ids_to_update: Optional set of element IDs to update, if None updates all Elements
        """
        updated_count = 0
        updated_elements = []

        for element_id, element in self.elements.items():
            # Skip if not in the selection (if a selection is provided)
            if element_ids_to_update is not None and element_id not in element_ids_to_update:
                continue

            if isinstance(element, Element1D):
                # Check if the element uses the old node
                if old_node_id in element.nodes:
                    # Track previous state for logging
                    old_nodes = list(element.nodes)

                    # Replace the old node with the new one
                    new_nodes = [new_node_id if n == old_node_id else n for n in element.nodes]
                    element.nodes = new_nodes
                    updated_count += 1
                    updated_elements.append(element_id)

                    logger.info(f"Updated beam element {element_id}: replaced node {old_node_id} with {new_node_id}")

                    # If this is an existing element in the file, update its line_content
                    if element.line_number >= 0 and element.line_number < len(self.file_content):
                        original_line = self.file_content[element.line_number]

                        # Use regex to find the node IDs in the line
                        pattern = re.compile(
                            r'^\s*C-4\.L3!![ L]+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)(?:\s+(\d+))?')
                        match = pattern.match(original_line)

                        if match:
                            # Extract parts before and after the node IDs
                            first_part = original_line[:match.start(2)]  # Everything up to first node ID
                            last_part = original_line[match.end(5):]  # Everything after last node ID

                            # Get up to 4 node IDs, using 0 for missing nodes
                            node_ids = element.nodes + [0] * (4 - len(element.nodes))

                            # Reconstruct the line with updated node IDs
                            updated_line = first_part
                            for i, node_id in enumerate(node_ids):
                                updated_line += f"{node_id:5d}"
                            updated_line += last_part

                            # Update the line content in the element
                            element.line_content = updated_line

        logger.info(f"Updated {updated_count} beam elements to use new node {new_node_id}")
        if updated_elements:
            logger.info(f"Updated elements: {updated_elements}")

        # Verify none of the updated elements still use the old node
        verification_failed = []
        for element_id in updated_elements:
            element = self.elements[element_id]
            if old_node_id in element.nodes:
                verification_failed.append(element_id)

        if verification_failed:
            logger.error(f"Verification failed! Elements still using old node {old_node_id}: {verification_failed}")

    # Add this debugging method to help diagnose interface issues
    def dump_interface_info(self, filename="interface_debug.txt"):
        """
        Dumps detailed information about all interface elements to a file
        for debugging purposes.
        """
        try:
            with open(filename, 'w') as f:
                f.write("=== INTERFACE ELEMENT DEBUG INFO ===\n\n")

                # Track nodes with interfaces
                nodes_with_interfaces = set()

                # Find interface elements
                interface_elements = {}
                for element_id, element in self.elements.items():
                    if isinstance(element, InterfaceElement):
                        interface_elements[element_id] = element

                        # Track nodes used by interfaces
                        nodes_with_interfaces.update(element.nodes)

                f.write(f"Total interface elements: {len(interface_elements)}\n")
                f.write(f"Total nodes used by interfaces: {len(nodes_with_interfaces)}\n\n")

                # Group interfaces by coordinates
                coords_to_interfaces = {}
                for element_id, element in interface_elements.items():
                    if len(element.nodes) >= 2 and all(n in self.nodes for n in element.nodes[:2]):
                        i_node = self.nodes[element.nodes[0]]
                        j_node = self.nodes[element.nodes[1]]
                        coords = (i_node.x, i_node.y)

                        if coords not in coords_to_interfaces:
                            coords_to_interfaces[coords] = []
                        coords_to_interfaces[coords].append(element_id)

                # Report on interface distribution
                f.write("=== INTERFACE DISTRIBUTION BY COORDINATES ===\n")
                for coords, elements in coords_to_interfaces.items():
                    f.write(f"Coordinates {coords}: {len(elements)} interfaces\n")
                    if len(elements) > 1:
                        f.write(f"  Elements: {elements}\n")

                f.write("\n=== DETAILED INTERFACE ELEMENTS ===\n")
                for element_id, element in sorted(interface_elements.items()):
                    f.write(f"\nInterface Element {element_id}:\n")
                    f.write(f"  Nodes: {element.nodes}\n")
                    f.write(f"  Material: {element.material}\n")
                    f.write(f"  Step: {element.step}\n")
                    f.write(f"  Friction: {getattr(element, 'friction', 'N/A')}\n")
                    f.write(f"  Angle: {getattr(element, 'angle', 'N/A')}\n")

                    # Add node coordinates
                    f.write("  Node coordinates:\n")
                    for node_id in element.nodes:
                        if node_id in self.nodes:
                            node = self.nodes[node_id]
                            f.write(f"    Node {node_id}: ({node.x}, {node.y})\n")
                        else:
                            f.write(f"    Node {node_id}: NOT FOUND\n")

                # Add verification for beam elements
                f.write("\n=== BEAM ELEMENT VERIFICATION ===\n")
                beam_elements = {id: e for id, e in self.elements.items() if isinstance(e, Element1D)}
                f.write(f"Total beam elements: {len(beam_elements)}\n")

                # Check for shared nodes
                node_to_beams = {}
                for element_id, element in beam_elements.items():
                    for node_id in element.nodes:
                        if node_id not in node_to_beams:
                            node_to_beams[node_id] = []
                        node_to_beams[node_id].append(element_id)

                shared_nodes = {n: beams for n, beams in node_to_beams.items() if len(beams) > 1}
                f.write(f"Shared nodes (used by multiple beams): {len(shared_nodes)}\n")

                for node_id, beam_ids in shared_nodes.items():
                    f.write(f"  Node {node_id} used by beams: {beam_ids}\n")
                    if node_id in nodes_with_interfaces:
                        f.write(f"    This node has interface(s)\n")

                        # Find interface elements using this node
                        interfaces_using_node = []
                        for element_id, element in interface_elements.items():
                            if node_id in element.nodes:
                                interfaces_using_node.append(element_id)

                        if interfaces_using_node:
                            f.write(f"    Used by interface elements: {interfaces_using_node}\n")

                f.write("\n=== END OF DEBUG INFO ===\n")

                return True
        except Exception as e:
            logger.error(f"Error dumping interface debug info: {e}")
            return False

    def _find_beam_chains(self, beam_elements: Dict[int, Element1D]) -> List[List[int]]:
        """
        Find chains of connected beam elements in geometric order.

        Args:
            beam_elements: Dictionary of beam elements to analyze

        Returns:
            List of chains, where each chain is a list of beam element IDs in geometric order
        """
        # Create a graph of beam connections
        beam_graph = {}  # node_id -> [(element_id, other_node_id), ...]

        # Build the graph
        for element_id, element in beam_elements.items():
            node1, node2 = element.nodes

            # Add connection from node1 to node2
            if node1 not in beam_graph:
                beam_graph[node1] = []
            beam_graph[node1].append((element_id, node2))

            # Add connection from node2 to node1
            if node2 not in beam_graph:
                beam_graph[node2] = []
            beam_graph[node2].append((element_id, node1))

        # Find all chains by traversing the graph
        chains = []
        visited_elements = set()

        # Start from each beam that hasn't been visited yet
        for element_id, element in beam_elements.items():
            if element_id in visited_elements:
                continue

            # Found a new chain
            chain = [element_id]
            visited_elements.add(element_id)

            # Start with the two endpoint nodes of this beam
            node1, node2 = element.nodes

            # Try to extend chain in both directions
            for start_node in [node1, node2]:
                # Find the other node in the current beam
                other_node = node2 if start_node == node1 else node1

                # Continue extending the chain until we can't anymore
                current_node = start_node
                prev_node = other_node

                while True:
                    # Find next beam connected to current_node that isn't already in the chain
                    next_beam = None
                    next_node = None

                    for beam_id, conn_node in beam_graph.get(current_node, []):
                        if beam_id not in visited_elements and conn_node != prev_node:
                            next_beam = beam_id
                            next_node = conn_node
                            break

                    if next_beam is None:
                        # No more beams to add in this direction
                        break

                    # Add the next beam to the chain
                    if start_node == node1:
                        # Extending forward
                        chain.append(next_beam)
                    else:
                        # Extending backward
                        chain.insert(0, next_beam)

                    visited_elements.add(next_beam)
                    prev_node = current_node
                    current_node = next_node

            # Add the chain to our list
            chains.append(chain)

        return chains

    def _extract_shared_nodes_from_chain(self, chain: List[int],
                                         beam_elements: Dict[int, Element1D]) -> List[int]:
        """
        Extract shared nodes from a chain of beam elements in geometric order.

        Args:
            chain: List of beam element IDs in geometric order
            beam_elements: Dictionary of beam elements

        Returns:
            List of shared node IDs in geometric order
        """
        if len(chain) <= 1:
            return []

        # Find geometric order of nodes in the chain
        first_beam = beam_elements[chain[0]]
        node1, node2 = first_beam.nodes

        # Try to determine consistent order by checking connection with second beam
        second_beam = beam_elements[chain[1]]
        if node1 in second_beam.nodes:
            chain_nodes = [node2, node1]  # node1 is shared with second beam
        else:
            chain_nodes = [node1, node2]  # node2 is shared with second beam

        # Walk through remaining beams to add their nodes in order
        for i in range(1, len(chain)):
            beam = beam_elements[chain[i]]
            last_node = chain_nodes[-1]

            # Find the next node (not the one we just added)
            next_node = [n for n in beam.nodes if n != last_node][0]
            chain_nodes.append(next_node)

        # Extract only the shared nodes (those appearing at the junction between beams)
        shared_nodes = chain_nodes[1:-1]

        return shared_nodes

    def _calculate_beam_angles(self, beam_collection: Dict[int, Element1D]) -> Dict[int, float]:
        """
        Calculate interface angles for nodes in beam elements based on beam directions.
        Uses a vector perpendicular to the chord connecting beam endpoints, with direction
        determined by the position of the shared node.

        Args:
            beam_collection: Dictionary of beam elements to analyze

        Returns:
            Dictionary mapping node IDs to angles (in degrees)
        """
        node_angles = {}

        # Build a node-to-elements map and a beam connectivity graph
        node_to_elements = {}
        beam_graph = {}  # Maps (element_id, node_id) to connected elements

        for element_id, element in beam_collection.items():
            for node_id in element.nodes:
                if node_id not in node_to_elements:
                    node_to_elements[node_id] = []
                node_to_elements[node_id].append(element_id)

                # Build the beam connectivity graph
                if node_id not in beam_graph:
                    beam_graph[node_id] = []
                beam_graph[node_id].append(element_id)

        # For each node connected to exactly two beam elements, calculate the interface angle
        for node_id, element_ids in node_to_elements.items():
            if len(element_ids) != 2:
                continue  # Skip nodes not connecting exactly two beam elements

            # Try to calculate angle with direct endpoints first
            angle = self._calculate_angle_for_node(node_id, element_ids, beam_collection)

            # If we couldn't determine the angle (colinearity issue), try with extended search
            if angle is None:
                angle = self._calculate_angle_with_extended_search(
                    node_id, element_ids, beam_collection, beam_graph, max_depth=3
                )

            # If we still couldn't determine the angle, skip (section is too flat to calculate)
            if angle is None:
                continue

            # Store the calculated angle
            node_angles[node_id] = angle

        return node_angles

    def _calculate_angle_for_node(self, shared_node_id: int, element_ids: List[int],
                                  beam_collection: Dict[int, Element1D]) -> Optional[float]:
        """
        Calculate interface angle for a specific shared node between two beam elements.

        Returns:
            Calculated angle in degrees, or None if angle couldn't be determined
        """
        # Get the shared node (interface location)
        if shared_node_id not in self.nodes:
            return None
        shared_node = self.nodes[shared_node_id]
        shared_point = (shared_node.x, shared_node.y)

        # Get the two beam elements
        beam1 = beam_collection[element_ids[0]]
        beam2 = beam_collection[element_ids[1]]

        # For each beam, find the other node (not the shared one)
        endpoints = []
        for beam in [beam1, beam2]:
            for other_node_id in beam.nodes:
                if other_node_id != shared_node_id and other_node_id in self.nodes:
                    other_node = self.nodes[other_node_id]
                    endpoints.append((other_node.x, other_node.y))
                    break

        # If we don't have two endpoints, can't calculate
        if len(endpoints) != 2:
            return None

        # Calculate the chord vector (from endpoint 0 to endpoint 1)
        chord_vector = (endpoints[1][0] - endpoints[0][0],
                        endpoints[1][1] - endpoints[0][1])

        # Calculate the chord length
        chord_length = math.sqrt(chord_vector[0] ** 2 + chord_vector[1] ** 2)

        if chord_length < 1e-8:  # Avoid division by zero
            return None

        # Calculate the chord midpoint
        chord_midpoint = ((endpoints[0][0] + endpoints[1][0]) / 2,
                          (endpoints[0][1] + endpoints[1][1]) / 2)

        # Vector from chord midpoint to shared node
        vector_to_shared = (shared_point[0] - chord_midpoint[0],
                            shared_point[1] - chord_midpoint[1])

        # Normalize vector_to_shared
        mag_vector_to_shared = math.sqrt(vector_to_shared[0] ** 2 + vector_to_shared[1] ** 2)

        # Check for colinearity - if the shared point is too close to the chord
        if mag_vector_to_shared < 1e-8:  # Colinear case
            return None

        # Normalize the vector
        vector_to_shared = (vector_to_shared[0] / mag_vector_to_shared,
                            vector_to_shared[1] / mag_vector_to_shared)

        # Calculate two possible perpendicular vectors to the chord
        perpendicular1 = (-chord_vector[1] / chord_length, chord_vector[0] / chord_length)  # 90° CCW
        perpendicular2 = (chord_vector[1] / chord_length, -chord_vector[0] / chord_length)  # 90° CW

        # Determine which perpendicular vector points toward the shared node
        # by comparing dot products
        dot1 = perpendicular1[0] * vector_to_shared[0] + perpendicular1[1] * vector_to_shared[1]
        dot2 = perpendicular2[0] * vector_to_shared[0] + perpendicular2[1] * vector_to_shared[1]

        # Select the perpendicular that has a positive dot product with the vector to shared point
        chosen_perpendicular = perpendicular1 if dot1 > dot2 else perpendicular2

        # Calculate the angle of this perpendicular vector from the horizontal
        angle = math.degrees(math.atan2(chosen_perpendicular[1], chosen_perpendicular[0]))

        # Normalize to 0-360 range
        while angle < 0:
            angle += 360.0
        while angle >= 360.0:
            angle -= 360.0

        return angle

    def _calculate_angle_with_extended_search(self, shared_node_id: int, element_ids: List[int],
                                              beam_collection: Dict[int, Element1D],
                                              beam_graph: Dict[int, List[int]],
                                              max_depth: int = 3) -> Optional[float]:
        """
        Calculate interface angle by looking at extended beam connections when direct
        calculation fails due to colinearity.

        Args:
            shared_node_id: ID of the shared node where angle is needed
            element_ids: List of the two beam elements connected at the shared node
            beam_collection: Dictionary of all beam elements
            beam_graph: Graph mapping node IDs to connected element IDs
            max_depth: Maximum depth to search for non-colinear configurations

        Returns:
            Calculated angle in degrees, or None if angle couldn't be determined
        """
        # Create a queue of node triplets to try [(shared_node, endpoint1, endpoint2), ...]
        # Each triplet is a candidate for angle calculation
        triplets_to_try = []

        # Get the shared node
        shared_node = self.nodes[shared_node_id]

        # Get the two connected beam endpoints (first hop)
        endpoints = []
        beam_endpoints = {}  # Map element_id -> endpoint_node_id

        for element_id in element_ids:
            beam = beam_collection[element_id]
            for node_id in beam.nodes:
                if node_id != shared_node_id:
                    endpoints.append(node_id)
                    beam_endpoints[element_id] = node_id
                    break

        # Initial case - direct endpoints (depth 1)
        triplets_to_try.append((shared_node_id, endpoints[0], endpoints[1]))

        # Try combinations of extended endpoints (depths 2 to max_depth)
        for depth in range(2, max_depth + 1):
            # For each original beam, look further along the beam path
            for i, start_element_id in enumerate(element_ids):
                # Use BFS to find nodes at exact depth
                frontier = [(beam_endpoints[start_element_id], start_element_id,
                             1)]  # (node_id, last_element_id, current_depth)
                visited = {shared_node_id, beam_endpoints[start_element_id]}

                while frontier:
                    current_node, last_element, current_depth = frontier.pop(0)

                    if current_depth == depth:
                        # Use this node with the direct endpoint from the other beam
                        other_endpoint = beam_endpoints[element_ids[1 - i]]
                        triplets_to_try.append((shared_node_id, current_node, other_endpoint))
                        continue

                    # Add connected nodes at next depth
                    for next_element_id in beam_graph.get(current_node, []):
                        # Skip the element we just came from
                        if next_element_id == last_element:
                            continue

                        # Get the other node of this beam element
                        beam = beam_collection.get(next_element_id)
                        if not beam:
                            continue

                        for next_node_id in beam.nodes:
                            if next_node_id != current_node and next_node_id not in visited:
                                visited.add(next_node_id)
                                frontier.append((next_node_id, next_element_id, current_depth + 1))

        # Try each triplet until we find one that gives a valid angle
        for shared, end1, end2 in triplets_to_try:
            # Skip the initial case which we know failed
            if end1 == endpoints[0] and end2 == endpoints[1]:
                continue

            # Try with this combination
            angle = self._calculate_angle_for_triplet(shared, end1, end2)
            if angle is not None:
                return angle

        # If all triplets failed, return None
        return None

    def _calculate_angle_for_triplet(self, shared_node_id: int, end1_id: int, end2_id: int) -> Optional[float]:
        """
        Calculate angle for a specific triplet of nodes.

        Args:
            shared_node_id: ID of the shared node
            end1_id: ID of the first endpoint
            end2_id: ID of the second endpoint

        Returns:
            Calculated angle in degrees, or None if angle couldn't be determined
        """
        # Check that all nodes exist
        if any(node_id not in self.nodes for node_id in [shared_node_id, end1_id, end2_id]):
            return None

        shared_node = self.nodes[shared_node_id]
        end1_node = self.nodes[end1_id]
        end2_node = self.nodes[end2_id]

        shared_point = (shared_node.x, shared_node.y)
        endpoints = [(end1_node.x, end1_node.y), (end2_node.x, end2_node.y)]

        # Calculate the chord vector (from endpoint 0 to endpoint 1)
        chord_vector = (endpoints[1][0] - endpoints[0][0],
                        endpoints[1][1] - endpoints[0][1])

        # Calculate the chord length
        chord_length = math.sqrt(chord_vector[0] ** 2 + chord_vector[1] ** 2)

        if chord_length < 1e-8:  # Endpoints are at the same location
            return None

        # Calculate the chord midpoint
        chord_midpoint = ((endpoints[0][0] + endpoints[1][0]) / 2,
                          (endpoints[0][1] + endpoints[1][1]) / 2)

        # Vector from chord midpoint to shared node
        vector_to_shared = (shared_point[0] - chord_midpoint[0],
                            shared_point[1] - chord_midpoint[1])

        # Normalize vector_to_shared
        mag_vector_to_shared = math.sqrt(vector_to_shared[0] ** 2 + vector_to_shared[1] ** 2)

        # Check for colinearity - if the shared point is too close to the chord
        if mag_vector_to_shared < 1e-8:  # Colinear case
            return None

        # Normalize the vector
        vector_to_shared = (vector_to_shared[0] / mag_vector_to_shared,
                            vector_to_shared[1] / mag_vector_to_shared)

        # Calculate perpendicular vectors to the chord (90° CCW and CW)
        perpendicular1 = (-chord_vector[1] / chord_length, chord_vector[0] / chord_length)
        perpendicular2 = (chord_vector[1] / chord_length, -chord_vector[0] / chord_length)

        # Choose the perpendicular that points toward the shared node
        dot1 = perpendicular1[0] * vector_to_shared[0] + perpendicular1[1] * vector_to_shared[1]
        dot2 = perpendicular2[0] * vector_to_shared[0] + perpendicular2[1] * vector_to_shared[1]
        chosen_perpendicular = perpendicular1 if dot1 > dot2 else perpendicular2

        # Calculate angle from horizontal
        angle = math.degrees(math.atan2(chosen_perpendicular[1], chosen_perpendicular[0]))

        # Normalize to 0-360 range
        while angle < 0:
            angle += 360.0
        while angle >= 360.0:
            angle -= 360.0

        return angle

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

    def ensure_valid_2d_element_ordering(self, element: Element2D) -> bool:
        """
        Ensure that 2D element nodes are ordered properly and in CCW orientation.
        Handles both triangular and quadrilateral elements.

        Args:
            element: The 2D element to check and potentially reorder

        Returns:
            True if the element was successfully ordered or already valid,
            False if the element has an invalid configuration that can't be fixed
        """
        # Get node coordinates
        node_coords = []
        node_ids = []
        for node_id in element.nodes:
            if node_id in self.nodes:
                node = self.nodes[node_id]
                node_coords.append((node.x, node.y))
                node_ids.append(node_id)
            else:
                logger.warning(f"Missing node {node_id} for element {element.element_id}")
                return False

        # For triangles (3 nodes)
        if len(node_coords) == 3:
            # Calculate signed area
            (x1, y1), (x2, y2), (x3, y3) = node_coords
            signed_area = 0.5 * ((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))

            # If area is negative, reverse node order to make it CCW
            if signed_area < 0:
                element.nodes = list(reversed(element.nodes))
                logger.info(f"Reordered triangle nodes for element {element.element_id} to ensure CCW orientation")
            return True

        # For quadrilaterals (4 nodes)
        elif len(node_coords) == 4:
            # Find the centroid
            centroid_x = sum(x for x, _ in node_coords) / 4
            centroid_y = sum(y for _, y in node_coords) / 4

            # Calculate angles from centroid to each node
            angles = []
            for x, y in node_coords:
                angle = math.atan2(y - centroid_y, x - centroid_x)
                angles.append(angle)

            # Sort nodes by angle around centroid (this gives CCW order)
            sorted_indices = sorted(range(4), key=lambda i: angles[i])

            # Check if we need to reorder
            if sorted_indices != [0, 1, 2, 3]:
                # Reorder nodes
                new_node_ids = [node_ids[i] for i in sorted_indices]
                element.nodes = new_node_ids
                logger.info(f"Reordered quad nodes for element {element.element_id} to ensure CCW orientation")

            # Verify the result is not self-intersecting
            new_coords = [node_coords[i] for i in sorted_indices]
            if self._is_self_intersecting(new_coords):
                logger.warning(f"Element {element.element_id} forms a self-intersecting quad")
                return False

            return True

        else:
            logger.warning(f"Element {element.element_id} has {len(node_coords)} nodes, expected 3 or 4")
            return False

    def _is_self_intersecting(self, quad_coords):
        """Check if a quadrilateral defined by 4 coordinates is self-intersecting."""
        # Check if any two non-adjacent edges intersect
        # Edge 0-1 vs Edge 2-3
        if self._lines_intersect(quad_coords[0], quad_coords[1], quad_coords[2], quad_coords[3]):
            return True
        # Edge 1-2 vs Edge 3-0
        if self._lines_intersect(quad_coords[1], quad_coords[2], quad_coords[3], quad_coords[0]):
            return True
        return False

    def _lines_intersect(self, p1, p2, p3, p4):
        """Check if line segment p1-p2 intersects with line segment p3-p4."""

        # Implementation of line segment intersection test
        def ccw(a, b, c):
            return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
