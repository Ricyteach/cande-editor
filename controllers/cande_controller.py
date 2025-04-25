"""
Main controller for CANDE Input File Editor.
"""
import tkinter as tk
from typing import Dict, Set, Optional, Tuple, Any, cast
from enum import Enum, auto
import logging

from models.cande_model import CandeModel
from views.main_window import MainWindow
from views.canvas_view import CanvasView, DisplayMode
from utils.constants import LINE_ELEMENT_WIDTH

# Configure logging
logger = logging.getLogger(__name__)


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


class CandeController:
    """Controller for the CANDE Editor application."""

    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the controller.

        Args:
            root: The root Tkinter window
        """
        # Create model and views
        self.model = CandeModel()
        self.main_window = MainWindow(root)
        self.canvas_view = CanvasView(self.main_window.canvas)

        # Selection state
        self.selection_mode = SelectionMode.NONE
        self.lasso_direction = LassoDirection.LEFT_TO_RIGHT
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.locked_cursor_x = 0
        self.locked_cursor_y = 0

        # Current display filter (None = show all)
        self.element_type_filter = None

        # Set up event handlers
        self._setup_callbacks()
        self._setup_bindings()

    def _setup_callbacks(self) -> None:
        """Set up callback functions for UI events."""
        callbacks = {
            "open_file": self.open_file,
            "save_file": self.save_file,
            "select_by_material": self.select_by_material,
            "select_by_step": self.select_by_step,
            "assign_to_selection": self.assign_to_selection,
            "display_change": self.on_display_change,
            "element_type_change": self.on_element_type_change,
            "line_width_change": self.on_line_width_change,
            "create_interfaces": self.create_interfaces,
        }
        self.main_window.set_callbacks(callbacks)

    def _setup_bindings(self) -> None:
        """Set up event bindings for the canvas."""
        # Mouse events
        canvas = self.main_window.canvas
        canvas.bind("<Button-1>", self.on_canvas_click)
        canvas.bind("<B1-Motion>", self.on_canvas_drag)
        canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        canvas.bind("<Motion>", self.on_mouse_move)

        # Key events
        root = self.main_window.root
        root.bind("<Control-Button-1>", self.on_ctrl_click)
        root.bind("<Shift-Button-1>", self.on_shift_click)
        root.bind("<Escape>", self.on_escape)
        root.bind("<Control-s>", lambda e: self.save_file())
        root.bind("<Control-o>", lambda e: self.open_file())
        root.bind("<Control-d>", lambda e: self.show_interface_debug_info())

        # Mouse wheel for zoom
        canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
        canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
        canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down

        # Middle mouse button for panning
        canvas.bind("<Button-2>", self.on_pan_start)  # Middle button on Linux
        canvas.bind("<Button-3>", self.on_pan_start)  # Right button as alternative
        canvas.bind("<B2-Motion>", self.on_pan_motion)
        canvas.bind("<B3-Motion>", self.on_pan_motion)

    def open_file(self) -> None:
        """Open a CANDE input file (.cid)."""
        filepath = self.main_window.get_open_filename()
        if not filepath:
            return

        if self.model.load_file(filepath):
            # Update window title
            self.main_window.root.title(f"CANDE Input File Editor - {filepath}")

            # Reset view and render
            self.canvas_view.zoom_to_fit(
                self.model.model_min_x,
                self.model.model_min_y,
                self.model.model_max_x,
                self.model.model_max_y
            )

            # Reset element type filter and update checkboxes to show all
            self.element_type_filter = None

            # Set all checkboxes to checked state
            self.main_window.show_all_var.set(True)
            self.main_window.show_1d_var.set(True)
            self.main_window.show_2d_var.set(True)
            self.main_window.show_interface_var.set(True)

            self.render_mesh()

            # Update status
            self.main_window.update_status(
                f"Loaded {len(self.model.nodes)} nodes and {len(self.model.elements)} elements"
            )
        else:
            self.main_window.show_message(
                "Error", f"Failed to open file: {filepath}", "error"
            )

    def save_file(self) -> None:
        """Save the modified CANDE input file."""
        if not self.model.filepath:
            self.main_window.show_message("Info", "No file loaded", "info")
            return

        # Ask for save location
        save_path = self.main_window.get_save_filename(self.model.filepath)
        if not save_path:
            return

        if self.model.save_file(save_path):
            self.main_window.update_status(f"File saved as {save_path}")
            self.main_window.show_message("Success", "File saved successfully", "info")
        else:
            self.main_window.show_message("Error", f"Failed to save file: {save_path}", "error")

    def render_mesh(self) -> None:
        """Render the mesh on the canvas with the selected filter types."""
        # Get the current line width value from the UI
        current_line_width = self.main_window.line_width_var.get()

        self.canvas_view.render_mesh(
            self.model.nodes,
            self.model.elements,
            self.model.selected_elements,
            self.model.max_material,
            self.model.max_step,
            self.element_type_filter,  # Pass the list of element types to filter
            current_line_width
        )

    def on_display_change(self, event: Any) -> None:
        """
        Handle display mode change between Material and Step.

        Args:
            event: The event that triggered the change
        """
        mode = self.main_window.display_var.get()
        if mode == "Material":
            self.canvas_view.set_display_mode(DisplayMode.MATERIAL)
        else:
            self.canvas_view.set_display_mode(DisplayMode.STEP)
        self.render_mesh()

    def on_element_type_change(self) -> None:
        """Handle element type selection change from checkboxes."""
        # Get selected element types from the UI
        selected_types = self.main_window.get_selected_element_types()

        # Update the element type filter based on selection
        if not selected_types:
            # If no types are selected, show nothing
            self.element_type_filter = []
            self.main_window.update_status("No element types selected for display")
        else:
            # Store the list of selected types
            self.element_type_filter = selected_types

            # Update status message
            if len(selected_types) == 3:
                self.main_window.update_status("Showing all element types")
            else:
                type_list = ", ".join(selected_types)
                self.main_window.update_status(f"Showing only {type_list} elements")

        # Re-render with the new filter
        self.render_mesh()

    def on_line_width_change(self) -> None:
        """Handle line width changes for 1D elements."""
        width = self.main_window.line_width_var.get()
        logger.info(f"1D element width changed to {width}")

        # Update the rendering with the new width
        self.render_mesh()

        # Update status bar
        self.main_window.update_status(f"1D element width set to {width}")

    def select_by_material(self) -> None:
        """Select all elements with the specified material number."""
        try:
            material = int(self.main_window.material_var.get())

            # Select elements that match both the material and current element type filter
            count = self.model.select_elements_by_material(
                material,
                element_type_filter=self.element_type_filter
            )

            self.render_mesh()

            # Update status message based on filter
            if self.element_type_filter:
                self.main_window.update_status(
                    f"Selected {count} {self.element_type_filter} elements with material {material}"
                )
            else:
                self.main_window.update_status(
                    f"Selected {count} elements with material {material}"
                )

        except ValueError:
            self.main_window.show_message("Error", "Please enter a valid material number", "error")

    def select_by_step(self) -> None:
        """Select all elements with the specified step number."""
        try:
            step = int(self.main_window.step_var.get())

            # Select elements that match both the step and current element type filter
            count = self.model.select_elements_by_step(
                step,
                element_type_filter=self.element_type_filter
            )

            self.render_mesh()

            # Update status message based on filter
            if self.element_type_filter:
                self.main_window.update_status(
                    f"Selected {count} {self.element_type_filter} elements with step {step}"
                )
            else:
                self.main_window.update_status(
                    f"Selected {count} elements with step {step}"
                )

        except ValueError:
            self.main_window.show_message("Error", "Please enter a valid step number", "error")

    def assign_to_selection(self) -> None:
        """Assign material and/or step to the selected elements."""
        if not self.model.selected_elements:
            self.main_window.show_message("Info", "No elements selected", "info")
            return

        try:
            material = None
            step = None

            # Get material if provided
            material_str = self.main_window.assign_material_var.get()
            if material_str:
                material = int(material_str)

            # Get step if provided
            step_str = self.main_window.assign_step_var.get()
            if step_str:
                step = int(step_str)

            if material is None and step is None:
                self.main_window.show_message(
                    "Info", "Please enter a material number or step number to assign", "info"
                )
                return

            # Only update elements that match the current element type filter
            updated_count = self.model.update_elements(
                material,
                step,
                element_type_filter=self.element_type_filter
            )
            self.render_mesh()

            # Update status message
            msg_parts = []
            if material is not None:
                msg_parts.append(f"material={material}")
            if step is not None:
                msg_parts.append(f"step={step}")

            # Include element type in status message if filtered
            if self.element_type_filter:
                self.main_window.update_status(
                    f"Assigned {', '.join(msg_parts)} to {updated_count} {self.element_type_filter} elements"
                )
            else:
                self.main_window.update_status(
                    f"Assigned {', '.join(msg_parts)} to {updated_count} elements"
                )

        except ValueError:
            self.main_window.show_message("Error", "Please enter valid numbers", "error")

    def on_canvas_click(self, event: Any) -> None:
        """
        Handle canvas click event.

        Args:
            event: The event that triggered the click
        """
        # Store the starting point for drag operations
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.locked_cursor_x = event.x
        self.locked_cursor_y = event.y
        self.is_dragging = True
        self.canvas_view.is_dragging = True

        # By default, a new click will start a new selection (without Ctrl/Shift)
        if self.selection_mode == SelectionMode.NONE:
            self.selection_mode = SelectionMode.NEW

    def on_ctrl_click(self, event: Any) -> None:
        """
        Handle Ctrl+Click for adding to element selection.

        Args:
            event: The event that triggered the click
        """
        self.selection_mode = SelectionMode.ADD
        self.on_canvas_click(event)

    def on_shift_click(self, event: Any) -> None:
        """
        Handle Shift+Click for removing from element selection.

        Args:
            event: The event that triggered the click
        """
        self.selection_mode = SelectionMode.REMOVE
        self.on_canvas_click(event)

    def on_canvas_drag(self, event: Any) -> None:
        """
        Handle mouse drag on canvas for selection box.

        Args:
            event: The event that triggered the drag
        """
        if self.is_dragging:
            # Update the current cursor position
            self.locked_cursor_x = event.x
            self.locked_cursor_y = event.y
            self.canvas_view.locked_cursor_x = event.x
            self.canvas_view.locked_cursor_y = event.y

            # Determine lasso direction
            if event.x > self.drag_start_x:
                self.lasso_direction = LassoDirection.LEFT_TO_RIGHT
            else:
                self.lasso_direction = LassoDirection.RIGHT_TO_LEFT

            # Update the selection box
            self.canvas_view.draw_selection_box(
                self.drag_start_x, self.drag_start_y,
                self.locked_cursor_x, self.locked_cursor_y
            )

    def on_canvas_release(self, event: Any) -> None:
        """
        Handle mouse release after dragging.

        Args:
            event: The event that triggered the release
        """
        if not self.is_dragging:
            return

        self.is_dragging = False
        self.canvas_view.is_dragging = False
        elements_selected = False  # Track if any elements were successfully selected

        # If we have a small drag distance, treat it as a click
        if (abs(event.x - self.drag_start_x) < 5 and
                abs(event.y - self.drag_start_y) < 5):
            # Find the element under the cursor
            current_line_width = self.main_window.line_width_var.get()
            element_id = self.canvas_view.find_element_at_position(
                event.x, event.y, self.model.nodes, self.model.elements, self.element_type_filter,
                current_line_width
            )
            if element_id is not None:
                elements_selected = True
                if self.selection_mode == SelectionMode.NEW:
                    # Start a new selection
                    self.model.selected_elements.clear()
                    self.model.selected_elements.add(element_id)
                elif self.selection_mode == SelectionMode.ADD:
                    # Add to existing selection
                    self.model.selected_elements.add(element_id)
                elif self.selection_mode == SelectionMode.REMOVE:
                    # Remove from selection
                    self.model.selected_elements.discard(element_id)
        else:
            # Process lasso selection
            min_x = min(self.drag_start_x, event.x)
            max_x = max(self.drag_start_x, event.x)
            min_y = min(self.drag_start_y, event.y)
            max_y = max(self.drag_start_y, event.y)

            # Convert to model coordinates
            model_min_x, model_max_y = self.canvas_view.screen_to_model(min_x, min_y)
            model_max_x, model_min_y = self.canvas_view.screen_to_model(max_x, max_y)

            # Collect elements in the lasso selection
            selected_in_lasso = self._find_elements_in_lasso(
                model_min_x, model_min_y, model_max_x, model_max_y
            )

            if selected_in_lasso:
                elements_selected = True
                if self.selection_mode == SelectionMode.NEW:
                    # Replace current selection
                    self.model.selected_elements = selected_in_lasso
                elif self.selection_mode == SelectionMode.ADD:
                    # Add to existing selection
                    self.model.selected_elements.update(selected_in_lasso)
                elif self.selection_mode == SelectionMode.REMOVE:
                    # Remove from selection
                    self.model.selected_elements.difference_update(selected_in_lasso)

        # Only clear selection if in NEW mode and nothing was selected
        if self.selection_mode == SelectionMode.NEW and not elements_selected:
            # Clicking in empty space clears selection
            self.model.selected_elements.clear()

        # Reset selection mode
        self.selection_mode = SelectionMode.NONE

        # Clear selection box and redraw
        self.canvas_view.canvas.delete("selection_box")
        self.render_mesh()

        # Update status
        self.main_window.update_status(f"Selected {len(self.model.selected_elements)} elements")

    def element_matches_filter(self, model, element) -> bool:
        """
        Check if an element matches the current type filter list.

        Args:
            model: The CandeModel instance
            element: The element to check

        Returns:
            True if the element matches any filter in the list or if the list is empty
        """
        # If filter is empty list, show nothing
        if not self.element_type_filter:
            return False

        # If filter is None (legacy "All" selection), show everything
        if self.element_type_filter is None:
            return True

        # Check if element type is in the filter list
        for filter_type in self.element_type_filter:
            if model.element_matches_filter(element, filter_type):
                return True

        return False

    def _find_elements_in_lasso(self, min_x: float, min_y: float,
                                max_x: float, max_y: float) -> Set[int]:
        """
        Find elements within the lasso selection box.

        Args:
            min_x: Minimum X coordinate
            min_y: Minimum Y coordinate
            max_x: Maximum X coordinate
            max_y: Maximum Y coordinate

        Returns:
            Set of element IDs within the lasso
        """
        selected_elements = set()

        for element_id, element in self.model.elements.items():
            # Skip elements that don't match the current filter
            # FIXED: Use self.element_matches_filter instead of model.element_matches_filter
            if not self.element_matches_filter(self.model, element):
                continue

            element_nodes = [self.model.nodes[node_id] for node_id in element.nodes
                             if node_id in self.model.nodes]

            # Skip if we don't have valid nodes
            if not element_nodes:
                continue

            # Check selection criteria based on lasso direction
            is_inside = False

            if self.lasso_direction == LassoDirection.LEFT_TO_RIGHT:
                # Window selection (all nodes must be inside)
                is_inside = all(
                    min_x <= node.x <= max_x and min_y <= node.y <= max_y
                    for node in element_nodes
                )
            else:  # RIGHT_TO_LEFT
                # Crossing selection (any node inside is enough)
                is_inside = any(
                    min_x <= node.x <= max_x and min_y <= node.y <= max_y
                    for node in element_nodes
                )

            if is_inside:
                selected_elements.add(element_id)

        return selected_elements

    def on_mouse_move(self, event: Any) -> None:
        """
        Handle mouse movement to update coordinates display.

        Args:
            event: The event that triggered the move
        """
        model_x, model_y = self.canvas_view.screen_to_model(event.x, event.y)
        self.main_window.update_coordinates(model_x, model_y)

    def on_mouse_wheel(self, event: Any) -> None:
        """
        Handle mouse wheel for zooming.

        Args:
            event: The event that triggered the wheel movement
        """
        # Get model coordinates of cursor before zoom
        model_x, model_y = self.canvas_view.screen_to_model(event.x, event.y)

        # Store the original zoom level
        old_zoom = self.canvas_view.zoom_level

        # Determine zoom direction and calculate new zoom level
        if hasattr(event, 'delta') and event.delta > 0 or event.num == 4:  # Zoom in
            self.canvas_view.zoom_level *= 1.1
        else:  # Zoom out
            self.canvas_view.zoom_level /= 1.1

        # Calculate how the screen point would change with the new zoom
        # if we didn't adjust the pan offset
        new_screen_x, new_screen_y = self.canvas_view.model_to_screen(model_x, model_y)

        # Adjust pan offset to keep the cursor over the same model point
        self.canvas_view.pan_offset_x += event.x - new_screen_x
        self.canvas_view.pan_offset_y -= (event.y - new_screen_y)  # Y is inverted

        # Redraw the mesh with new zoom level and pan offset
        self.render_mesh()

        # Update status to show current zoom level
        zoom_percent = int(self.canvas_view.zoom_level * 100)
        self.main_window.update_status(f"Zoom: {zoom_percent}%")

    def on_pan_start(self, event: Any) -> None:
        """
        Handle start of panning with middle mouse button.

        Args:
            event: The event that triggered the pan start
        """
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_pan_motion(self, event: Any) -> None:
        """
        Handle panning with middle mouse button.

        Args:
            event: The event that triggered the pan motion
        """
        # Calculate the difference
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        # Update pan offset
        self.canvas_view.pan_offset_x += dx
        self.canvas_view.pan_offset_y -= dy  # Invert Y for proper panning

        # Update drag start position
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        # Redraw with the new pan offset
        self.render_mesh()

    def on_escape(self, event: Any) -> None:
        """
        Handle ESC key to clear selection.

        Args:
            event: The event that triggered the escape
        """
        self.model.selected_elements.clear()
        self.render_mesh()
        self.main_window.update_status("Selection cleared")

    def create_interfaces(self) -> None:
        """Create interface elements between beam elements and 2D elements."""
        if not self.model.nodes or not self.model.elements:
            self.main_window.show_message("Info", "No model loaded", "info")
            return

        # Check if there's a selection and if it contains any beam elements
        if not self.model.selected_elements:
            self.main_window.show_message(
                "Info",
                "No eligible nodes found for interface creation. Try selecting beam elements first.",
                "info"
            )
            return

        # Get friction value from UI (textbox)
        try:
            friction = float(self.main_window.friction_var.get())
            # Validate range
            if friction < 0.0 or friction > 1.0:
                raise ValueError("Friction must be between 0.0 and 1.0")
        except ValueError as e:
            # Show error and terminate
            self.main_window.show_message(
                "Error",
                f"Invalid friction value: {str(e)}. Please enter a valid number between 0.0 and 1.0.",
                "error"
            )
            self.main_window.update_status("Interface creation cancelled: Invalid friction value")
            return

        # Create interface elements with the specified friction value
        count = self.model.create_interfaces(self.model.selected_elements, friction)

        if count > 0:
            self.render_mesh()
            self.main_window.update_status(f"Created {count} interface elements with friction {friction:.2f}")
            self.main_window.show_message(
                "Success",
                f"Created {count} interface elements with friction {friction:.2f}",
                "info"
            )
        else:
            self.main_window.show_message(
                "Info",
                "No eligible nodes found for interface creation. Try selecting beam elements first.",
                "info"
            )

    def show_interface_debug_info(self) -> None:
        """
        Display a debug window showing interface elements and their properties.
        This is for testing purposes only.
        """
        import tkinter as ttk
        from models.element import InterfaceElement
        # Find all interface elements in the model
        interface_elements = {
            element_id: element for element_id, element in self.model.elements.items()
            if isinstance(element, InterfaceElement)
        }

        if not interface_elements:
            self.main_window.show_message(
                "Info",
                "No interface elements found in the model",
                "info"
            )
            return

        # Create debug window
        debug_window = tk.Toplevel(self.main_window.root)
        debug_window.title("Interface Elements Debug Info")
        debug_window.geometry("600x400")

        # Create frame for the table
        frame = ttk.Frame(debug_window)
        frame.pack(fill=tk.BOTH, expand=True)

        # Create table headers
        headers = ["Element ID", "Material", "Step", "Nodes (I,J,K)", "Friction", "Angle"]
        for col, header in enumerate(headers):
            ttk.Label(frame, text=header, font=("Arial", 10, "bold")).grid(
                row=0, column=col, padx=5, pady=5, sticky="w"
            )

        # Add table rows
        for row, (element_id, element) in enumerate(sorted(interface_elements.items()), start=1):
            # Element ID
            ttk.Label(frame, text=str(element_id)).grid(
                row=row, column=0, padx=5, pady=2, sticky="w"
            )

            # Material
            ttk.Label(frame, text=str(element.material)).grid(
                row=row, column=1, padx=5, pady=2, sticky="w"
            )

            # Step
            ttk.Label(frame, text=str(element.step)).grid(
                row=row, column=2, padx=5, pady=2, sticky="w"
            )

            # Nodes
            nodes_str = f"{element.nodes[0]},{element.nodes[1]},{element.nodes[2]}"
            ttk.Label(frame, text=nodes_str).grid(
                row=row, column=3, padx=5, pady=2, sticky="w"
            )

            # Friction
            ttk.Label(frame, text=f"{element.friction:.3f}").grid(
                row=row, column=4, padx=5, pady=2, sticky="w"
            )

            # Angle
            ttk.Label(frame, text=f"{element.angle:.1f}°").grid(
                row=row, column=5, padx=5, pady=2, sticky="w"
            )

        # Add close button
        ttk.Button(
            debug_window,
            text="Close",
            command=debug_window.destroy
        ).pack(pady=10)

        # Make the window modal
        debug_window.transient(self.main_window.root)
        debug_window.grab_set()

        # Update status bar
        self.main_window.update_status(f"Found {len(interface_elements)} interface elements")
