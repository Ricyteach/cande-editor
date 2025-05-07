from typing import Optional, Tuple
from pydantic import Field, field_validator, model_validator
import math
from domain.geometry.point import Point
from domain.geometry.constants import EPSILON
from utils.registry import RegisteredModel


class Line(RegisteredModel):
    """
    Represents a line segment defined by two points.

    This class provides operations for line segment calculations
    needed for engineering applications.
    """
    start: Point = Field(description="Starting point of the line segment")
    end: Point = Field(description="Ending point of the line segment")

    @field_validator("start", "end")
    @classmethod
    def validate_point(cls, v: Point) -> Point:
        """Ensure the point is valid."""
        if not isinstance(v, Point):
            raise ValueError(f"Expected Point object, got {type(v)}")
        return v

    @model_validator(mode="after")
    def validate_line_length(self):
        """Validate that the line has non-zero length."""
        if self.start.is_close_to(self.end):
            raise ValueError("Line cannot have zero length (start and end points are the same)")
        return self

    @property
    def length(self) -> float:
        """Get the length of the line segment."""
        return self.start.distance_to(self.end)

    @property
    def midpoint(self) -> Point:
        """Get the midpoint of the line segment."""
        return self.start.midpoint(self.end)

    @property
    def direction_vector(self) -> Point:
        """Get the direction vector from start to end (vector pointing along the line)."""
        return self.end - self.start

    @property
    def unit_direction_vector(self) -> Point:
        """Get the unit direction vector (normalized direction vector)."""
        return self.direction_vector.scale(1.0 / self.length)

    @property
    def normal_vector(self) -> Point:
        """Get the normal vector (perpendicular to the line, 90° counterclockwise rotation)."""
        direction = self.direction_vector
        return Point(x=-direction.y, y=direction.x)

    @property
    def unit_normal_vector(self) -> Point:
        """Get the unit normal vector (normalized normal vector)."""
        return self.normal_vector.scale(1.0 / self.length)

    @property
    def angle(self) -> float:
        """Get the angle of the line from start to end (in radians, measured from positive x-axis)."""
        return self.direction_vector.polar_angle()

    def distance_to_point(self, point: Point) -> float:
        """Calculate the perpendicular distance from a point to the line."""
        # Using the formula: |n·(p - p0)| / |n|
        # where n is the normal vector, p is the point, and p0 is a point on the line
        vec_to_point = point - self.start
        return abs(self.normal_vector.x * vec_to_point.x + self.normal_vector.y * vec_to_point.y) / self.length

    def contains_point(self, point: Point, tolerance: float = None) -> bool:
        """
        Check if a point lies on the line segment.

        Args:
            point: The point to check
            tolerance: Distance tolerance for considering the point to be on the line

        Returns:
            True if the point is on the line within the tolerance
        """
        if tolerance is None:
            tolerance = EPSILON

        # First check if point is within distance tolerance of the line
        if self.distance_to_point(point) > tolerance:
            return False

        # Check if point is within the bounds of the line segment
        # A point is on the segment if its projection onto the line is between 0 and 1
        t = self.project_point(point)
        return -tolerance <= t <= 1.0 + tolerance

    def project_point(self, point: Point) -> float:
        """
        Project a point onto the line and return the parameter t.

        The parameter t represents the position along the line:
        - t = 0 at the start point
        - t = 1 at the end point
        - t outside [0,1] means the projection falls outside the segment

        Returns:
            The parameter t indicating the projection position
        """
        vec_to_point = point - self.start
        direction = self.direction_vector
        t = (vec_to_point.x * direction.x + vec_to_point.y * direction.y) / (self.length ** 2)
        return t

    def closest_point_to(self, point: Point) -> Point:
        """
        Find the closest point on the line segment to a given point.

        Args:
            point: The point to find the closest point to

        Returns:
            The closest point on the line segment
        """
        t = self.project_point(point)

        # Clamp t to the range [0, 1] to stay within the segment
        t = max(0.0, min(1.0, t))

        # Calculate the point using the parameter t
        return Point(
            x=self.start.x + t * self.direction_vector.x,
            y=self.start.y + t * self.direction_vector.y
        )

    def intersect(self, other: "Line", tolerance: float = None) -> Optional[Point]:
        """
        Find the intersection point with another line segment.

        Args:
            other: The other line segment
            tolerance: Tolerance for considering lines to intersect

        Returns:
            The intersection point if it exists, None otherwise
        """
        if tolerance is None:
            tolerance = EPSILON

        # Line 1 represented as: P1 + t * dir1
        # Line 2 represented as: P2 + u * dir2

        d1x, d1y = self.direction_vector.x, self.direction_vector.y
        d2x, d2y = other.direction_vector.x, other.direction_vector.y

        # Determinant for line intersection
        det = d1x * d2y - d1y * d2x

        # Lines are parallel if determinant is close to zero
        if abs(det) < tolerance:
            return None

        # Calculate parameters for intersection
        dx = other.start.x - self.start.x
        dy = other.start.y - self.start.y

        t = (dx * d2y - dy * d2x) / det
        u = (dx * d1y - dy * d1x) / det

        # Check if intersection point is within both line segments
        if 0 <= t <= 1 and 0 <= u <= 1:
            return Point(
                x=self.start.x + t * d1x,
                y=self.start.y + t * d1y
            )

        return None

    def is_parallel(self, other: "Line", tolerance: float = None) -> bool:
        """
        Check if this line is parallel to another line.

        Args:
            other: The other line to check parallelism with
            tolerance: Angle tolerance in radians for considering lines parallel

        Returns:
            True if the lines are parallel within the tolerance
        """
        if tolerance is None:
            tolerance = EPSILON

        # Calculate the angle difference
        angle_diff = abs(self.angle - other.angle)

        # Normalize angle difference to [0, π]
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff

        # Check if lines are parallel or anti-parallel
        return angle_diff < tolerance or abs(angle_diff - math.pi) < tolerance

    def __str__(self) -> str:
        """String representation of the line."""
        return f"Line({self.start} -> {self.end})"
