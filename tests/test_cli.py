"""Tests for the command line, the semantic diff and the viewer payload."""

from __future__ import annotations

from pathlib import Path

import pytest

from candejar.cli import main
from candejar.diff import diff_problems
from candejar.io import read_cid, write_cid
from candejar.model import Problem
from candejar.web import payload_for


def edited(source: Path, target: Path, **changes: object) -> Path:
    """Copy a file, applying field changes to the first matching element."""
    document = read_cid(source)
    index, record = next(document.records("C-4.L3"))
    for field, value in changes.items():
        record = record.set(field, value)
    write_cid(document.replaced(index, record), target)
    return target


class TestCheck:
    def test_clean_file_exits_zero(self, cid_path: Path) -> None:
        assert main(["check", str(cid_path)]) == 0

    def test_broken_file_exits_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        broken = tmp_path / "broken.cid"
        record = "    1    3    0    3    1    9  999    5"
        broken.write_bytes(f"{'C-2.L3':>25}!!{record}\r\nSTOP\r\n".encode("latin-1"))
        assert main(["check", str(broken)]) == 1
        assert "NELEM" in capsys.readouterr().out

    def test_severity_filter(
        self, level3_document_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["check", "--severity", "error", str(level3_document_path)])
        out = capsys.readouterr().out
        assert "note" not in out

    def test_missing_file_exits_two(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["check", "no/such/file.cid"]) == 2


class TestShow:
    def test_reports_the_shape_of_the_model(
        self, level3_document_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["show", str(level3_document_path)]) == 0
        out = capsys.readouterr().out
        assert "Level:" in out
        assert "1,288" in out  # element count, thousands-separated
        assert "Continuous Load Scaling" in out
        assert "B-3b.Plastic.A.Profile" in out  # uncatalogued lines are disclosed

    def test_outline(self, level3_document_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        main(["show", "--outline", str(level3_document_path)])
        assert "C-4.L3" in capsys.readouterr().out


class TestFmt:
    def test_round_trip_reported_as_unchanged(
        self, cid_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["fmt", str(cid_path)]) == 0
        assert "unchanged" in capsys.readouterr().out


class TestTypes:
    def test_lists_specs_and_their_provenance(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert main(["types"]) == 0
        out = capsys.readouterr().out
        assert "C-4.L3" in out
        assert "manual" in out and "inferred" in out

    def test_names_what_a_file_uses_that_is_not_catalogued(
        self, level3_document_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(["types", str(level3_document_path)])
        assert "B-2.Plastic" in capsys.readouterr().out


class TestDiff:
    def test_identical_files_have_no_differences(self, level3_document_path: Path) -> None:
        problem = Problem.read(str(level3_document_path))
        assert diff_problems(problem, problem) == []

    def test_material_move_is_described_in_words(
        self, level3_document_path: Path, tmp_path: Path
    ) -> None:
        target = edited(level3_document_path, tmp_path / "after.cid", material=99)
        changes = diff_problems(Problem.read(str(level3_document_path)), Problem.read(str(target)))
        details = [c.detail for c in changes]
        assert any("moved from material" in d and "to 99" in d for d in details)

    def test_step_move_is_described(self, level3_document_path: Path, tmp_path: Path) -> None:
        target = edited(level3_document_path, tmp_path / "after.cid", birth=9)
        changes = diff_problems(Problem.read(str(level3_document_path)), Problem.read(str(target)))
        assert any("moved from step" in c.detail for c in changes)

    def test_density_change_is_attributed_to_its_material(
        self, level3_document_path: Path, tmp_path: Path
    ) -> None:
        document = read_cid(level3_document_path)
        index, record = next(document.records("D-1"))
        target = tmp_path / "after.cid"
        write_cid(document.replaced(index, record.set("density", 137.0)), target)
        changes = diff_problems(Problem.read(str(level3_document_path)), Problem.read(str(target)))
        assert any("density" in c.detail and c.section == "materials" for c in changes)

    def test_cli_diff_runs(
        self, level3_document_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        target = edited(level3_document_path, tmp_path / "after.cid", material=42)
        assert main(["diff", str(level3_document_path), str(target)]) == 0
        assert "elements" in capsys.readouterr().out


class TestViewerPayload:
    def test_carries_everything_the_page_draws(self, level3_document_path: Path) -> None:
        payload = payload_for(Problem.read(str(level3_document_path)), level3_document_path)
        assert len(payload["nodes"]) == 800
        assert len(payload["elements"]) == 1288
        assert payload["extents"]["minX"] == pytest.approx(-243.98)
        assert payload["steps"] == [1, 2, 3, 4, 5, 6, 7, 8]
        assert payload["loadScaling"] == 2
        assert {"n", "nodes", "kind", "material", "birth", "index"} <= set(payload["elements"][0])

    def test_is_json_serialisable(self, cid_path: Path) -> None:
        import json

        json.dumps(payload_for(Problem.read(str(cid_path)), cid_path))

    def test_a_level_2_file_reports_no_mesh(self, tmp_path: Path) -> None:
        payload = payload_for(Problem.read("tests/fixtures/level2_plastic_trench_wsd.cid"), None)
        assert payload["hasMesh"] is False
        assert payload["elements"] == []
