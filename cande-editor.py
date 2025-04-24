#!/usr/bin/env python3
"""
CANDE Input File Editor - Version 1.0

A GUI tool for editing CANDE input files (.cid), specifically for selecting
and modifying soil elements' material model and step numbers.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import math
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Dict, Tuple, Set, Optional, Callable, Any, cast

# Constants for CANDE file format
# Character positions (1-based in CANDE documentation, converted to 0-based for Python)
MATERIAL_START_POS = 52  # Material field starts at position 53 (1-based) -> 52 (0-based)
MATERIAL_END_POS = 57  # Material field ends at position 57 (1-based) -> 57 (0-based)
MATERIAL_FIELD_WIDTH = MATERIAL_END_POS - MATERIAL_START_POS

STEP_START_POS = 57  # Step field starts at position 58 (1-based) -> 57 (0-based)
STEP_END_POS = 62  # Step field ends at position 62 (1-based) -> 62 (0-based)
STEP_FIELD_WIDTH = STEP_END_POS - STEP_START_POS


class SelectionMode(Enum):
    """Modes for element selection."""
    NONE = auto()
    NEW = auto()  # Start a new selection (replacing existing)
    ADD = auto()  # Add to existing selection (Ctrl)
    REMOVE = auto()  # Remove from existing selection (Shift)


class LassoDirection(Enum):
    """Direction of lasso selection."""
    LEFT_TO_RIGHT = auto()
    RIGHT_TO_LEFT = auto()


class DisplayMode(Enum):
    """Display mode for coloring elements."""
    MATERIAL = auto()
    STEP = auto()


@dataclass
class Node:
    """Represents a node in the CANDE model."""
    node_id: int
    x: float
    y: float
    line_number: int
    line_content: str


@dataclass
class Element:
    """Represents an element in the CANDE model."""
    element_id: int
    nodes: List[int]  # List of node IDs (2, 3, or 4)
    material: int
    step: int
    line_number: int
    line_content: str
    node_count: int  # 2 for beams, 3 for triangles, 4 for quads


class CandeEditor:
    """Main class for the CANDE Input File Editor."""

    # Define CANDE colors
    CANDE_COLORS = [
        "#FF0000",  # 1 Red
        "#FFA500",  # 2 Orange
        "#FFFF00",  # 3 Yellow
        "#00FF00",  # 4 Green
        "#0000FF",  # 5 Blue
        "#800080",  # 6 Purple
        "#D3D3D3",  # 7 Light Gray
        "#00FFFF",  # 8 Cyan
        "#FF00FF",  # 9 Magenta
        "#FF4500",  # 10 Red Orange
        "#808080",  # 11 Gray
        "#FA8072",  # 12 Salmon
        "#FFFFFF",  # 13 White
        "#A52A2A",  # 14 Brown
        "#CC5500",  # 15 Burnt Orange
        "#A9A9A9",  # 16 Dark Gray
        "#8B0000",  # 17 Dark Red
        "#E6E6FA",  # 18 Lavender
        "#00008B",  # 19 Dark Blue
        "#D2B48C",  # 20 Tan
    ]

    def __init__(self) -> None:
        """Initialize the CANDE Editor application."""
        self.root = tk.Tk()
        self.root.title("CANDE Input File Editor")
        self.root.geometry("1200x800")

        # Variables to store model data
        self.filepath: Optional[str] = None
        self.nodes: Dict[int, Node] = {}
        self.elements: Dict[int, Element] = {}
        self.selected_elements: Set[int] = set()
        self.file_content: List[str] = []

        # Variables for selection and display
        self.selection_mode = SelectionMode.NONE
        self.display_mode = DisplayMode.MATERIAL
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False
        self.lasso_direction = LassoDirection.LEFT_TO_RIGHT
        self.zoom_level = 1.0
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        self.locked_cursor_x = 0
        self.locked_cursor_y = 0
        self.model_min_x = 0.0
        self.model_min_y = 0.0
        self.model_max_x = 0.0
        self.model_max_y = 0.0

        # Material/step max values for color mapping
        self.max_material = 1
        self.max_step = 1

        # Create main UI components
        self.create_ui()

        # Set up event bindings
        self.setup_bindings()

    def create_ui(self) -> None:
        """Create the user interface components."""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create toolbar frame
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        # Open file button
        ttk.Button(toolbar, text="Open File", command=self.open_file).pack(side=tk.LEFT, padx=5)

        # Save file button
        ttk.Button(toolbar, text="Save File", command=self.save_file).pack(side=tk.LEFT, padx=5)

        # Display mode selection
        ttk.Label(toolbar, text="Display:").pack(side=tk.LEFT, padx=5)
        self.display_var = tk.StringVar(value="Material")
        display_combo = ttk.Combobox(toolbar, textvariable=self.display_var, values=["Material", "Step"], width=10,
                                     state="readonly")
        display_combo.pack(side=tk.LEFT, padx=5)
        display_combo.bind("<<ComboboxSelected>>", self.on_display_change)

        # Material number input for selection
        ttk.Label(toolbar, text="Material:").pack(side=tk.LEFT, padx=5)
        self.material_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.material_var, width=5).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Select by Material", command=self.select_by_material).pack(side=tk.LEFT, padx=5)

        # Step number input for selection
        ttk.Label(toolbar, text="Step:").pack(side=tk.LEFT, padx=5)
        self.step_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.step_var, width=5).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Select by Step", command=self.select_by_step).pack(side=tk.LEFT, padx=5)

        # Assign material/step to selection
        ttk.Label(toolbar, text="Assign Material:").pack(side=tk.LEFT, padx=5)
        self.assign_material_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.assign_material_var, width=5).pack(side=tk.LEFT)

        ttk.Label(toolbar, text="Assign Step:").pack(side=tk.LEFT, padx=5)
        self.assign_step_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.assign_step_var, width=5).pack(side=tk.LEFT)

        ttk.Button(toolbar, text="Assign to Selection", command=self.assign_to_selection).pack(side=tk.LEFT, padx=5)

        # Canvas for rendering
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(canvas_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

        # Coordinates display
        self.coords_var = tk.StringVar(value="X: 0.00  Y: 0.00")
        coords_label = ttk.Label(main_frame, textvariable=self.coords_var, relief=tk.SUNKEN, anchor=tk.E)
        coords_label.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

    def setup_bindings(self) -> None:
        """Set up event bindings for the canvas."""
        # Mouse events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        # Key events
        self.root.bind("<Control-Button-1>", self.on_ctrl_click)
        self.root.bind("<Shift-Button-1>", self.on_shift_click)
        self.root.bind("<Escape>", self.on_escape)
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())

        # Mouse wheel for zoom
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down

        # Middle mouse button for panning
        self.canvas.bind("<Button-2>", self.on_pan_start)  # Middle button on Linux
        self.canvas.bind("<Button-3>", self.on_pan_start)  # Right button as alternative
        self.canvas.bind("<B2-Motion>", self.on_pan_motion)
        self.canvas.bind("<B3-Motion>", self.on_pan_motion)

    def open_file(self) -> None:
        """Open a CANDE input file (.cid)."""
        filepath = filedialog.askopenfilename(
            title="Open CANDE Input File",
            filetypes=[("CANDE Input Files", "*.cid"), ("All Files", "*.*")]
        )

        if not filepath:
            return

        try:
            with open(filepath, 'r') as file:
                self.file_content = file.readlines()

            self.filepath = filepath
            self.parse_cande_file()
            self.calculate_model_extents()
            self.selected_elements.clear()
            self.zoom_to_fit()
            self.render_mesh()

            self.status_var.set(f"Loaded {filepath}")
            self.root.title(f"CANDE Input File Editor - {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")

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

                # Skip beam elements (2-node elements)
                if node_count == 2:
                    continue

                # Store the element
                self.elements[element_id] = Element(
                    element_id=element_id,
                    nodes=node_ids,
                    material=material,
                    step=step,
                    line_number=line_num,
                    line_content=line,
                    node_count=node_count
                )

                # Update max material and step numbers
                self.max_material = max(self.max_material, material)
                self.max_step = max(self.max_step, step)

        self.status_var.set(f"Loaded {len(self.nodes)} nodes and {len(self.elements)} elements")

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

    def zoom_to_fit(self) -> None:
        """Zoom to fit the entire model in the canvas."""
        if not self.nodes:
            return

        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Ensure we have valid dimensions
        if canvas_width < 10 or canvas_height < 10:
            # Canvas not ready yet, schedule another attempt
            self.root.after(100, self.zoom_to_fit)
            return

        # Calculate model dimensions
        model_width = self.model_max_x - self.model_min_x
        model_height = self.model_max_y - self.model_min_y

        # Add padding
        padding = 0.05  # 5% padding
        model_width *= (1 + padding * 2)
        model_height *= (1 + padding * 2)

        # Calculate zoom level to fit
        zoom_x = canvas_width / model_width if model_width > 0 else 1.0
        zoom_y = canvas_height / model_height if model_height > 0 else 1.0
        self.zoom_level = min(zoom_x, zoom_y)

        # Calculate pan offset to center the model
        center_x = (self.model_min_x + self.model_max_x) / 2
        center_y = (self.model_min_y + self.model_max_y) / 2

        self.pan_offset_x = canvas_width / 2 - center_x * self.zoom_level
        self.pan_offset_y = canvas_height / 2 + center_y * self.zoom_level  # Y is inverted

        self.render_mesh()

    def model_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """Convert model coordinates to screen coordinates."""
        # In CANDE, Y=0 is at the bottom of the screen (inverted from canvas)
        screen_x = x * self.zoom_level + self.pan_offset_x
        screen_y = self.canvas.winfo_height() - (y * self.zoom_level + self.pan_offset_y)
        return screen_x, screen_y

    def screen_to_model(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """Convert screen coordinates to model coordinates."""
        # Invert the model_to_screen transformation
        model_x = (screen_x - self.pan_offset_x) / self.zoom_level
        model_y = (self.canvas.winfo_height() - screen_y - self.pan_offset_y) / self.zoom_level
        return model_x, model_y

    def render_mesh(self) -> None:
        """Render the mesh on the canvas."""
        if not self.nodes or not self.elements:
            return

        # Clear the canvas
        self.canvas.delete("all")

        # Draw elements more efficiently by batching
        for element_id, element in self.elements.items():
            # Get screen coordinates for each node
            screen_coords = []
            for node_id in element.nodes:
                if node_id in self.nodes:
                    node = self.nodes[node_id]
                    screen_x, screen_y = self.model_to_screen(node.x, node.y)
                    screen_coords.append((screen_x, screen_y))

            # Skip if we don't have enough coordinates
            if len(screen_coords) < 3:
                continue

            # Create polygon coordinates list
            polygon_coords = [coord for point in screen_coords for coord in point]

            # Determine fill color based on display mode
            if self.display_mode == DisplayMode.MATERIAL:
                color_index = (element.material - 1) % len(self.CANDE_COLORS)
                fill_color = self.CANDE_COLORS[color_index]
            else:  # Step mode
                color_index = (element.step - 1) % len(self.CANDE_COLORS)
                fill_color = self.CANDE_COLORS[color_index]

            # Draw with thicker outline if selected
            outline_width = 2 if element_id in self.selected_elements else 1
            outline_color = "red" if element_id in self.selected_elements else "black"

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
            self.canvas.delete("selection_box")
            self.canvas.create_rectangle(
                self.drag_start_x, self.drag_start_y,
                self.locked_cursor_x, self.locked_cursor_y,
                outline="blue",
                width=2,
                dash=(4, 4),
                tags=("selection_box",)
            )

        # Update display immediately to improve responsiveness
        self.canvas.update_idletasks()

    def on_display_change(self, event: Any) -> None:
        """Handle display mode change between Material and Step."""
        mode = self.display_var.get()
        if mode == "Material":
            self.display_mode = DisplayMode.MATERIAL
        else:
            self.display_mode = DisplayMode.STEP
        self.render_mesh()

    def on_canvas_click(self, event: Any) -> None:
        """Handle canvas click event."""
        # Store the starting point for drag operations
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.locked_cursor_x = event.x
        self.locked_cursor_y = event.y
        self.is_dragging = True

        # By default, a new click will start a new selection (without Ctrl/Shift)
        if self.selection_mode == SelectionMode.NONE:
            self.selection_mode = SelectionMode.NEW

    def on_ctrl_click(self, event: Any) -> None:
        """Handle Ctrl+Click for adding to element selection."""
        self.selection_mode = SelectionMode.ADD
        self.on_canvas_click(event)

    def on_shift_click(self, event: Any) -> None:
        """Handle Shift+Click for removing from element selection."""
        self.selection_mode = SelectionMode.REMOVE
        self.on_canvas_click(event)

    def on_canvas_drag(self, event: Any) -> None:
        """Handle mouse drag on canvas for selection box."""
        if self.is_dragging:
            # Update the current cursor position
            self.locked_cursor_x = event.x
            self.locked_cursor_y = event.y

            # Determine lasso direction
            if event.x > self.drag_start_x:
                self.lasso_direction = LassoDirection.LEFT_TO_RIGHT
            else:
                self.lasso_direction = LassoDirection.RIGHT_TO_LEFT

            # Instead of full redraw, just update the selection box
            self.canvas.delete("selection_box")
            self.canvas.create_rectangle(
                self.drag_start_x, self.drag_start_y,
                self.locked_cursor_x, self.locked_cursor_y,
                outline="blue",
                width=2,
                dash=(4, 4),
                tags=("selection_box",)
            )

            # Force update to make the dragging smoother
            self.canvas.update_idletasks()

    def on_canvas_release(self, event: Any) -> None:
        """Handle mouse release after dragging."""
        if not self.is_dragging:
            return

        self.is_dragging = False
        elements_selected = False  # Track if any elements were successfully selected

        # If we have a small drag distance, treat it as a click
        if (abs(event.x - self.drag_start_x) < 5 and
                abs(event.y - self.drag_start_y) < 5):
            # Find the element under the cursor
            element_id = self.find_element_at_position(event.x, event.y)
            if element_id is not None:
                elements_selected = True
                if self.selection_mode == SelectionMode.NEW:
                    # Start a new selection
                    self.selected_elements.clear()
                    self.selected_elements.add(element_id)
                elif self.selection_mode == SelectionMode.ADD:
                    # Add to existing selection
                    self.selected_elements.add(element_id)
                elif self.selection_mode == SelectionMode.REMOVE:
                    # Remove from selection
                    self.selected_elements.discard(element_id)
        else:
            # Process lasso selection
            min_x = min(self.drag_start_x, event.x)
            max_x = max(self.drag_start_x, event.x)
            min_y = min(self.drag_start_y, event.y)
            max_y = max(self.drag_start_y, event.y)

            # Convert to model coordinates
            model_min_x, model_max_y = self.screen_to_model(min_x, min_y)
            model_max_x, model_min_y = self.screen_to_model(max_x, max_y)

            # Collect elements in the lasso selection
            selected_in_lasso = set()
            for element_id, element in self.elements.items():
                element_nodes = [self.nodes[node_id] for node_id in element.nodes if node_id in self.nodes]

                # Check if the element is within or intersecting the selection box
                is_inside = self.is_element_in_selection(
                    element_nodes, model_min_x, model_min_y, model_max_x, model_max_y
                )

                if is_inside:
                    selected_in_lasso.add(element_id)

            if selected_in_lasso:
                elements_selected = True
                if self.selection_mode == SelectionMode.NEW:
                    # Replace current selection
                    self.selected_elements = selected_in_lasso
                elif self.selection_mode == SelectionMode.ADD:
                    # Add to existing selection
                    self.selected_elements.update(selected_in_lasso)
                elif self.selection_mode == SelectionMode.REMOVE:
                    # Remove from selection
                    self.selected_elements.difference_update(selected_in_lasso)

        # Only clear selection if in NEW mode and nothing was selected
        if self.selection_mode == SelectionMode.NEW and not elements_selected:
            # Clicking in empty space clears selection
            self.selected_elements.clear()

        # Reset selection mode
        self.selection_mode = SelectionMode.NONE

        # Clear selection box and redraw
        self.canvas.delete("selection_box")
        self.render_mesh()

        # Update status
        self.status_var.set(f"Selected {len(self.selected_elements)} elements")

    def is_element_in_selection(self, element_nodes: List[Node],
                                min_x: float, min_y: float,
                                max_x: float, max_y: float) -> bool:
        """Check if an element is inside the selection box using a faster algorithm."""
        if not element_nodes:
            return False

        # For better performance, first check if any node is inside the box
        # This avoids more expensive calculations in many cases
        any_node_inside = any(
            min_x <= node.x <= max_x and min_y <= node.y <= max_y
            for node in element_nodes
        )

        # For right-to-left selection (window crossing), any node inside is enough
        if self.lasso_direction == LassoDirection.RIGHT_TO_LEFT and any_node_inside:
            return True

        # For left-to-right selection (window enclosing), all nodes must be inside
        if self.lasso_direction == LassoDirection.LEFT_TO_RIGHT:
            return all(
                min_x <= node.x <= max_x and min_y <= node.y <= max_y
                for node in element_nodes
            )

        # If we get here, it's a right-to-left where no nodes are inside
        # We could check for intersections with the selection box, but for simplicity
        # we'll just return False
        return False

    def find_element_at_position(self, screen_x: float, screen_y: float) -> Optional[int]:
        """Find the element at the given screen position."""
        model_x, model_y = self.screen_to_model(screen_x, screen_y)

        # Check each element
        for element_id, element in self.elements.items():
            # Get the nodes for this element
            element_nodes = [self.nodes[node_id] for node_id in element.nodes if node_id in self.nodes]
            if len(element_nodes) < 3:
                continue

            # Create a polygon from the nodes
            polygon = [(node.x, node.y) for node in element_nodes]

            # Check if the point is inside the polygon
            if self.point_in_polygon(model_x, model_y, polygon):
                return element_id

        return None

    def point_in_polygon(self, x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
        """Check if a point is inside a polygon using ray casting algorithm."""
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

    def on_mouse_move(self, event: Any) -> None:
        """Handle mouse movement to update coordinates display."""
        model_x, model_y = self.screen_to_model(event.x, event.y)
        self.coords_var.set(f"X: {model_x:.2f}  Y: {model_y:.2f}")

    def on_mouse_wheel(self, event: Any) -> None:
        """Handle mouse wheel for zooming."""
        # Get model coordinates of cursor before zoom
        model_x, model_y = self.screen_to_model(event.x, event.y)

        # Store the original zoom level
        old_zoom = self.zoom_level

        # Determine zoom direction and calculate new zoom level
        if event.delta > 0 or event.num == 4:  # Zoom in
            self.zoom_level *= 1.1
        else:  # Zoom out
            self.zoom_level /= 1.1

        # Calculate how the screen point would change with the new zoom
        # if we didn't adjust the pan offset
        new_screen_x, new_screen_y = self.model_to_screen(model_x, model_y)

        # Adjust pan offset to keep the cursor over the same model point
        self.pan_offset_x += event.x - new_screen_x
        self.pan_offset_y -= (event.y - new_screen_y)  # Y is inverted

        # Redraw the mesh with new zoom level and pan offset
        self.render_mesh()

        # Update status to show current zoom level
        zoom_percent = int(self.zoom_level * 100)
        self.status_var.set(f"Zoom: {zoom_percent}%")

    def on_pan_start(self, event: Any) -> None:
        """Handle start of panning with middle mouse button."""
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_pan_motion(self, event: Any) -> None:
        """Handle panning with middle mouse button."""
        # Calculate the difference
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        # Update pan offset
        self.pan_offset_x += dx
        self.pan_offset_y -= dy  # Invert Y for proper panning

        # Update drag start position
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        self.render_mesh()

    def on_escape(self, event: Any) -> None:
        """Handle ESC key to clear selection."""
        self.selected_elements.clear()
        self.render_mesh()
        self.status_var.set("Selection cleared")

    def select_by_material(self) -> None:
        """Select all elements with the specified material number."""
        try:
            material = int(self.material_var.get())
            count = 0

            for element_id, element in self.elements.items():
                if element.material == material:
                    self.selected_elements.add(element_id)
                    count += 1

            self.render_mesh()
            self.status_var.set(f"Selected {count} elements with material {material}")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid material number")

    def select_by_step(self) -> None:
        """Select all elements with the specified step number."""
        try:
            step = int(self.step_var.get())
            count = 0

            for element_id, element in self.elements.items():
                if element.step == step:
                    self.selected_elements.add(element_id)
                    count += 1

            self.render_mesh()
            self.status_var.set(f"Selected {count} elements with step {step}")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid step number")

    def assign_to_selection(self) -> None:
        """Assign material and/or step to the selected elements."""
        if not self.selected_elements:
            messagebox.showinfo("Info", "No elements selected")
            return

        try:
            material = None
            step = None

            # Get material if provided
            material_str = self.assign_material_var.get()
            if material_str:
                material = int(material_str)

            # Get step if provided
            step_str = self.assign_step_var.get()
            if step_str:
                step = int(step_str)

            if material is None and step is None:
                messagebox.showinfo("Info", "Please enter a material number or step number to assign")
                return

            self.update_elements(material, step)
            self.render_mesh()

            # Update status message
            msg_parts = []
            if material is not None:
                msg_parts.append(f"material={material}")
            if step is not None:
                msg_parts.append(f"step={step}")

            self.status_var.set(f"Assigned {', '.join(msg_parts)} to {len(self.selected_elements)} elements")

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")

    def update_elements(self, material: Optional[int], step: Optional[int]) -> None:
        """Update the material and/or step of selected elements."""
        if not self.file_content:
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

    def save_file(self) -> None:
        """Save the modified CANDE input file."""
        if not self.filepath or not self.file_content:
            messagebox.showinfo("Info", "No file loaded")
            return

        # Ask for save location
        save_path = filedialog.asksaveasfilename(
            title="Save CANDE Input File",
            defaultextension=".cid",
            initialfile=self.filepath,
            filetypes=[("CANDE Input Files", "*.cid"), ("All Files", "*.*")]
        )

        if not save_path:
            return

        try:
            with open(save_path, 'w') as file:
                file.writelines(self.file_content)

            self.status_var.set(f"File saved as {save_path}")
            messagebox.showinfo("Success", "File saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")


def main() -> None:
    """Main function to start the application."""
    app = CandeEditor()
    app.root.mainloop()


if __name__ == "__main__":
    main()