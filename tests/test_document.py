"""Tests for reading, editing and writing whole ``.cid`` documents."""

from __future__ import annotations

from pathlib import Path

import pytest

from candejar.io import Record, Verbatim, dumps, loads, read_cid, write_cid


class TestFidelity:
    """The property everything else depends on."""

    def test_round_trip_is_byte_identical(self, cid_path: Path) -> None:
        original = cid_path.read_bytes()
        assert dumps(read_cid(cid_path)).encode("latin-1") == original

    def test_write_then_read_is_stable(self, cid_path: Path, tmp_path: Path) -> None:
        out = tmp_path / cid_path.name
        write_cid(read_cid(cid_path), out)
        assert out.read_bytes() == cid_path.read_bytes()

    def test_uncatalogued_lines_survive(self, cid_path: Path) -> None:
        """Line types with no spec must still come back byte-for-byte."""
        document = read_cid(cid_path)
        unparsed = [line for line in document if isinstance(line, Verbatim) and "!!" in line.text]
        assert unparsed, "fixture no longer exercises uncatalogued line types"
        assert dumps(document).encode("latin-1") == cid_path.read_bytes()

    def test_lf_files_keep_lf(self) -> None:
        text = "                      D-1!!    1    1       120Soil\nSTOP\n"
        assert dumps(loads(text)) == text

    def test_a_file_without_a_trailing_newline_keeps_that(self) -> None:
        text = "                      D-1!!    1    1       120Soil\r\nSTOP"
        assert dumps(loads(text)) == text


class TestEditing:
    def test_setting_a_field_changes_only_those_columns(self) -> None:
        document = loads("                   C-4.L3!!    1  687   42    0    0    7    1    0\r\n")
        _, record = next(document.records("C-4.L3"))
        before = record.line.record

        after = record.set("material", 12).line.record

        assert after[25:30] == "   12"
        assert after[:25] == before[:25]
        assert after[30:] == before[30:]

    def test_editing_leaves_the_rest_of_the_file_alone(self, cid_path: Path) -> None:
        document = read_cid(cid_path)
        index, record = next(document.records("D-1"))
        edited = document.replaced(index, record.set("density", 137.5))

        original_lines = dumps(document).split(document.newline)
        edited_lines = dumps(edited).split(document.newline)
        pairs = zip(original_lines, edited_lines, strict=True)
        differing = [i for i, (a, b) in enumerate(pairs) if a != b]
        assert differing == [index]

    def test_a_written_value_reads_back(self) -> None:
        document = loads("                   C-4.L3!!    1  687   42    0    0    7    1    0\r\n")
        _, record = next(document.records("C-4.L3"))
        assert record.set("birth", 4).int_at("birth") == 4

    def test_a_value_too_wide_is_refused(self) -> None:
        document = loads("                   C-4.L3!!    1  687   42    0    0    7    1    0\r\n")
        _, record = next(document.records("C-4.L3"))
        with pytest.raises(ValueError, match="does not fit"):
            record.set("material", 123456)

    def test_an_unknown_field_names_the_alternatives(self) -> None:
        document = loads("                   C-4.L3!!    1  687   42\r\n")
        _, record = next(document.records("C-4.L3"))
        with pytest.raises(KeyError, match="material"):
            record.get("materail")


class TestDecoding:
    def test_master_control(self, level3_document_path: Path) -> None:
        record = read_cid(level3_document_path).first("A-1")
        assert record is not None
        assert record.str_at("mode") == "ANALYS"
        assert record.int_at("level") == 3
        assert record.int_at("pipe_groups") == 9
        assert record.str_at("title") is not None
        assert "-999" not in str(record.str_at("title")), "title is eating a control field"

    def test_control_line(self, level3_document_path: Path) -> None:
        record = read_cid(level3_document_path).first("C-2.L3")
        assert record is not None
        assert record.int_at("load_steps") == 10
        assert record.int_at("highest_node") == 800
        assert record.int_at("element_count") == 1288
        assert record.int_at("bandwidth") == 1
        assert record.int_at("load_scaling") == 2  # CLS-AAM-theta*

    def test_nodes_and_elements(self, level3_document_path: Path) -> None:
        document = read_cid(level3_document_path)
        node = document.first("C-3.L3")
        element = document.first("C-4.L3")
        assert node is not None and element is not None
        assert (node.int_at("node"), node.float_at("x"), node.float_at("y")) == (1, -243.98, 56.81)
        assert element.int_at("element") == 1
        assert element.int_at("i") == 687
        assert element.int_at("material") == 7
        assert element.int_at("code") == 0

    def test_interface_material_keeps_its_tensile_field(self, level3_document_path: Path) -> None:
        """The field the previous editor silently dropped."""
        record = read_cid(level3_document_path).first("D-2.Interface")
        assert record is not None
        assert record.float_at("angle") == 9.08
        assert record.float_at("friction") == 0.3
        assert record.float_at("tensile") == 10.0
        assert record.float_at("gap") is None

    def test_boundary_conditions_carry_live_loads(self, level3_document_path: Path) -> None:
        document = read_cid(level3_document_path)
        loaded = [r for _, r in document.records("C-5.L3") if (r.float_at("y_value") or 0.0) != 0.0]
        assert len(loaded) == 6
        assert loaded[0].float_at("y_value") == -400.0
        # Live-load steps must fall inside the window C-2b declares.
        c2b = document.first("C-2b.L3")
        assert c2b is not None
        start, end = c2b.int_at("live_load_start"), c2b.int_at("live_load_end")
        assert start is not None and end is not None
        assert all(start <= (r.int_at("step") or 0) <= end for r in loaded)

    def test_soil_and_interface_materials_are_separate_sequences(
        self, level3_document_path: Path
    ) -> None:
        document = read_cid(level3_document_path)
        materials = [r for _, r in document.records("D-1")]
        interface = [r.int_at("material") for r in materials if r.int_at("model") == 6]
        soil = [r.int_at("material") for r in materials if r.int_at("model") != 6]
        assert soil == [1, 2, 3, 4, 5]
        assert interface == list(range(1, 20))  # ids restart at 1


class TestRecordSelection:
    def test_records_filters_by_name(self, level3_document_path: Path) -> None:
        document = read_cid(level3_document_path)
        assert document.count("C-4.L3") == 1288
        assert document.count("nonexistent") == 0

    def test_records_with_no_filter_yields_every_record(self, level3_document_path: Path) -> None:
        document = read_cid(level3_document_path)
        assert len(list(document.records())) == sum(
            1 for line in document if isinstance(line, Record)
        )
