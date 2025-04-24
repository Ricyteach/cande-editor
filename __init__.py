"""
CANDE Input File Editor - Package initialization
"""
import logging

# Configure logging to print to console
logging.basicConfig(
    level=logging.INFO,  # Set the threshold level for logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# This allows running the package directly
if __name__ == "__main__":
    from .main import main
    main()
