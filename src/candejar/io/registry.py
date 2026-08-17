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
        doc="Master control. User Manual 5.3.1.",
        source=Source.MANUAL,
        fields=(
            _f("mode", 1, 8, _TEXT, "XMODE: ANALYS, DESIGN, CHECK or STOP"),
            _f("level", 9, 10, _INT, "LEVEL: solution level 1, 2 or 3"),
            _f("method", 11, 12, _INT, "LRFD: 0 working stress, 1 LRFD"),
            _f("pipe_groups", 13, 15, _INT, "NPGRPS: number of pipe groups; Part A/B repeats"),
            _f("title", 16, 75, _TEXT, "HED: heading for output files"),
            _f("iterations", 76, 80, _INT, "ITMAX: iterations per load step"),
            _f("culvert_id", 81, 85, _INT, "CULVERTID"),
            _f("process_id", 86, 90, _INT, "PROCESSID"),
            _f("subdomain_id", 91, 95, _INT, "SUBDID"),
        ),
    ),
    LineSpec(
        name="A-2.L3",
        doc="Pipe selection, Level 3. One per pipe group. User Manual 5.3.2.",
        source=Source.MANUAL,
        fields=(
            _f(
                "pipe_type",
                1,
                10,
                _TEXT,
                "PTYPE: ALUMINUM, BASIC, CONCRETE, CONRIB, CONTUBE, PLASTIC or STEEL",
            ),
            _f("elements", 11, 15, _INT, "NPMATX: connected beam elements in this group, max 999"),
        ),
    ),
    LineSpec(
        name="A-2.L12",
        doc=(
            "Pipe selection, Levels 1 and 2. User Manual 5.3.2.  Columns 11-15 are "
            "NPCAN, the canned-mesh code -- *not* an element count.  Only A-2.L3 "
            "carries a beam count there, and reading this field as one reports a "
            "circular pipe mesh as a group of one element."
        ),
        source=Source.MANUAL,
        fields=(
            _f("pipe_type", 1, 10, _TEXT, "PTYPE"),
            _f("canned_mesh", 11, 15, _INT, "NPCAN: canned mesh code, Level 2 only"),
        ),
    ),
    # ------------------------------------------------------------------ Part B
    #
    # Part B describes the pipe material, and repeats once per pipe group.  The
    # command name carries the pipe type, and for some lines the solution mode
    # too: ``.A`` is the analysis form, ``.D`` the design form.
    LineSpec(
        name="B-1.Steel",
        doc="Steel material properties and control. User Manual 5.4.5.1.",
        source=Source.MANUAL,
        fields=(
            _f("modulus", 1, 10, _REAL, "PE: Young's modulus"),
            _f("poisson", 11, 20, _REAL, "PNU: Poisson's ratio"),
            _f("yield_stress", 21, 30, _REAL, "PYIELD: yield stress of the pipe wall"),
            _f("seam_strength", 31, 40, _REAL, "PSEAM: yield stress of the seam"),
            _f("density", 41, 50, _REAL, "PDEN"),
            _f("modulus_bilinear", 51, 60, _REAL, "PE2: second modulus of the bilinear model"),
            _f("joint_slip", 61, 65, _INT, "JOINT: 0 none, 1 slippage, 2 slippage with trace"),
            _f("behaviour", 66, 70, _INT, "NONLIN: 1 linear, 2 bilinear stress-strain"),
            _f(
                "buckling",
                71,
                75,
                _INT,
                "IBUCK: 0 small deformation + AASHTO 1, 1 large + AASHTO 1, "
                "2 large + CANDE, 3 small + AASHTO 2",
            ),
        ),
    ),
    LineSpec(
        name="B-2.Steel.A",
        doc=(
            "Steel section properties, analysis mode. User Manual 5.4.5.2.  These "
            "are the four numbers a corrugation-and-gage library would supply; "
            "they are per unit length of pipe, not totals."
        ),
        source=Source.MANUAL,
        fields=(
            _f("area", 1, 10, _REAL, "PA: wall area per unit length"),
            _f("inertia", 11, 20, _REAL, "PI: moment of inertia per unit length"),
            _f("section_modulus", 21, 30, _REAL, "PS: section modulus per unit length"),
            _f("deep_modulus", 31, 40, _REAL, "PZ: plastic modulus, deep corrugations only"),
        ),
    ),
    LineSpec(
        name="B-3.Steel.AD.LRFD",
        doc="Steel resistance factors for LRFD. User Manual 5.4.5.8.",
        source=Source.MANUAL,
        fields=(
            _f("phi_thrust", 1, 10, _REAL, "PHI(1): thrust stress yielding"),
            _f("phi_buckling", 11, 20, _REAL, "PHI(2): global buckling"),
            _f("phi_seam", 21, 30, _REAL, "PHI(3): seam strength in thrust"),
            _f("phi_plastic", 31, 40, _REAL, "PHI(4): plastic penetration"),
            _f("deflection_limit", 41, 50, _REAL, "DISP: allowable deflection at service load"),
            _f("phi_deep", 51, 60, _REAL, "PHI(5): deep-corrugation criterion"),
        ),
    ),
    LineSpec(
        name="B-1.Alum",
        doc=(
            "Aluminum material properties and control. User Manual 5.4.1.1.  "
            "Deliberately not a copy of B-1.Steel: aluminum has no joint-slip "
            "option, so NONLIN and IBUCK sit five columns earlier."
        ),
        source=Source.MANUAL,
        fields=(
            _f("modulus", 1, 10, _REAL, "PE: Young's modulus"),
            _f("poisson", 11, 20, _REAL, "PNU: Poisson's ratio"),
            _f("yield_stress", 21, 30, _REAL, "PYIELD: yield stress of the pipe wall"),
            _f("seam_strength", 31, 40, _REAL, "PSEAM: yield strength of the seam"),
            _f("density", 41, 50, _REAL, "PDEN"),
            _f("modulus_bilinear", 51, 60, _REAL, "PE2: second modulus of the bilinear model"),
            _f("behaviour", 61, 65, _INT, "NONLIN: 1 linear, 2 bilinear stress-strain"),
            _f("buckling", 66, 70, _INT, "IBUCK: buckling indicator"),
        ),
    ),
    LineSpec(
        name="B-2.Alum.A",
        doc=(
            "Aluminum analysis section properties. User Manual 5.4.1.2.  Per unit "
            "length of pipe, not totals.  Aluminum has no deep-corrugation plastic "
            "modulus, so there is no counterpart to B-2.Steel.A's PZ."
        ),
        source=Source.MANUAL,
        fields=(
            _f("area", 1, 10, _REAL, "PA: wall area per unit length"),
            _f("inertia", 11, 20, _REAL, "PI: moment of inertia per unit length"),
            _f("section_modulus", 21, 30, _REAL, "PS: section modulus per unit length"),
        ),
    ),
    LineSpec(
        name="B-3.Alum.AD.LRFD",
        doc="Aluminum resistance factors for LRFD. User Manual 5.4.1.4.",
        source=Source.MANUAL,
        fields=(
            _f("phi_thrust", 1, 10, _REAL, "PHI(1): wall area yielding in thrust"),
            _f("phi_buckling", 11, 20, _REAL, "PHI(2): global buckling in thrust"),
            _f("phi_seam", 21, 30, _REAL, "PHI(3): seam strength in thrust"),
            _f("phi_plastic", 31, 40, _REAL, "PHI(4): plastic penetration"),
            _f("deflection_limit", 41, 50, _REAL, "DISP: allowable deflection at service load"),
        ),
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
        doc=(
            "Material control. User Manual 5.6.1.  Every field but 'name' matches "
            "the manual's table; 'name' deliberately does not -- see below -- so the "
            "spec as a whole stays INFERRED."
        ),
        source=Source.INFERRED,
        partial=True,
        fields=(
            _f("limit", 1, 1, _TEXT, "blank, or L on the last material"),
            _f("material", 2, 5, _INT, "I: ID within its own namespace, soil or interface"),
            _f(
                "model",
                6,
                10,
                _INT,
                "ITYP: 1 Isotropic, 2 Orthotropic, 3 Duncan, 4 Overburden, "
                "5 Hardin, 6 Interface, 7 Composite Link, 8 Mohr/Coulomb",
            ),
            _f("density", 11, 20, _REAL, "DEN: pcf; ignored for interface and link"),
            # MATNAM is positional: the manual states it "starts in column 21 and
            # is 4 or 5 capital letters and/or numbers", and for ITYP 3, 4 and 5 it
            # selects a canned soil, so column 21 must be preserved exactly.
            #
            # The manual gives MATNAM as columns 21-40 (5A4) and a GUI-only layer
            # count at 41-42 (I2).  Real files do not respect that boundary: they
            # run descriptive text straight through it -- the corpus fixture writes
            # "SW100  Embankement Fill", whose "il" lands in columns 41-42 -- and
            # 63,112 D-1 lines across the 2,886-file corpus do likewise.  Modelling
            # 41-42 as an integer would report those files as broken, so the span is
            # kept wide and the layer count is left unaddressed rather than invented.
            _f("name", 21, 60, _TEXT, "MATNAM in the first five columns, then free text"),
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
    # ------------------------------------------------------------------ Part E
    LineSpec(
        name="E-1",
        doc="LRFD net load factor per load step. User Manual 5.7.1.",
        source=Source.MANUAL,
        fields=(
            _f("first_step", 1, 5, _INT, "INCRS: first load step this factor applies to"),
            _f("last_step", 6, 10, _INT, "INCRL: last load step; defaults to INCRS"),
            _f("factor", 11, 20, _REAL, "FACTOR: net LRFD load factor, default 1.00"),
            _f("comment", 21, 60, _TEXT, "COMMENT: printed with the factor for each step"),
        ),
    ),
)

#: Every known line type, keyed by command name.
LINE_TYPES: dict[str, LineSpec] = {spec.name: spec for spec in _SPECS}


def spec_for(name: str) -> LineSpec | None:
    """Return the spec for a command name, or ``None`` if it is not catalogued."""
    return LINE_TYPES.get(name)
