"""
Canvas view for CANDE Input File Editor.
"""
import tkinter as tk
from typing import Dict, List, Set, Tuple, Any, Optional
from enum import Enum, auto
import logging
import math

from models.node import Node
from models.element import BaseElement, Element, Element1D, Element2D, InterfaceElement
from utils.constants import CANDE_COLORS, LINE_ELEMENT_WIDTH

# Configure logging
logger = logging.getLogger(__name__)


class DisplayMode(Enum):
    """Display mode for coloring elements."""
    MATERIAL = auto()
    STEP = auto()


class CanvasView:
    """Handles rendering the CANDE model on the canvas."""

    def __init__(self, canvas: tk.Canvas) -> None:
        """
        Initialize the canvas view.

        Args:
            canvas: The Tkinter canvas to render on
        """
        self.canvas = canvas
        self.display_mode = DisplayMode.MATERIAL

        # View state variables
        self.zoom_level = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0

        # Selection box variables
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False
        self.locked_cursor_x = 0
        self.locked_cursor_y = 0

    def render_mesh(self, nodes, elements, selected_elements, max_material=1, max_step=1,
                    element_type_filter=None, line_width=3) -> None:
        """
            Render the mesh on the canvas.

            Special rendering is applied to interface elements to show:
            - Diamond-shaped markers at interface locations
            - Red arrows indicating the direction of normal force
            - Green dashed lines showing the interface plane
            - Color-coding based on friction values
            - Material and angle labels for better identification

            Args:
                nodes: Dictionary of nodes
                elements: Dictionary of elements
                selected_elements: Set of selected element IDs
                max_material: Maximum material number for color mapping
                max_step: Maximum step number for color mapping
                element_type_filter: List of element types to display, None means display all
                line_width: Width for 1D elements
            """
        if not nodes or not elements:
            return

        # Clear the canvas
        self.canvas.delete("all")

        # Draw elements
        for element_id, element in elements.items():
            # Check if the element should be displayed based on filter
            if not self._should_display_element(element, element_type_filter):
                continue

            # Get screen coordinates for each node
            screen_coords = []
            for node_id in element.nodes:
                if node_id in nodes:
                    node = nodes[node_id]
                    screen_x, screen_y = self.model_to_screen(node.x, node.y)
                    screen_coords.append((screen_x, screen_y))

            # Skip if we don't have enough coordinates
            if len(screen_coords) < 2:
                continue

            # Determine fill color based on display mode
            if self.display_mode == DisplayMode.MATERIAL:
                color_index = ((element.material - 1) % len(CANDE_COLORS))
                fill_color = CANDE_COLORS[color_index]
            else:  # Step mode
                color_index = ((element.step - 1) % len(CANDE_COLORS))
                fill_color = CANDE_COLORS[color_index]

            # Draw with thicker outline if selected
            outline_width = 2 if element_id in selected_elements else 1
            outline_color = "red" if element_id in selected_elements else "black"

            # Different rendering for 1D vs 2D vs Interface elements
            if isinstance(element, Element1D) and len(screen_coords) == 2:
                # For 1D elements (beams), draw a thick line
                element_line_width = line_width * outline_width

                # Create the line
                self.canvas.create_line(
                    screen_coords[0][0], screen_coords[0][1],
                    screen_coords[1][0], screen_coords[1][1],
                    fill=fill_color,
                    width=element_line_width,
                    tags=(f"element_{element_id}",)
                )

                # Draw a selection indicator if the element is selected
                if element_id in selected_elements:
                    # Draw selection indicators at each end point
                    self._draw_selection_indicator(screen_coords[0][0], screen_coords[0][1])
                    self._draw_selection_indicator(screen_coords[1][0], screen_coords[1][1])
                    # In the CanvasView.render_mesh method, for interface elements:

            elif isinstance(element, InterfaceElement) and len(element.nodes) >= 2:
                # For interface elements, use consistent colors based on friction
                friction = getattr(element, 'friction', 0.3)

                # Get color index from model
                if hasattr(self, 'model'):
                    color_index = self.model.get_friction_color_index(friction)
                else:
                    # Fallback if model reference is not available
                    color_index = int(friction * 10) % len(CANDE_COLORS)

                fill_color = CANDE_COLORS[color_index]

                # IMPORTANT: For interface elements, always use normal outline (never show as selected)
                # This avoids confusing users since interfaces can't be modified
                outline_width = 1
                outline_color = "black"

                # For interface elements, draw a diamond shape
                # Get coordinates for interface element nodes (only need first two nodes for placement)
                screen_coords = []
                for node_id in element.nodes[:2]:  # Just use I and J nodes for rendering
                    if node_id in nodes:
                        node = nodes[node_id]
                        screen_x, screen_y = self.model_to_screen(node.x, node.y)
                        screen_coords.append((screen_x, screen_y))

                # Skip if we don't have enough coordinates
                if len(screen_coords) < 2:
                    continue

                # Calculate average position (they should be the same, but just in case)
                avg_x = sum(x for x, _ in screen_coords) / len(screen_coords)
                avg_y = sum(y for _, y in screen_coords) / len(screen_coords)

                # Draw interface marker (diamond shape)
                size = 8  # Size of marker
                self.canvas.create_polygon(
                    avg_x, avg_y - size,
                           avg_x + size, avg_y,
                    avg_x, avg_y + size,
                           avg_x - size, avg_y,
                    fill=fill_color,
                    outline=outline_color,
                    width=outline_width,
                    tags=(f"element_{element_id}",)
                )

                # After drawing the interface diamond:
                if isinstance(element, InterfaceElement):
                    # Draw improved angle indicator with a longer line and better arrow
                    indicator_length = 20  # Make this longer to be more visible
                    angle_rad = math.radians(element.angle)

                    # Calculate arrow endpoint
                    indicator_x = avg_x + indicator_length * math.cos(angle_rad)
                    # Flip the y direction since canvas has y increasing downward
                    indicator_y = avg_y - indicator_length * math.sin(angle_rad)

                    # Draw the main arrow line
                    self.canvas.create_line(
                        avg_x, avg_y, indicator_x, indicator_y,
                        fill="red",  # Use a bright color
                        width=2,  # Make the line thicker
                        arrow=tk.LAST,  # Add arrowhead at the end
                        arrowshape=(10, 12, 5),  # Customize arrowhead shape (dx, dy, z)
                        tags=(f"angle_indicator_{element_id}",)
                    )

                    # Add a small text label showing the angle value and friction
                    # Position the text offset from the arrow to avoid overlap
                    offset_factor = 1.3
                    text_x = avg_x + (indicator_length * offset_factor) * math.cos(angle_rad)
                    text_y = avg_y - (indicator_length * offset_factor) * math.sin(angle_rad)

                    self.canvas.create_text(
                        text_x, text_y,
                        text=f"{element.angle:.0f}°",
                        fill="blue",
                        font=("Arial", 8, "bold"),  # Make font bold for better visibility
                        tags=(f"angle_text_{element_id}",)
                    )

                    # Material ID text
                    # Calculate position on opposite side of diamond from the angle indicator
                    opposite_angle_rad = angle_rad + math.pi  # Opposite direction from angle indicator
                    text_distance = indicator_length * 0.8  # Same offset factor as for angle text
                    material_text_x = avg_x + text_distance * math.cos(opposite_angle_rad)
                    material_text_y = avg_y - text_distance * math.sin(opposite_angle_rad)

                    # Draw the material ID text with the same color as the diamond
                    self.canvas.create_text(
                        material_text_x, material_text_y,
                        text=f"{element.material}",
                        fill=fill_color,  # Use the same color as the diamond
                        font=("Arial", 8, "bold"),
                        tags=(f"material_text_{element_id}",)
                    )

                    # Add a perpendicular tick mark to indicate the interface plane
                    perp_length = 10
                    perp_angle_rad = angle_rad + math.pi / 2  # Perpendicular to force direction

                    perp1_x = avg_x + perp_length * math.cos(perp_angle_rad)
                    perp1_y = avg_y - perp_length * math.sin(perp_angle_rad)
                    perp2_x = avg_x - perp_length * math.cos(perp_angle_rad)
                    perp2_y = avg_y + perp_length * math.sin(perp_angle_rad)

                    # Draw the interface plane indicator line
                    self.canvas.create_line(
                        perp1_x, perp1_y, perp2_x, perp2_y,
                        fill="green",  # Different color for interface plane
                        width=2,
                        dash=(3, 2),  # Dashed line
                        tags=(f"plane_indicator_{element_id}",)
                    )

                # Draw a selection indicator if the element is selected
                if element_id in selected_elements:
                    self._draw_selection_indicator(avg_x, avg_y)
            else:
                # For 2D elements, create a polygon
                polygon_coords = [coord for point in screen_coords for coord in point]

                self.canvas.create_polygon(
                    polygon_coords,
                    fill=fill_color,
                    outline=outline_color,
                    width=outline_width,
                    tags=(f"element_{element_id}",)
                )

        # Draw selection box if dragging
        if self.is_dragging:
            self.draw_selection_box(
                self.drag_start_x, self.drag_start_y,
                self.locked_cursor_x, self.locked_cursor_y
            )

        # Update display immediately to improve responsiveness
        self.canvas.update_idletasks()

    def _draw_selection_indicator(self, x: float, y: float, radius: int = 4) -> None:
        """
        Draw a small circle to indicate selection points.

        Args:
            x: X coordinate
            y: Y coordinate
            radius: Radius of the indicator circle
        """
        self.canvas.create_oval(
            x - radius, y - radius,
            x + radius, y + radius,
            fill="red",
            outline="red"
        )

    def draw_selection_box(self, start_x: float, start_y: float,
                          end_x: float, end_y: float) -> None:
        """
        Draw the selection box on the canvas.

        Args:
            start_x: Starting X coordinate
            start_y: Starting Y coordinate
            end_x: Ending X coordinate
            end_y: Ending Y coordinate
        """
        self.canvas.delete("selection_box")
        self.canvas.create_rectangle(
            start_x, start_y, end_x, end_y,
            outline="blue",
            width=2,
            dash=(4, 4),
            tags=("selection_box",)
        )

    def model_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert model coordinates to screen coordinates.

        Args:
            x: Model X coordinate
            y: Model Y coordinate

        Returns:
            Tuple of screen coordinates (x, y)
        """
        # In CANDE, Y=0 is at the bottom of the screen (inverted from canvas)
        screen_x = x * self.zoom_level + self.pan_offset_x
        screen_y = self.canvas.winfo_height() - (y * self.zoom_level + self.pan_offset_y)
        return screen_x, screen_y

    def screen_to_model(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """
        Convert screen coordinates to model coordinates.

        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate

        Returns:
            Tuple of model coordinates (x, y)
        """
        # Invert the model_to_screen transformation
        model_x = (screen_x - self.pan_offset_x) / self.zoom_level
        model_y = (self.canvas.winfo_height() - screen_y - self.pan_offset_y) / self.zoom_level
        return model_x, model_y

    def zoom_to_fit(self, model_min_x: float, model_min_y: float,
                   model_max_x: float, model_max_y: float) -> None:
        """
        Zoom to fit the entire model in the canvas.

        Args:
            model_min_x: Minimum X coordinate of the model
            model_min_y: Minimum Y coordinate of the model
            model_max_x: Maximum X coordinate of the model
            model_max_y: Maximum Y coordinate of the model
        """
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Ensure we have valid dimensions
        if canvas_width < 10 or canvas_height < 10:
            logger.warning("Canvas dimensions not ready for zoom_to_fit")
            return

        # Calculate model dimensions
        model_width = model_max_x - model_min_x
        model_height = model_max_y - model_min_y

        # Add padding
        padding = 0.05  # 5% padding
        model_width *= (1 + padding * 2)
        model_height *= (1 + padding * 2)

        # Calculate zoom level to fit
        zoom_x = canvas_width / model_width if model_width > 0 else 1.0
        zoom_y = canvas_height / model_height if model_height > 0 else 1.0
        self.zoom_level = min(zoom_x, zoom_y)

        # Calculate pan offset to center the model
        center_x = (model_min_x + model_max_x) / 2
        center_y = (model_min_y + model_max_y) / 2

        self.pan_offset_x = canvas_width / 2 - center_x * self.zoom_level
        self.pan_offset_y = canvas_height / 2 + center_y * self.zoom_level  # Y is inverted

    def set_display_mode(self, mode: DisplayMode) -> None:
        """
        Set the display mode.

        Args:
            mode: The display mode (MATERIAL or STEP)
        """
        self.display_mode = mode

    def point_in_polygon(self, x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
        """
        Check if a point is inside a polygon using ray casting algorithm.

        Args:
            x: X coordinate of the point
            y: Y coordinate of the point
            polygon: List of (x, y) coordinates defining the polygon vertices

        Returns:
            True if the point is inside the polygon, False otherwise
        """
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def point_near_line(self, x: float, y: float, line_start: Tuple[float, float],
                        line_end: Tuple[float, float], threshold: float = None) -> bool:
        """
        Check if a point is near a line segment.

        Args:
            x: X coordinate of the point
            y: Y coordinate of the point
            line_start: Start point of the line (x, y)
            line_end: End point of the line (x, y)
            threshold: Maximum distance to consider a point near the line

        Returns:
            True if the point is near the line, False otherwise
        """
        # Use the passed threshold or default to LINE_ELEMENT_WIDTH * 2
        if threshold is None:
            threshold = LINE_ELEMENT_WIDTH * 2

        # Extract line start and end points
        x1, y1 = line_start
        x2, y2 = line_end

        # Calculate the length of the line segment
        line_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

        # If the line has zero length, check distance to the point
        if line_length == 0:
            return math.sqrt((x - x1)**2 + (y - y1)**2) <= threshold

        # Calculate the normalized direction vector of the line
        dx, dy = (x2 - x1) / line_length, (y2 - y1) / line_length

        # Calculate the vector from line start to the point
        px, py = x - x1, y - y1

        # Project the point onto the line
        projection = px * dx + py * dy

        # Clamp the projection to the line segment
        projection = max(0, min(projection, line_length))

        # Calculate the closest point on the line
        closest_x = x1 + projection * dx
        closest_y = y1 + projection * dy

        # Calculate the distance from the point to the closest point on the line
        distance = math.sqrt((x - closest_x)**2 + (y - closest_y)**2)

        return distance <= threshold

    def find_element_at_position(self, screen_x: float, screen_y: float,
                                 nodes: Dict[int, Node],
                                 elements: Dict[int, BaseElement],
                                 element_type_filter: Optional[str] = None,
                                 line_width: int = LINE_ELEMENT_WIDTH) -> Optional[int]:
        """
        Find the element at the given screen position.

        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            nodes: Dictionary of nodes
            elements: Dictionary of elements
            element_type_filter: Optional filter for element type ("1D", "2D", or None)
            line_width: Screen beam element width

        Returns:
            Element ID if found, None otherwise
        """
        model_x, model_y = self.screen_to_model(screen_x, screen_y)

        # Check each element
        for element_id, element in elements.items():
            # Apply element type filter
            if element_type_filter == "1D" and not isinstance(element, Element1D):
                continue
            elif element_type_filter == "2D" and not isinstance(element, Element2D):
                continue

            # Get the nodes for this element
            element_nodes = [nodes[node_id] for node_id in element.nodes if node_id in nodes]

            # Handle 1D elements (2 nodes)
            if isinstance(element, Element1D) and len(element_nodes) == 2:
                # Convert to screen coordinates for threshold comparison
                node1_screen_x, node1_screen_y = self.model_to_screen(element_nodes[0].x, element_nodes[0].y)
                node2_screen_x, node2_screen_y = self.model_to_screen(element_nodes[1].x, element_nodes[1].y)

                # Check if point is near the line
                if self.point_near_line(
                    screen_x, screen_y,
                    (node1_screen_x, node1_screen_y),
                    (node2_screen_x, node2_screen_y),
                    threshold=line_width * 2  # Double the line width as threshold
                ):
                    return element_id

            # Handle interface elements (3 nodes)
            elif isinstance(element, InterfaceElement):
                # For interface elements, check distance to the marker position
                avg_x = sum(node.x for node in element_nodes[:2]) / 2
                avg_y = sum(node.y for node in element_nodes[:2]) / 2

                # Convert to screen coordinates
                avg_screen_x, avg_screen_y = self.model_to_screen(avg_x, avg_y)

                # Check if point is near the marker (use a simple distance check)
                distance = math.sqrt((screen_x - avg_screen_x) ** 2 + (screen_y - avg_screen_y) ** 2)
                if distance <= 10:  # Adjust threshold as needed
                    return element_id

            # Handle 2D elements (3+ nodes)
            elif len(element_nodes) >= 3:
                # Create a polygon from the nodes
                polygon = [(node.x, node.y) for node in element_nodes]

                # Check if the point is inside the polygon
                if self.point_in_polygon(model_x, model_y, polygon):
                    return element_id

        return None

    def _should_display_element(self, element, element_type_filter):
        """
        Check if an element should be displayed based on the filter.

        Args:
            element: The element to check
            element_type_filter: List of element types to display, None means display all

        Returns:
            True if the element should be displayed, False otherwise
        """
        # If no filter or None, show all elements
        if element_type_filter is None:
            return True

        # If empty filter list, show nothing
        if element_type_filter == []:
            return False

        # Check element type against the filter list
        if "1D" in element_type_filter and isinstance(element, Element1D):
            return True
        if "2D" in element_type_filter and isinstance(element, Element2D):
            return True
        if "Interface" in element_type_filter and isinstance(element, InterfaceElement):
            return True

        return False
