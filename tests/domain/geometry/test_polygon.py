import pytest
from domain.geometry.point import Point
from domain.geometry.polygon import Polygon


class TestPolygon:
    def test_create_polygon(self):
        vertices = [
            Point(x=0.0, y=0.0),
            Point(x=1.0, y=0.0),
            Point(x=1.0, y=1.0),
            Point(x=0.0, y=1.0)
        ]
        polygon = Polygon(vertices=vertices)
        assert len(polygon.vertices) == 4

    def test_insufficient_vertices(self):
        with pytest.raises(ValueError):
            Polygon(vertices=[Point(x=0.0, y=0.0), Point(x=1.0, y=0.0)])

    def test_duplicate_consecutive_vertices(self):
        vertices = [
            Point(x=0.0, y=0.0),
            Point(x=1.0, y=0.0),
            Point(x=1.0, y=0.0),  # Duplicate
            Point(x=0.0, y=1.0)
        ]
        with pytest.raises(ValueError):
            Polygon(vertices=vertices)

    def test_area_calculation(self):
        # Square
        vertices = [
            Point(x=0.0, y=0.0),
            Point(x=1.0, y=0.0),
            Point(x=1.0, y=1.0),
            Point(x=0.0, y=1.0)
        ]
        polygon = Polygon(vertices=vertices)
        assert polygon.area == pytest.approx(1.0)

        # Triangle
        vertices = [
            Point(x=0.0, y=0.0),
            Point(x=2.0, y=0.0),
            Point(x=1.0, y=1.0)
        ]
        polygon = Polygon(vertices=vertices)
        assert polygon.area == pytest.approx(1.0)

    def test_orientation_normalization(self):
        # Clockwise square (will be normalized to CCW)
        cw_vertices = [
            Point(x=0.0, y=0.0),
            Point(x=0.0, y=1.0),
            Point(x=1.0, y=1.0),
            Point(x=1.0, y=0.0)
        ]
        polygon = Polygon(vertices=cw_vertices)
        assert not polygon.is_clockwise()  # Should be normalized to CCW
        assert polygon.area == pytest.approx(1.0)  # Area should be positive

    def test_centroid(self):
        # Square centered at origin
        vertices = [
            Point(x=-1.0, y=-1.0),
            Point(x=1.0, y=-1.0),
            Point(x=1.0, y=1.0),
            Point(x=-1.0, y=1.0)
        ]
        polygon = Polygon(vertices=vertices)
        centroid = polygon.centroid
        assert centroid.x == pytest.approx(0.0)
        assert centroid.y == pytest.approx(0.0)

    def test_bounding_box(self):
        vertices = [
            Point(x=1.0, y=1.0),
            Point(x=4.0, y=1.0),
            Point(x=3.0, y=4.0),
            Point(x=2.0, y=4.0)
        ]
        polygon = Polygon(vertices=vertices)
        min_point, max_point = polygon.bounding_box
        assert min_point.x == pytest.approx(1.0)
        assert min_point.y == pytest.approx(1.0)
        assert max_point.x == pytest.approx(4.0)
        assert max_point.y == pytest.approx(4.0)

    def test_perimeter(self):
        # Square
        vertices = [
            Point(x=0.0, y=0.0),
            Point(x=2.0, y=0.0),
            Point(x=2.0, y=2.0),
            Point(x=0.0, y=2.0)
        ]
        polygon = Polygon(vertices=vertices)
        assert polygon.perimeter == pytest.approx(8.0)

    def test_contains_point(self):
        # Square
        vertices = [
            Point(x=0.0, y=0.0),
            Point(x=2.0, y=0.0),
            Point(x=2.0, y=2.0),
            Point(x=0.0, y=2.0)
        ]
        polygon = Polygon(vertices=vertices)

        # Inside
        assert polygon.contains_point(Point(x=1.0, y=1.0))

        # On boundary
        assert polygon.contains_point(Point(x=1.0, y=0.0))
        assert polygon.contains_point(Point(x=0.0, y=1.0))

        # Outside
        assert not polygon.contains_point(Point(x=3.0, y=1.0))
        assert not polygon.contains_point(Point(x=1.0, y=-1.0))

    def test_is_convex(self):
        # Convex square
        convex_vertices = [
            Point(x=0.0, y=0.0),
            Point(x=1.0, y=0.0),
            Point(x=1.0, y=1.0),
            Point(x=0.0, y=1.0)
        ]
        convex_polygon = Polygon(vertices=convex_vertices)
        assert convex_polygon.is_convex()

        # Concave polygon (L-shape)
        concave_vertices = [
            Point(x=0.0, y=0.0),
            Point(x=2.0, y=0.0),
            Point(x=2.0, y=1.0),
            Point(x=1.0, y=1.0),
            Point(x=1.0, y=2.0),
            Point(x=0.0, y=2.0)
        ]
        concave_polygon = Polygon(vertices=concave_vertices)
        assert not concave_polygon.is_convex()

    @pytest.mark.skip
    def test_offset(self):
        # Square
        vertices = [
            Point(x=0.0, y=0.0),
            Point(x=1.0, y=0.0),
            Point(x=1.0, y=1.0),
            Point(x=0.0, y=1.0)
        ]
        polygon = Polygon(vertices=vertices)

        # Expand
        expanded = polygon.offset(0.5)
        assert expanded is not None
        assert expanded.area > polygon.area

        # Contract
        contracted = polygon.offset(-0.2)
        assert contracted is not None
        assert contracted.area < polygon.area

    def test_self_intersecting_polygon(self):
        # Self-intersecting polygon (bowtie)
        vertices = [
            Point(x=0.0, y=0.0),
            Point(x=2.0, y=2.0),
            Point(x=2.0, y=0.0),
            Point(x=0.0, y=2.0)
        ]
        with pytest.raises(ValueError):
            Polygon(vertices=vertices)

    def test_string_representation(self):
        vertices = [
            Point(x=0.0, y=0.0),
            Point(x=1.0, y=0.0),
            Point(x=1.0, y=1.0)
        ]
        polygon = Polygon(vertices=vertices)
        expected = "Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])"
        assert str(polygon) == expected
