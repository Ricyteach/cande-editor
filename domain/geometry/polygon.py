from typing import List, Tuple
from pydantic import Field, field_validator, model_validator
from domain.geometry.point import Point
from domain.geometry.line import Line
from domain.geometry.constants import EPSILON
from utils.registry import RegisteredModel


class Polygon(RegisteredModel):
    """
    Represents a closed polygon defined by a sequence of vertices.

    The polygon is automatically oriented counter-clockwise and validates
    that it doesn't self-intersect.
    """
    vertices: List[Point] = Field(description="List of vertices defining the polygon")

    @field_validator("vertices")
    @classmethod
    def validate_vertices(cls, v: List[Point]) -> List[Point]:
        """Validate that we have enough vertices and they're all unique."""
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 vertices")

        # Check for duplicate consecutive vertices
        for i in range(len(v)):
            current = v[i]
            next_idx = (i + 1) % len(v)
            if current.is_close_to(v[next_idx]):
                raise ValueError(f"Consecutive vertices {i} and {next_idx} are too close")

        return v

    @field_validator("vertices", mode="after")
    @classmethod
    def ensure_counter_clockwise(cls, vertices: List[Point]) -> List[Point]:
        """Ensure vertices are ordered counter-clockwise."""
        # Calculate signed area to determine orientation
        area = 0.0
        for i in range(len(vertices)):
            current = vertices[i]
            next_vertex = vertices[(i + 1) % len(vertices)]
            area += current.x * next_vertex.y - next_vertex.x * current.y
        area /= 2.0

        # If area is negative, vertices are clockwise - reverse them
        if area < 0:
            return vertices[::-1]
        return vertices

    @model_validator(mode="after")
    def validate_no_self_intersection(self):
        """Validate that the polygon doesn't self-intersect."""
        edges = self.edges
        for i, edge1 in enumerate(edges):
            for j, edge2 in enumerate(edges[i + 2:], start=i + 2):
                # Check adjacent edges separately to handle shared vertex
                if j - i == 1 or (i == 0 and j == len(edges) - 1):
                    # Adjacent edges share a vertex, only check for crossing
                    if self._edges_cross_improperly(edge1, edge2):
                        raise ValueError(f"Polygon self-intersects at edges {i} and {j}")
                else:
                    # Non-adjacent edges
                    if edge1.intersect(edge2) is not None:
                        raise ValueError(f"Polygon self-intersects at edges {i} and {j}")
        return self

    @staticmethod
    def _edges_cross_improperly(edge1: Line, edge2: Line, tolerance: float = EPSILON) -> bool:
        """Check if two edges cross improperly (not just at endpoints)."""
        intersection = edge1.intersect(edge2, tolerance)
        if intersection is None:
            return False

        # Check if intersection is at an endpoint of either edge
        end_points = [edge1.start, edge1.end, edge2.start, edge2.end]
        for end_point in end_points:
            if intersection.is_close_to(end_point, tolerance):
                return False

        return True

    @property
    def edges(self) -> List[Line]:
        """Get all edges of the polygon as Line objects."""
        edges = []
        for i in range(len(self.vertices)):
            start = self.vertices[i]
            end = self.vertices[(i + 1) % len(self.vertices)]
            # Skip edges with identical vertices (should not happen after validation)
            if not start.is_close_to(end):
                edges.append(Line(start=start, end=end))
        return edges

    @property
    def area(self) -> float:
        """Calculate the signed area of the polygon using the shoelace formula."""
        area = 0.0
        for i in range(len(self.vertices)):
            current = self.vertices[i]
            next_vertex = self.vertices[(i + 1) % len(self.vertices)]
            area += current.x * next_vertex.y - next_vertex.x * current.y
        return area / 2.0

    @property
    def centroid(self) -> Point:
        """Calculate the centroid of the polygon."""
        if abs(self.area) < EPSILON:
            # For zero area, return average of vertices
            total_x = sum(v.x for v in self.vertices)
            total_y = sum(v.y for v in self.vertices)
            return Point(x=total_x / len(self.vertices), y=total_y / len(self.vertices))

        cx = 0.0
        cy = 0.0
        area = self.area

        for i in range(len(self.vertices)):
            current = self.vertices[i]
            next_vertex = self.vertices[(i + 1) % len(self.vertices)]
            cross = current.x * next_vertex.y - next_vertex.x * current.y
            cx += (current.x + next_vertex.x) * cross
            cy += (current.y + next_vertex.y) * cross

        factor = 1.0 / (6.0 * area)
        return Point(x=cx * factor, y=cy * factor)

    @property
    def bounding_box(self) -> Tuple[Point, Point]:
        """Get the bounding box as (min_point, max_point)."""
        min_x = min(v.x for v in self.vertices)
        max_x = max(v.x for v in self.vertices)
        min_y = min(v.y for v in self.vertices)
        max_y = max(v.y for v in self.vertices)

        return Point(x=min_x, y=min_y), Point(x=max_x, y=max_y)

    @property
    def perimeter(self) -> float:
        """Calculate the perimeter of the polygon."""
        perimeter = 0.0
        for edge in self.edges:
            perimeter += edge.length
        return perimeter

    def is_clockwise(self) -> bool:
        """Determine if the polygon is oriented clockwise."""
        # A positive area indicates counter-clockwise, negative indicates clockwise
        return self.area < 0

    def contains_point(self, point: Point, tolerance: float = None) -> bool:
        """
        Determine if a point is inside the polygon using ray casting algorithm.

        Args:
            point: The point to test
            tolerance: Tolerance for edge cases

        Returns:
            True if the point is inside the polygon
        """
        if tolerance is None:
            tolerance = EPSILON

        # Check if point is on the boundary
        for edge in self.edges:
            if edge.contains_point(point, tolerance):
                return True

        # Ray casting algorithm
        ray_end = Point(x=point.x + 1000.0, y=point.y)  # Far point to the right
        ray = Line(start=point, end=ray_end)

        intersection_count = 0
        for edge in self.edges:
            intersection = ray.intersect(edge)
            if intersection is not None:
                # Only count if intersection is to the right of the test point
                if intersection.x >= point.x:
                    intersection_count += 1

        # Point is inside if odd number of intersections
        return intersection_count % 2 == 1

    def is_convex(self) -> bool:
        """Determine if the polygon is convex."""
        if len(self.vertices) < 3:
            return False

        # Check if all angles turn in the same direction
        edges = self.edges

        # Calculate cross product for each consecutive edge pair
        cross_products = []
        for i in range(len(edges)):
            edge1 = edges[i]
            edge2 = edges[(i + 1) % len(edges)]

            # Cross product of the direction vectors
            v1 = edge1.direction_vector
            v2 = edge2.direction_vector
            cross = v1.x * v2.y - v1.y * v2.x
            cross_products.append(cross)

        # All cross products should have the same sign for a convex polygon
        if not cross_products:
            return False

        first_sign = cross_products[0] >= 0
        return all((cp >= 0) == first_sign for cp in cross_products)

    def __str__(self) -> str:
        """String representation of the polygon."""
        vertices_str = ", ".join(str(v) for v in self.vertices)
        return f"Polygon([{vertices_str}])"
