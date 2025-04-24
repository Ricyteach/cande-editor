"""
Canvas view for CANDE Input File Editor.
"""
import tkinter as tk
from typing import Dict, List, Set, Tuple, Any, Optional
from enum import Enum, auto
import logging

from models.node import Node
from models.element import BaseElement, Element, Element1D, Element2D
from utils.constants import CANDE_COLORS

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

    def render_mesh(self, nodes: Dict[int, Node], elements: Dict[int, BaseElement],
                   selected_elements: Set[int], max_material: int = 1, max_step: int = 1) -> None:
        """
        Render the mesh on the canvas.

        Args:
            nodes: Dictionary of nodes
            elements: Dictionary of elements
            selected_elements: Set of selected element IDs
            max_material: Maximum material number for color mapping
            max_step: Maximum step number for color mapping
        """
        if not nodes or not elements:
            return

        # Clear the canvas
        self.canvas.delete("all")

        # Draw elements
        for element_id, element in elements.items():
            # Get screen coordinates for each node
            screen_coords = []
            for node_id in element.nodes:
                if node_id in nodes:
                    node = nodes[node_id]
                    screen_x, screen_y = self.model_to_screen(node.x, node.y)
                    screen_coords.append((screen_x, screen_y))

            # Skip if we don't have enough coordinates
            if len(screen_coords) < 3:
                continue

            # Create polygon coordinates list
            polygon_coords = [coord for point in screen_coords for coord in point]

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

            # Create the polygon
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

    def find_element_at_position(self, screen_x: float, screen_y: float,
                                nodes: Dict[int, Node],
                                elements: Dict[int, BaseElement]) -> Optional[int]:
        """
        Find the element at the given screen position.

        Args:
            screen_x: Screen X coordinate
            screen_y: Screen Y coordinate
            nodes: Dictionary of nodes
            elements: Dictionary of elements

        Returns:
            Element ID if found, None otherwise
        """
        model_x, model_y = self.screen_to_model(screen_x, screen_y)

        # Check each element
        for element_id, element in elements.items():
            # Get the nodes for this element
            element_nodes = [nodes[node_id] for node_id in element.nodes if node_id in nodes]
            if len(element_nodes) < 3:
                continue

            # Create a polygon from the nodes
            polygon = [(node.x, node.y) for node in element_nodes]

            # Check if the point is inside the polygon
            if self.point_in_polygon(model_x, model_y, polygon):
                return element_id

        return None
