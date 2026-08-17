"""Tests for the viewer's JSON payload.

The page is a pure function of this dict, so what it can show is decided here.
"""

from __future__ import annotations

from pathlib import Path

from candejar.model import Problem
from candejar.web import payload_for


def payload(path: Path) -> dict[str, object]:
    return payload_for(Problem.read(str(path)), path)


class TestPipeGroupPayload:
    def test_a_steel_group_carries_material_and_section(self, fixtures_dir: Path) -> None:
        groups = payload(fixtures_dir / "level2_pipe_steel_wsd.cid")["pipeGroups"]
        assert isinstance(groups, list)
        (group,) = groups
        assert group["pipeType"] == "STEEL"
        assert group["material"]["modulus"] == 29_000_000.0
        assert group["section"]["area"] == 0.04
        # NPCAN is a canned-mesh code, so the page must not show it as a count.
        assert (group["cannedMesh"], group["elements"]) == (1, None)

    def test_a_profile_wall_carries_its_bands(self, fixtures_dir: Path) -> None:
        groups = payload(fixtures_dir / "level3_plastic_asd.cid")["pipeGroups"]
        assert isinstance(groups, list)
        profile = [g for g in groups if g["wallType"] == "PROFILE"]
        assert len(profile) == 3
        bands = profile[0]["profile"]
        assert len(bands) == 21
        assert bands[0]["height"] == 4.968
        assert bands[0]["nodeFirst"] == 1
        # Plastic is the one type with duration-dependent properties.
        assert profile[0]["material"]["modulusLongTerm"] == 75_000.0

    def test_an_uncatalogued_pipe_type_sends_nulls_not_guesses(self, fixtures_dir: Path) -> None:
        groups = payload(fixtures_dir / "level3_concrete_wsd.cid")["pipeGroups"]
        assert isinstance(groups, list)
        (group,) = groups
        assert group["pipeType"] == "CONCRETE"
        assert group["material"] is None and group["section"] is None

    def test_every_fixture_produces_a_serialisable_payload(self, cid_path: Path) -> None:
        """The page json-encodes this; a stray dataclass would break at runtime."""
        import json

        text = json.dumps(payload(cid_path))
        assert '"pipeGroups"' in text
