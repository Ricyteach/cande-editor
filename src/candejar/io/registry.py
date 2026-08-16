"""The catalogue of known ``.cid`` line types.

Only line types with a verified column table appear here.  Anything absent is
still read and written -- it simply arrives as an unparsed record whose text is
preserved byte-for-byte -- so the catalogue can grow one entry at a time without
ever risking fidelity.

Sources are recorded per spec.  ``Source.MANUAL`` means the columns were read
from a CANDE User Manual input-instruction table; ``Source.INFERRED`` means they
were derived from real files and cross-checked, but not yet confirmed against
the manual.  See ``docs/CID-FORMAT.md``.
"""

from __future__ import annotations

from candejar.io.spec import Field, LineSpec, Real, Source, Text, Whole

__all__ = ["LINE_TYPES", "spec_for"]

_TEXT = Text()
_INT = Whole()
_REAL = Real()


def _f(name: str, start: int, end: int, kind: object, doc: str = "") -> Field:
    return Field(name, start, end, kind, doc)  # type: ignore[arg-type]


_SPECS: tuple[LineSpec, ...] = (
    # ------------------------------------------------------------------ Part A
    LineSpec(
        name="A-1",
        doc="Master control.",
        source=Source.INFERRED,
        partial=True,
        fields=(
            _f("mode", 1, 6, _TEXT, "ANALYS, DESIGN or CHECK"),
            _f("level", 7, 10, _INT, "solution level: 1, 2 or 3"),
            _f("method", 11, 12, _INT, "evaluation method"),
            _f("pipe_groups", 13, 15, _INT, "number of pipe groups; Part A/B repeats"),
            _f("title", 16, 75, _TEXT, "free-text problem title"),
            # Four trailing control fields, confirmed present and 5 wide in both
            # Level 2 and Level 3 files, but not yet matched to manual names.
            _f("control_a", 76, 80, _INT, "purpose not yet pinned"),
            _f("control_b", 81, 85, _INT, "purpose not yet pinned"),
            _f("control_c", 86, 90, _INT, "purpose not yet pinned"),
            _f("control_d", 91, 95, _INT, "purpose not yet pinned"),
        ),
    ),
    LineSpec(
        name="A-2.L3",
        doc="Pipe selection, Level 3. One per pipe group.",
        source=Source.INFERRED,
        partial=True,
        fields=(
            _f("pipe_type", 1, 10, _TEXT, "ALUMINUM/BASIC/CONCRETE/CONRIB/CONTUBE/PLASTIC/STEEL"),
            _f("elements", 11, 15, _INT, "number of beam elements in this group"),
        ),
    ),
    LineSpec(
        name="A-2.L12",
        doc="Pipe selection, Levels 1 and 2.",
        source=Source.INFERRED,
        partial=True,
        fields=(_f("pipe_type", 1, 10, _TEXT), _f("elements", 11, 15, _INT)),
    ),
    # ------------------------------------------------------- Part C, Level 3
    LineSpec(
        name="C-1.L3",
        doc="Prep word and title.",
        source=Source.MANUAL,
        partial=True,
        fields=(_f("prep", 1, 4, _TEXT, "PREP"), _f("title", 5, 72, _TEXT)),
    ),
    LineSpec(
        name="C-2.L3",
        doc="Key control variables. User Manual 5.5.6.2.",
        source=Source.MANUAL,
        fields=(
            _f("load_steps", 1, 5, _INT, "NINC"),
            _f("mesh_print", 6, 10, _INT, "MGENPR"),
            _f("input_check", 11, 15, _INT, "NPUTCK"),
            _f("plot_control", 16, 20, _INT, "IPLOT"),
            _f("response_print", 21, 25, _INT, "IWRT: 0 minimal .. 4 plus Mohr/Coulomb trace"),
            _f("highest_node", 26, 30, _INT, "NPT -- highest node NUMBER used, not a count"),
            _f("element_count", 31, 35, _INT, "NELEM -- must match the element count exactly"),
            _f("boundary_count", 36, 40, _INT, "NBPTC -- upper bound; may exceed the actual count"),
            _f("soil_materials", 41, 45, _INT, "NSMAT -- GUI-only hint, ignored on batch input"),
            _f("interface_materials", 46, 50, _INT, "NXMAT -- GUI-only hint, ignored"),
            _f("bandwidth", 51, 55, _INT, "MINBW: 0 none, 1 minimise, 2 minimise and print"),
            _f("load_scaling", 56, 60, _INT, "Iscale: 0 off, 1 CLS-EBM, 2 CLS-AAM-theta*"),
        ),
    ),
    LineSpec(
        name="C-2b.L3",
        doc="Continuous Load Scaling for live loads. User Manual 5.5.6.3.",
        source=Source.MANUAL,
        fields=(
            _f("live_load_start", 1, 5, _INT, "LSstart"),
            _f("live_load_end", 6, 10, _INT, "LSstop"),
            _f("wheel_length", 11, 20, _REAL, "XLONG, in-plane footprint length"),
            _f("wheel_width", 21, 30, _REAL, "ZWIDE, out-of-plane footprint width"),
            _f("axle_spacing", 31, 40, _REAL, "SPACING"),
            _f("surface_node", 41, 45, _INT, "NDsurf"),
            _f("width_min", 46, 55, _REAL, "Wmin, minimum 3DSE distribution width"),
            _f("width_critical", 56, 65, _REAL, "Wcritical"),
            _f("group_first", 66, 70, _INT, "NGcrit1"),
            _f("group_last", 71, 75, _INT, "NGcrit2"),
            _f("pavement_3d", 76, 80, _INT, "Ipave3D"),
        ),
    ),
    LineSpec(
        name="C-3.L3",
        doc="Node input. User Manual 5.5.6.3. Columns beyond 30 not yet pinned.",
        source=Source.INFERRED,
        partial=True,
        fields=(
            _f("limit", 1, 1, _TEXT, "blank, or L on the last node line"),
            _f("node", 2, 5, _INT, "NNP -- may be given in any order"),
            _f("reference", 6, 8, _INT, "KRELAD: 0 plain, 1 x from node, 2 y from node, 3 both"),
            _f("generate", 9, 10, _INT, "MODEG"),
            _f("x", 11, 20, _REAL, "XCOORD"),
            _f("y", 21, 30, _REAL, "YCOORD"),
        ),
    ),
    LineSpec(
        name="C-4.L3",
        doc="Element input. User Manual 5.5.6.4.",
        source=Source.MANUAL,
        fields=(
            _f("limit", 1, 1, _TEXT, "blank, or L on the last element line"),
            _f("element", 2, 5, _INT, "NE -- must ascend from 1; gaps are auto-generated"),
            _f("i", 6, 10, _INT, "IX(1)"),
            _f("j", 11, 15, _INT, "IX(2)"),
            _f("k", 16, 20, _INT, "IX(3): 0 for beams; for interface/link must exceed i and j"),
            _f("l", 21, 25, _INT, "IX(4): quadrilaterals only"),
            _f("material", 26, 30, _INT, "IX(5): soil material, pipe group, or interface property"),
            _f("birth", 31, 35, _INT, "IX(6): load step at which the element enters"),
            _f("code", 36, 40, _INT, "IX(7): 0 continuum/beam, 1 interface, 8/9 link"),
        ),
    ),
    LineSpec(
        name="C-5.L3",
        doc="Boundary conditions. Columns inferred from files; User Manual 5.5.6.5.",
        source=Source.INFERRED,
        partial=True,
        fields=(
            _f("limit", 1, 1, _TEXT, "blank, or L on the last boundary line"),
            _f("node", 2, 5, _INT),
            _f("x_code", 6, 10, _INT, "0 force, 1 displacement"),
            _f("x_value", 11, 20, _REAL),
            _f("y_code", 21, 25, _INT, "0 force, 1 displacement"),
            _f("y_value", 26, 35, _REAL),
            _f("angle", 36, 45, _REAL),
            _f("step", 46, 50, _INT, "load step at which the condition applies"),
        ),
    ),
    # ------------------------------------------------------------------ Part D
    LineSpec(
        name="D-1",
        doc="Material control. User Manual 5.6.1.",
        source=Source.INFERRED,
        fields=(
            _f("limit", 1, 1, _TEXT, "blank, or L on the last material"),
            _f("material", 2, 5, _INT, "ID within its own namespace: soil or interface"),
            _f(
                "model",
                6,
                10,
                _INT,
                "1 Isotropic, 2 Orthotropic, 3 Duncan, 4 Overburden, "
                "5 Hardin, 6 Interface, 7 Composite Link, 8 Mohr/Coulomb",
            ),
            _f("density", 11, 20, _REAL),
            _f("name", 21, 40, _TEXT, "MATNAM plus free text"),
        ),
    ),
    LineSpec(
        name="D-2.Isotropic",
        doc="Isotropic linear elastic properties. User Manual 5.6.2.",
        source=Source.INFERRED,
        partial=True,
        fields=(_f("modulus", 1, 10, _REAL), _f("poisson", 11, 20, _REAL)),
    ),
    LineSpec(
        name="D-2.Interface",
        doc="Interface element properties. User Manual 5.6.7.",
        source=Source.INFERRED,
        fields=(
            _f("angle", 1, 10, _REAL, "interface angle, degrees from horizontal"),
            _f("friction", 11, 20, _REAL, "coefficient of friction"),
            _f("tensile", 21, 30, _REAL, "tensile force capacity"),
            _f("gap", 31, 40, _REAL, "initial gap distance"),
        ),
    ),
    LineSpec(
        name="D-2.Duncan",
        doc="Duncan / Duncan-Selig controls. User Manual 5.6.4.1.",
        source=Source.INFERRED,
        partial=True,
        fields=(
            _f("model_number", 1, 5, _INT),
            _f("ratio", 6, 15, _REAL),
            _f("bulk", 16, 20, _INT, "IBULK: 0 Duncan, 1 Duncan/Selig"),
        ),
    ),
)

#: Every known line type, keyed by command name.
LINE_TYPES: dict[str, LineSpec] = {spec.name: spec for spec in _SPECS}


def spec_for(name: str) -> LineSpec | None:
    """Return the spec for a command name, or ``None`` if it is not catalogued."""
    return LINE_TYPES.get(name)
