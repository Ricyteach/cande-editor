import pytest
import math
from domain.geometry.point import Point


class TestPoint:
    def test_create_point(self):
        p = Point(x=1.0, y=2.0)
        assert p.x == 1.0
        assert p.y == 2.0

    def test_invalid_coordinates(self):
        with pytest.raises(ValueError):
            Point(x=float('nan'), y=1.0)
        with pytest.raises(ValueError):
            Point(x=1.0, y=float('inf'))

    def test_distance_to(self):
        p1 = Point(x=0.0, y=0.0)
        p2 = Point(x=3.0, y=4.0)
        assert p1.distance_to(p2) == 5.0
        assert p2.distance_to(p1) == 5.0

    def test_is_close_to(self):
        p1 = Point(x=1.0, y=1.0)
        p2 = Point(x=1.0 + 1e-11, y=1.0)
        p3 = Point(x=1.1, y=1.0)

        assert p1.is_close_to(p2)  # Using default EPSILON
        assert not p1.is_close_to(p3)

        # With custom tolerance
        assert p1.is_close_to(p3, tolerance=0.2)
        assert not p1.is_close_to(p3, tolerance=0.05)

    def test_vector_addition(self):
        p1 = Point(x=1.0, y=2.0)
        p2 = Point(x=3.0, y=4.0)
        p3 = p1 + p2

        assert p3.x == 4.0
        assert p3.y == 6.0

    def test_vector_subtraction(self):
        p1 = Point(x=3.0, y=5.0)
        p2 = Point(x=1.0, y=2.0)
        p3 = p1 - p2

        assert p3.x == 2.0
        assert p3.y == 3.0

    def test_scaling(self):
        p1 = Point(x=2.0, y=3.0)
        p2 = p1.scale(2.5)

        assert p2.x == 5.0
        assert p2.y == 7.5

    def test_midpoint(self):
        p1 = Point(x=1.0, y=2.0)
        p2 = Point(x=5.0, y=6.0)
        mid = p1.midpoint(p2)

        assert mid.x == 3.0
        assert mid.y == 4.0

    def test_polar_angle(self):
        # Points on the axes
        assert Point(x=1.0, y=0.0).polar_angle() == 0.0
        assert Point(x=0.0, y=1.0).polar_angle() == pytest.approx(math.pi / 2)
        assert Point(x=-1.0, y=0.0).polar_angle() == pytest.approx(math.pi)
        assert Point(x=0.0, y=-1.0).polar_angle() == pytest.approx(3 * math.pi / 2)

        # Points in quadrants
        assert Point(x=1.0, y=1.0).polar_angle() == pytest.approx(math.pi / 4)
        assert Point(x=-1.0, y=1.0).polar_angle() == pytest.approx(3 * math.pi / 4)

    def test_immutability(self):
        p = Point(x=1.0, y=2.0)

        with pytest.raises(Exception):
            p.x = 3.0  # Should not be able to modify after creation

    def test_string_representation(self):
        p = Point(x=1.0, y=2.0)
        assert str(p) == "(1.0, 2.0)"
        assert p.format_as_tuple() == "(1.0, 2.0)"
