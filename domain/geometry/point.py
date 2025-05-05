# domain/geometry/point.py
from pydantic import Field, field_validator
import math
from domain.geometry.constants import EPSILON
from utils.base_model import ImmutableModel


class Point(ImmutableModel):
    """
    Represents a 2D point in Cartesian coordinates.

    This class provides basic point operations needed for geometric calculations
    in engineering applications, with appropriate handling of floating-point precision.
    """
    x: float = Field(description="X coordinate")
    y: float = Field(description="Y coordinate")

    @field_validator("x", "y")
    @classmethod
    def validate_coordinates(cls, value: float) -> float:
        """Validate that coordinates are finite numbers."""
        if not math.isfinite(value):
            raise ValueError(f"Coordinate must be a finite number, got {value}")
        return value

    def distance_to(self, other: "Point") -> float:
        """Calculate the Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def is_close_to(self, other: "Point", tolerance: float = None) -> bool:
        """
        Check if this point is close to another point within the specified tolerance.

        Args:
            other: The point to compare with
            tolerance: Maximum distance between points to be considered equal.
                      If None, uses the default EPSILON value.

        Returns:
            True if points are within the tolerance distance of each other
        """
        if tolerance is None:
            tolerance = EPSILON
        return self.distance_to(other) <= tolerance

    def __add__(self, other: "Point") -> "Point":
        """Vector addition of two points."""
        return Point(x=self.x + other.x, y=self.y + other.y)

    def __sub__(self, other: "Point") -> "Point":
        """Vector subtraction of two points."""
        return Point(x=self.x - other.x, y=self.y - other.y)

    def scale(self, factor: float) -> "Point":
        """Scale the point coordinates by a factor."""
        return Point(x=self.x * factor, y=self.y * factor)

    def midpoint(self, other: "Point") -> "Point":
        """Calculate the midpoint between this point and another point."""
        return Point(x=(self.x + other.x) / 2, y=(self.y + other.y) / 2)

    def polar_angle(self) -> float:
        """
        Calculate the polar angle of the point (from origin).
        Returns angle in radians, in range [0, 2π).
        """
        angle = math.atan2(self.y, self.x)
        if angle < 0:
            angle += 2 * math.pi
        return angle

    def format_as_tuple(self) -> str:
        """Format the point as a tuple string."""
        return f"({self.x}, {self.y})"

    def __str__(self) -> str:
        """String representation of the point."""
        return self.format_as_tuple()
