# cande_editor.py
"""
CANDE Input File Editor - Main package module
"""
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Import main components to expose them at package level
from controllers.cande_controller import CandeController
from models.cande_model import CandeModel
from models.node import Node
from models.element import Element1D, Element2D, InterfaceElement
from views.main_window import MainWindow
from views.canvas_view import CanvasView

# Make them available when someone does 'import cande_editor'
__all__ = [
    'CandeController',
    'CandeModel',
    'Node',
    'Element1D',
    'Element2D',
    'InterfaceElement',
    'MainWindow',
    'CanvasView'
]

# This allows running the package directly
if __name__ == "__main__":
    from main import main
    main()
