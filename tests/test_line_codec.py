"""Tests for the ``.cid`` line envelope, exercised against real files.

The central claim these tests defend is that the whole format is one rule --
``f"{name:>25}!!" + record`` -- so that a declarative field spec can drive both
the reader and the writer.  If these ever fail on a new fixture, the claim is
wrong and the codec design needs revisiting.
"""

from __future__ import annotations

import pytest

from candejar.io import RECORD_START, TERMINATOR, CommandLine, join_line, split_line


def test_record_start_is_column_28() -> None:
    assert RECORD_START == 27


class TestSplitLine:
    def test_splits_name_and_record(self) -> None:
        line = split_line("                   C-4.L3!!    1  687   42")
        assert line == CommandLine("C-4.L3", "    1  687   42")

    def test_keeps_trailing_whitespace_in_record(self) -> None:
        line = split_line("                   C-1.L3!!PREP    ")
        assert line is not None
        assert line.record == "PREP    "

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "STOP",
            "                         !!has no name",
            "too short",
            "                   C-4.L3! only one bang",
        ],
    )
    def test_returns_none_for_non_command_lines(self, text: str) -> None:
        assert split_line(text) is None


class TestJoinLine:
    def test_round_trips_a_split(self) -> None:
        text = "            D-2.Interface!!     9.080     0.300        10"
        line = split_line(text)
        assert line is not None
        assert join_line(line) == text

    def test_right_justifies_the_name(self) -> None:
        assert join_line(CommandLine("D-1", "x")).index("!!") == 25

    def test_rejects_an_overlong_name(self) -> None:
        with pytest.raises(ValueError, match="exceeds"):
            join_line(CommandLine("X" * 26, ""))


class TestField:
    """Manual column ranges are 1-based and inclusive."""

    def test_extracts_c4_fields(self) -> None:
        line = split_line("                   C-4.L3!!    1  687   42    0    0    7    1    0")
        assert line is not None
        assert line.field(1, 1) == " "  # LIMIT
        assert line.field(2, 5) == "   1"  # element number
        assert line.field(6, 10) == "  687"  # node I
        assert line.field(26, 30) == "    7"  # material
        assert line.field(31, 35) == "    1"  # birth load step
        assert line.field(36, 40) == "    0"  # element-class code

    def test_pads_a_short_record(self) -> None:
        line = CommandLine("C-4.L3", "    1")
        assert line.field(36, 40) == "     "

    def test_rejects_an_invalid_range(self) -> None:
        with pytest.raises(ValueError):
            CommandLine("D-1", "x").field(0, 3)


class TestAgainstRealFiles:
    def test_every_command_line_conforms(self, cid_lines: list[str], fixture_name: str) -> None:
        """No line may carry ``!!`` anywhere other than the envelope position."""
        for number, text in enumerate(cid_lines, start=1):
            if text == TERMINATOR or not text.strip():
                continue
            line = split_line(text)
            assert line is not None, f"{fixture_name}:{number} does not conform: {text!r}"
            assert "!!" not in line.name

    def test_line_round_trip_is_exact(self, cid_lines: list[str], fixture_name: str) -> None:
        for number, text in enumerate(cid_lines, start=1):
            line = split_line(text)
            if line is None:
                continue
            assert join_line(line) == text, f"{fixture_name}:{number} did not round-trip"

    def test_file_ends_with_stop(self, cid_lines: list[str]) -> None:
        assert cid_lines[-1] == TERMINATOR


class TestLevel3Fixture:
    """Counts asserted here are what the C-2.L3 control line claims."""

    def test_entity_counts_match_the_control_line(self, level3_lines: list[str]) -> None:
        names = [line.name for line in map(split_line, level3_lines) if line is not None]
        assert names.count("C-3.L3") == 800
        assert names.count("C-4.L3") == 1288
        assert names.count("C-5.L3") == 70

    def test_control_line_declares_continuous_load_scaling(self, level3_lines: list[str]) -> None:
        c2 = next(
            line
            for line in map(split_line, level3_lines)
            if line is not None and line.name == "C-2.L3"
        )
        assert c2.field(31, 35).strip() == "1288"  # NELEM, an exact count
        assert c2.field(56, 60).strip() == "2"  # Iscale == CLS-AAM-theta*
