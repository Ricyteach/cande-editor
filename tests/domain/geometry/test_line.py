import pytest
import math
from domain.geometry.point import Point
from domain.geometry.line import Line


class TestLine:
    def test_create_line(self):
        start = Point(x=0.0, y=0.0)
        end = Point(x=3.0, y=4.0)
        line = Line(start=start, end=end)

        assert line.start == start
        assert line.end == end

    def test_zero_length_line(self):
        point = Point(x=1.0, y=1.0)
        with pytest.raises(ValueError):
            Line(start=point, end=point)

    def test_length(self):
        line = Line(
            start=Point(x=0.0, y=0.0),
            end=Point(x=3.0, y=4.0)
        )
        assert line.length == 5.0

    def test_midpoint(self):
        line = Line(
            start=Point(x=1.0, y=2.0),
            end=Point(x=5.0, y=6.0)
        )
        midpoint = line.midpoint
        assert midpoint.x == 3.0
        assert midpoint.y == 4.0

    def test_direction_vector(self):
        line = Line(
            start=Point(x=1.0, y=2.0),
            end=Point(x=4.0, y=6.0)
        )
        direction = line.direction_vector
        assert direction.x == 3.0
        assert direction.y == 4.0

    def test_unit_direction_vector(self):
        line = Line(
            start=Point(x=0.0, y=0.0),
            end=Point(x=3.0, y=4.0)
        )
        unit_dir = line.unit_direction_vector
        assert unit_dir.x == pytest.approx(0.6)
        assert unit_dir.y == pytest.approx(0.8)

    def test_normal_vector(self):
        line = Line(
            start=Point(x=0.0, y=0.0),
            end=Point(x=1.0, y=0.0)
        )
        normal = line.normal_vector
        assert normal.x == 0.0
        assert normal.y == 1.0

    def test_angle(self):
        # Horizontal line
        line1 = Line(start=Point(x=0.0, y=0.0), end=Point(x=1.0, y=0.0))
        assert line1.angle == 0.0

        # Vertical line
        line2 = Line(start=Point(x=0.0, y=0.0), end=Point(x=0.0, y=1.0))
        assert line2.angle == pytest.approx(math.pi / 2)

        # 45-degree line
        line3 = Line(start=Point(x=0.0, y=0.0), end=Point(x=1.0, y=1.0))
        assert line3.angle == pytest.approx(math.pi / 4)

    def test_distance_to_point(self):
        line = Line(
            start=Point(x=0.0, y=0.0),
            end=Point(x=4.0, y=0.0)
        )

        # Point directly on the line
        assert line.distance_to_point(Point(x=2.0, y=0.0)) == pytest.approx(0.0)

        # Point above the line
        assert line.distance_to_point(Point(x=2.0, y=3.0)) == pytest.approx(3.0)

        # Point below the line
        assert line.distance_to_point(Point(x=2.0, y=-3.0)) == pytest.approx(3.0)

    def test_contains_point(self):
        line = Line(
            start=Point(x=0.0, y=0.0),
            end=Point(x=4.0, y=0.0)
        )

        # Point on the line
        assert line.contains_point(Point(x=2.0, y=0.0))

        # Point slightly off the line
        assert not line.contains_point(Point(x=2.0, y=0.1))

        # Point outside the segment but on the extended line
        assert not line.contains_point(Point(x=5.0, y=0.0))

    def test_project_point(self):
        line = Line(
            start=Point(x=0.0, y=0.0),
            end=Point(x=4.0, y=0.0)
        )

        # Start point
        assert line.project_point(Point(x=0.0, y=0.0)) == pytest.approx(0.0)

        # End point
        assert line.project_point(Point(x=4.0, y=0.0)) == pytest.approx(1.0)

        # Middle point
        assert line.project_point(Point(x=2.0, y=3.0)) == pytest.approx(0.5)

        # Beyond end
        assert line.project_point(Point(x=8.0, y=0.0)) == pytest.approx(2.0)

    def test_closest_point_to(self):
        line = Line(
            start=Point(x=0.0, y=0.0),
            end=Point(x=4.0, y=0.0)
        )

        # Point above the line
        closest = line.closest_point_to(Point(x=2.0, y=3.0))
        assert closest.x == pytest.approx(2.0)
        assert closest.y == pytest.approx(0.0)

        # Point beyond the end
        closest = line.closest_point_to(Point(x=6.0, y=0.0))
        assert closest.x == pytest.approx(4.0)
        assert closest.y == pytest.approx(0.0)

        # Point before the start
        closest = line.closest_point_to(Point(x=-2.0, y=0.0))
        assert closest.x == pytest.approx(0.0)
        assert closest.y == pytest.approx(0.0)

    def test_intersect(self):
        # Intersecting lines
        line1 = Line(start=Point(x=0.0, y=0.0), end=Point(x=4.0, y=4.0))
        line2 = Line(start=Point(x=0.0, y=4.0), end=Point(x=4.0, y=0.0))

        intersection = line1.intersect(line2)
        assert intersection is not None
        assert intersection.x == pytest.approx(2.0)
        assert intersection.y == pytest.approx(2.0)

        # Non-intersecting lines
        line3 = Line(start=Point(x=0.0, y=0.0), end=Point(x=2.0, y=0.0))
        line4 = Line(start=Point(x=3.0, y=0.0), end=Point(x=4.0, y=0.0))

        assert line3.intersect(line4) is None

        # Parallel lines
        line5 = Line(start=Point(x=0.0, y=0.0), end=Point(x=1.0, y=0.0))
        line6 = Line(start=Point(x=0.0, y=1.0), end=Point(x=1.0, y=1.0))

        assert line5.intersect(line6) is None

    def test_is_parallel(self):
        # Parallel horizontal lines
        line1 = Line(start=Point(x=0.0, y=0.0), end=Point(x=1.0, y=0.0))
        line2 = Line(start=Point(x=0.0, y=1.0), end=Point(x=1.0, y=1.0))
        assert line1.is_parallel(line2)

        # Anti-parallel lines (opposite direction)
        line3 = Line(start=Point(x=1.0, y=0.0), end=Point(x=0.0, y=0.0))
        assert line1.is_parallel(line3)

        # Non-parallel lines
        line4 = Line(start=Point(x=0.0, y=0.0), end=Point(x=0.0, y=1.0))
        assert not line1.is_parallel(line4)

    def test_immutability(self):
        line = Line(
            start=Point(x=0.0, y=0.0),
            end=Point(x=1.0, y=1.0)
        )

        with pytest.raises(Exception):
            line.start = Point(x=2.0, y=2.0)

    def test_string_representation(self):
        line = Line(
            start=Point(x=0.0, y=0.0),
            end=Point(x=1.0, y=1.0)
        )
        assert str(line) == "Line((0.0, 0.0) -> (1.0, 1.0))"
