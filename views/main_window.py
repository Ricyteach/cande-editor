"""
Main window view for CANDE Input File Editor.
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, Callable, Optional, List

from utils.constants import LINE_ELEMENT_WIDTH


class MainWindow:
    """Main application window for the CANDE Editor."""

    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the main window.

        Args:
            root: The root Tkinter window
        """
        self.root = root
        self.root.title("CANDE Input File Editor")
        self.root.geometry("1200x800")

        # Variables for UI controls
        self.display_var = tk.StringVar(value="Material")
        self.material_var = tk.StringVar()
        self.step_var = tk.StringVar()
        self.assign_material_var = tk.StringVar()
        self.assign_step_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.coords_var = tk.StringVar(value="X: 0.00  Y: 0.00")

        # Replace single radio button variable with checkbox variables
        self.show_all_var = tk.BooleanVar(value=True)
        self.show_1d_var = tk.BooleanVar(value=True)
        self.show_2d_var = tk.BooleanVar(value=True)
        self.show_interface_var = tk.BooleanVar(value=True)

        self.line_width_var = tk.IntVar(value=LINE_ELEMENT_WIDTH)  # Default from constants

        # Dictionary to store callback functions
        self.callbacks: Dict[str, Callable] = {}

        # Create UI components
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the user interface components."""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create toolbar frame
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)

        # Open file button
        self.open_btn = ttk.Button(toolbar, text="Open File")
        self.open_btn.pack(side=tk.LEFT, padx=5)

        # Save file button
        self.save_btn = ttk.Button(toolbar, text="Save File")
        self.save_btn.pack(side=tk.LEFT, padx=5)

        # Display mode selection
        ttk.Label(toolbar, text="Display:").pack(side=tk.LEFT, padx=5)
        self.display_combo = ttk.Combobox(
            toolbar,
            textvariable=self.display_var,
            values=["Material", "Step"],
            width=10,
            state="readonly"
        )
        self.display_combo.pack(side=tk.LEFT, padx=5)

        # Material number input for selection
        ttk.Label(toolbar, text="Material:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(toolbar, textvariable=self.material_var, width=5).pack(side=tk.LEFT)
        self.select_material_btn = ttk.Button(toolbar, text="Select by Material")
        self.select_material_btn.pack(side=tk.LEFT, padx=5)

        # Step number input for selection
        ttk.Label(toolbar, text="Step:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(toolbar, textvariable=self.step_var, width=5).pack(side=tk.LEFT)
        self.select_step_btn = ttk.Button(toolbar, text="Select by Step")
        self.select_step_btn.pack(side=tk.LEFT, padx=5)

        # Assign material/step to selection
        ttk.Label(toolbar, text="Assign Material:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(toolbar, textvariable=self.assign_material_var, width=5).pack(side=tk.LEFT)

        ttk.Label(toolbar, text="Assign Step:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(toolbar, textvariable=self.assign_step_var, width=5).pack(side=tk.LEFT)

        self.assign_btn = ttk.Button(toolbar, text="Assign to Selection")
        self.assign_btn.pack(side=tk.LEFT, padx=5)

        # CHANGE: Element type CHECKBOXES instead of radio buttons
        element_type_frame = ttk.LabelFrame(toolbar, text="Element Types")
        element_type_frame.pack(side=tk.LEFT, padx=5)

        self.all_checkbox = ttk.Checkbutton(
            element_type_frame,
            text="All",
            variable=self.show_all_var,
            command=self._handle_all_checkbox
        )
        self.all_checkbox.pack(anchor=tk.W)

        ttk.Separator(element_type_frame, orient='horizontal').pack(fill='x', pady=2)

        self.el1d_checkbox = ttk.Checkbutton(
            element_type_frame,
            text="1D Elements",
            variable=self.show_1d_var,
            command=self._handle_individual_checkbox
        )
        self.el1d_checkbox.pack(anchor=tk.W)

        self.el2d_checkbox = ttk.Checkbutton(
            element_type_frame,
            text="2D Elements",
            variable=self.show_2d_var,
            command=self._handle_individual_checkbox
        )
        self.el2d_checkbox.pack(anchor=tk.W)

        self.interface_checkbox = ttk.Checkbutton(
            element_type_frame,
            text="Interface Elements",
            variable=self.show_interface_var,
            command=self._handle_individual_checkbox
        )
        self.interface_checkbox.pack(anchor=tk.W)

        # Add 1D element width control
        line_width_frame = ttk.LabelFrame(toolbar, text="1D Element Width")
        line_width_frame.pack(side=tk.LEFT, padx=5)

        line_width_scale = ttk.Scale(
            line_width_frame,
            from_=1,
            to=10,
            orient=tk.HORIZONTAL,
            variable=self.line_width_var,
            length=100,
            command=lambda val: self.line_width_var.set(round(float(val)))  # Force integer values
        )
        line_width_scale.pack(side=tk.TOP, padx=5)

        # Add a spinbox for precise control
        line_width_spinbox = ttk.Spinbox(
            line_width_frame,
            from_=1,
            to=10,
            textvariable=self.line_width_var,
            width=2
        )
        line_width_spinbox.pack(side=tk.LEFT, padx=5)

        # Add interface friction input
        interface_frame = ttk.LabelFrame(toolbar, text="Interface Properties")
        interface_frame.pack(side=tk.LEFT, padx=5)

        ttk.Label(interface_frame, text="Friction:").pack(side=tk.LEFT, padx=2)
        self.friction_var = tk.StringVar(value="0.3")  # Default friction value as string
        friction_entry = ttk.Entry(
            interface_frame,
            textvariable=self.friction_var,
            width=5
        )
        friction_entry.pack(side=tk.LEFT, padx=2)

        # Create interfaces button
        self.create_interfaces_btn = ttk.Button(toolbar, text="Create Interfaces")
        self.create_interfaces_btn.pack(side=tk.LEFT, padx=5)

        # Canvas for rendering
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(canvas_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Status bar
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

        # Coordinates display
        coords_label = ttk.Label(main_frame, textvariable=self.coords_var, relief=tk.SUNKEN, anchor=tk.E)
        coords_label.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)

    def _handle_all_checkbox(self) -> None:
        """Handle the state change of the 'All' checkbox."""
        # When "All" is checked/unchecked, set all other checkboxes to match
        all_checked = self.show_all_var.get()
        self.show_1d_var.set(all_checked)
        self.show_2d_var.set(all_checked)
        self.show_interface_var.set(all_checked)

        # Trigger the element type change callback if it exists
        if "element_type_change" in self.callbacks:
            self.callbacks["element_type_change"]()

    def _handle_individual_checkbox(self) -> None:
        """Handle state changes of individual element type checkboxes."""
        # Update "All" checkbox based on individual selections
        if self.show_1d_var.get() and self.show_2d_var.get() and self.show_interface_var.get():
            self.show_all_var.set(True)
        else:
            self.show_all_var.set(False)

        # Trigger the element type change callback if it exists
        if "element_type_change" in self.callbacks:
            self.callbacks["element_type_change"]()

    def get_selected_element_types(self) -> List[str]:
        """Get a list of currently selected element types."""
        selected_types = []
        if self.show_1d_var.get():
            selected_types.append("1D")
        if self.show_2d_var.get():
            selected_types.append("2D")
        if self.show_interface_var.get():
            selected_types.append("Interface")
        return selected_types

    def set_callbacks(self, callbacks: Dict[str, Callable]) -> None:
        """
        Set callback functions for UI events.

        Args:
            callbacks: Dictionary mapping event names to callback functions
        """
        self.callbacks = callbacks

        # Connect UI elements to callbacks
        if "open_file" in callbacks:
            self.open_btn.config(command=callbacks["open_file"])

        if "save_file" in callbacks:
            self.save_btn.config(command=callbacks["save_file"])

        if "display_change" in callbacks:
            self.display_combo.bind("<<ComboboxSelected>>", callbacks["display_change"])

        if "select_by_material" in callbacks:
            self.select_material_btn.config(command=callbacks["select_by_material"])

        if "select_by_step" in callbacks:
            self.select_step_btn.config(command=callbacks["select_by_step"])

        if "assign_to_selection" in callbacks:
            self.assign_btn.config(command=callbacks["assign_to_selection"])

        if "line_width_change" in callbacks:
            self.line_width_var.trace("w", lambda *args: callbacks["line_width_change"]())

        if "create_interfaces" in callbacks:
            self.create_interfaces_btn.config(command=callbacks["create_interfaces"])

    def update_status(self, message: str) -> None:
        """
        Update the status bar message.

        Args:
            message: The message to display
        """
        self.status_var.set(message)

    def update_coordinates(self, x: float, y: float) -> None:
        """
        Update the coordinates display.

        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.coords_var.set(f"X: {x:.2f}  Y: {y:.2f}")

    def show_message(self, title: str, message: str, message_type: str = "info") -> None:
        """
        Show a message dialog.

        Args:
            title: Dialog title
            message: Message to display
            message_type: Type of message ("info", "error", or "warning")
        """
        if message_type == "error":
            messagebox.showerror(title, message)
        elif message_type == "warning":
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)

    def get_open_filename(self) -> Optional[str]:
        """
        Show file open dialog.

        Returns:
            Selected file path or None if cancelled
        """
        filepath = filedialog.askopenfilename(
            title="Open CANDE Input File",
            filetypes=[("CANDE Input Files", "*.cid"), ("All Files", "*.*")]
        )
        return filepath if filepath else None

    def get_save_filename(self, default_path: Optional[str] = None) -> Optional[str]:
        """
        Show file save dialog.

        Args:
            default_path: Default file path

        Returns:
            Selected file path or None if cancelled
        """
        filepath = filedialog.asksaveasfilename(
            title="Save CANDE Input File",
            defaultextension=".cid",
            initialfile=default_path,
            filetypes=[("CANDE Input Files", "*.cid"), ("All Files", "*.*")]
        )
        return filepath if filepath else None
