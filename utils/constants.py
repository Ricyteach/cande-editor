"""
Constants for the CANDE Editor application.
"""

# Character positions (1-based in CANDE documentation, converted to 0-based for Python)
MATERIAL_START_POS = 52  # Material field starts at position 53 (1-based) -> 52 (0-based)
MATERIAL_END_POS = 57    # Material field ends at position 57 (1-based) -> 57 (0-based)
MATERIAL_FIELD_WIDTH = MATERIAL_END_POS - MATERIAL_START_POS

STEP_START_POS = 57      # Step field starts at position 58 (1-based) -> 57 (0-based)
STEP_END_POS = 62        # Step field ends at position 62 (1-based) -> 62 (0-based)
STEP_FIELD_WIDTH = STEP_END_POS - STEP_START_POS

# Width for line elements (1D elements)
LINE_ELEMENT_WIDTH = 3  # Default width for line elements

# CANDE colors for element rendering
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

# Application settings
DEFAULT_WINDOW_SIZE = "1200x800"
CANVAS_BG_COLOR = "white"
SELECTION_BOX_COLOR = "blue"
SELECTION_BOX_WIDTH = 2
SELECTION_BOX_DASH = (4, 4)
SELECTED_ELEMENT_COLOR = "red"
NORMAL_ELEMENT_COLOR = "black"
SELECTED_ELEMENT_WIDTH = 2
NORMAL_ELEMENT_WIDTH = 1
CANVAS_PADDING = 0.05  # 5% padding for zoom to fit
CLICK_THRESHOLD = 5  # Pixels to distinguish click from drag
ZOOM_FACTOR = 1.1  # Zoom in/out factor per mouse wheel tick

# TODO: resolve with unit system
# Standard physical constants
WATER_UNIT_WEIGHT = 9.81  # kN/m³ (SI units)
WATER_UNIT_WEIGHT_IMPERIAL = 62.4  # lb/ft³ (Imperial units)
