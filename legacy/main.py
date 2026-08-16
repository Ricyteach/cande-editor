#!/usr/bin/env python3
"""
CANDE Input File Editor - Version 2.0

A GUI tool for editing CANDE input files (.cid), specifically for selecting
and modifying element material and step numbers.
"""
__version__ = "2.0"

import tkinter as tk
from controllers.cande_controller import CandeController


def main() -> None:
    """Main function to start the application."""
    root = tk.Tk()
    app = CandeController(root)
    root.mainloop()


if __name__ == "__main__":
    main()
