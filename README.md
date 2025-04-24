# CANDE Input File Editor

A GUI tool for editing CANDE input files (.cid), specifically for selecting and modifying element material and step numbers.

## Features

- Load and save CANDE input files (.cid)
- Visualize soil elements with color coding based on material or step number
- Select elements by clicking, dragging, or filtering by material/step
- Modify material and step numbers for selected elements
- Pan and zoom for easy navigation

## Requirements

- Python 3.6 or higher
- Tkinter (usually included with Python)

## Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Run `python main.py` to start the application

## Usage

### Opening a File

Click the "Open File" button or press Ctrl+O to open a CANDE input file (.cid).

### Navigating the View

- **Pan**: Middle-click or right-click and drag
- **Zoom**: Use the mouse wheel
- **Zoom to Fit**: Automatically done when opening a file

### Selecting Elements

- **Single Element**: Click on an element to select it
- **Multiple Elements**: 
  - Ctrl+Click to add elements to the selection
  - Shift+Click to remove elements from the selection
  - Drag from left to right to select elements completely inside the box
  - Drag from right to left to select elements touching the box
- **Clear Selection**: Press Escape or click in an empty area

### Filtering Elements

- **By Material**: Enter a material number and click "Select by Material"
- **By Step**: Enter a step number and click "Select by Step"
- **By Element Type**: Use the radio buttons to filter by 2D or 3D elements

### Modifying Elements

1. Select the elements you want to modify
2. Enter the new material and/or step number
3. Click "Assign to Selection"

### Display Mode

Use the "Display" dropdown to toggle between coloring elements by:
- Material Number
- Step Number

### Saving Changes

Click the "Save File" button or press Ctrl+S to save your changes to a CANDE input file.

## Project Structure

```
cande-editor/
├── main.py                  # Main entry point
├── models/                  # Data models
│   ├── __init__.py
│   ├── node.py              # Node model
│   ├── element.py           # Element models (2D/3D)
│   └── cande_model.py       # Main model for CANDE data
├── views/                   # UI components
│   ├── __init__.py
│   ├── main_window.py       # Main application window
│   └── canvas_view.py       # Canvas rendering
├── controllers/             # Application logic
│   ├── __init__.py
│   └── cande_controller.py  # Main controller
└── utils/                   # Utilities
    ├── __init__.py
    └── constants.py         # Application constants
```

## Key Bindings

- **Ctrl+O**: Open file
- **Ctrl+S**: Save file
- **Ctrl+Click**: Add to selection
- **Shift+Click**: Remove from selection
- **Escape**: Clear selection
- **Mouse Wheel**: Zoom in/out
- **Middle-Click Drag**: Pan view
- **Right-Click Drag**: Pan view (alternative)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.