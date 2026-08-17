"""Tests for reading, editing and writing whole ``.cid`` documents."""

from __future__ import annotations

from pathlib import Path

import pytest

from candejar.io import (
    FieldDecodeError,
    Record,
    Verbatim,
    dumps,
    loads,
    read_cid,
    write_cid,
)


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
        if not unparsed:
            pytest.skip(f"{cid_path.name} is now fully catalogued")
        assert dumps(document).encode("latin-1") == cid_path.read_bytes()

    def test_some_fixture_still_exercises_uncatalogued_lines(self, fixtures_dir: Path) -> None:
        """The Verbatim path must stay covered as the catalogue grows.

        Fidelity for line types with no spec (invariant 2) is what makes it safe
        to ship a codec that covers part of a large format. Individual fixtures
        become fully catalogued over time -- that is progress -- but if *every*
        fixture did, this guarantee would silently stop being tested.
        """
        exercising = [
            path.name
            for path in sorted(fixtures_dir.glob("*.cid"))
            if any(isinstance(line, Verbatim) and "!!" in line.text for line in read_cid(path))
        ]
        assert exercising, "no fixture exercises the Verbatim path any more"

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
        materials = document.records("D-1")
        first = next(materials, None)
        if first is None:
            # Level 1 files carry their soil on C-2.L1 and have no D-1 at all.
            pytest.skip(f"{cid_path.name} defines no D-1 material")
        index, record = first
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


class TestNoOpWrites:
    """Writing the value a field already holds must not touch the bytes.

    The encoders render canonically; a file records how its author wrote it.
    Re-encoding an unchanged value used to rewrite the field, which across a
    2,886-file corpus affected 44 field kinds and 2.8 million fields.
    """

    def test_rewriting_a_real_keeps_the_authors_decimals(self) -> None:
        document = loads(f"{'C-3.L3':>25}!!    1  000   -300.00    -60.00\r\n")
        _, record = next(document.records("C-3.L3"))
        assert record.set("x", -300.0).render() == record.render()

    def test_rewriting_a_whole_keeps_leading_zeros(self) -> None:
        document = loads(f"{'C-3.L3':>25}!!    1  000   -300.00    -60.00\r\n")
        _, record = next(document.records("C-3.L3"))
        assert record.raw("generate") == "00"
        assert record.set("generate", 0).raw("generate") == "00"

    def test_rewriting_text_does_not_shift_it_left(self) -> None:
        """MATNAM is positional -- the manual says it starts in column 21."""
        document = loads(f"{'D-1':>25}!!    1    6         0 Inter # 1\r\n")
        _, record = next(document.records("D-1"))
        assert record.set("name", "Inter # 1").render() == record.render()

    def test_a_no_op_write_is_free_for_every_field_of_every_fixture(self, cid_path: Path) -> None:
        document = read_cid(cid_path)
        for line in document.lines:
            if not isinstance(line, Record):
                continue
            for spec_field in line.spec.fields:
                try:
                    value = line.get(spec_field.name)
                except FieldDecodeError:
                    continue  # malformed text is meant to be overwritten
                assert line.set(spec_field.name, value).render() == line.render(), (
                    f"{cid_path.name}: rewriting {line.name}.{spec_field.name} "
                    f"with its own value changed the line"
                )

    def test_a_real_change_still_writes(self) -> None:
        document = loads(f"{'C-3.L3':>25}!!    1  000   -300.00    -60.00\r\n")
        _, record = next(document.records("C-3.L3"))
        assert record.set("x", -301.0).float_at("x") == -301.0

    def test_an_unreadable_field_is_overwritten_not_preserved(self) -> None:
        """A write is exactly what junk in a column is for."""
        document = loads(f"{'C-4.L3':>25}!!    1  6x7   42\r\n")
        _, record = next(document.records("C-4.L3"))
        assert record.raw("i") == "  6x7"
        assert record.set("i", 687).int_at("i") == 687


class TestDecoding:
    def test_master_control(self, level3_document_path: Path) -> None:
        record = read_cid(level3_document_path).first("A-1")
        assert record is not None
        assert record.str_at("mode") == "ANALYS"
        assert record.int_at("level") == 3
        assert record.int_at("pipe_groups") == 9
        assert record.str_at("title") is not None
        assert "-999" not in str(record.str_at("title")), "title is eating a control field"

    def test_lrfd_load_factor_line(self) -> None:
        """E-1 carries the LRFD net load factor. User Manual 5.7.1."""
        document = loads(f"{'E-1':>25}!!    1   10      1.95Vertical earth load, max\r\n")
        record = document.first("E-1")
        assert record is not None
        assert record.int_at("first_step") == 1
        assert record.int_at("last_step") == 10
        assert record.float_at("factor") == 1.95
        assert record.str_at("comment") == "Vertical earth load, max"

    def test_steel_material_properties(self, fixtures_dir: Path) -> None:
        """B-1.Steel. User Manual 5.4.5.1."""
        record = read_cid(fixtures_dir / "level2_pipe_steel_wsd.cid").first("B-1.Steel")
        assert record is not None
        assert record.float_at("modulus") == 29_000_000.0
        assert record.float_at("poisson") == 0.3
        assert record.float_at("yield_stress") == 80_000.0
        assert record.float_at("seam_strength") == 80_000.0
        assert record.float_at("density") == 0.284
        assert record.int_at("behaviour") == 2  # bilinear
        assert record.int_at("joint_slip") == 0

    def test_steel_section_properties(self, fixtures_dir: Path) -> None:
        """B-2.Steel.A -- the numbers a corrugation library would supply.

        Per unit length of pipe, not totals. User Manual 5.4.5.2.
        """
        record = read_cid(fixtures_dir / "level2_pipe_steel_wsd.cid").first("B-2.Steel.A")
        assert record is not None
        assert record.float_at("area") == 0.04
        assert record.float_at("inertia") == 0.00333
        assert record.float_at("section_modulus") == 0.00668
        assert record.float_at("deep_modulus") is None  # not a deep corrugation

    def test_steel_lrfd_resistance_factors(self, fixtures_dir: Path) -> None:
        """B-3.Steel.AD.LRFD. User Manual 5.4.5.8."""
        record = read_cid(fixtures_dir / "level2_pipe_steel_lrfd.cid").first("B-3.Steel.AD.LRFD")
        assert record is not None
        assert record.float_at("phi_thrust") == 1.0
        assert record.float_at("phi_buckling") == 1.0
        assert record.float_at("phi_seam") == 1.0
        assert record.float_at("phi_plastic") == 1.0
        assert record.float_at("deflection_limit") == 5.0

    def test_aluminum_is_not_laid_out_like_steel(self, fixtures_dir: Path) -> None:
        """B-1.Alum has no joint-slip field, so NONLIN and IBUCK shift left.

        Assuming aluminum mirrored steel would read NONLIN out of PE2's columns.
        User Manual 5.4.1.1.
        """
        record = read_cid(fixtures_dir / "level3_aluminum_wsd.cid").first("B-1.Alum")
        assert record is not None
        assert record.float_at("modulus") == 10_000_000.0
        assert record.float_at("poisson") == 0.33
        assert record.float_at("yield_stress") == 24_000.0
        assert record.int_at("behaviour") == 2  # NONLIN at 61-65, not 66-70
        assert record.int_at("buckling") == 0
        assert "joint_slip" not in {f.name for f in record.spec.fields}

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
