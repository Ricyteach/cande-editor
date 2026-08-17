from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def cid_fixtures() -> list[Path]:
    return sorted(FIXTURES.glob("*.cid"))


def read_lines(path: Path) -> list[str]:
    """Read a ``.cid`` file preserving every byte except the line endings.

    Opened in binary and split on CRLF explicitly: text mode would rewrite the
    line endings on a non-Windows host and quietly defeat any fidelity test.
    """
    raw = path.read_bytes()
    text = raw.decode("ascii")
    if text.endswith("\r\n"):
        text = text[:-2]
    return text.split("\r\n")


#: Fixtures that are input *skeletons* rather than models CANDE ran: a single
#: element on a node that is never defined, and no restraint anywhere.  They are
#: here for line-type coverage -- they carry the Concrete and Aluminum Part B
#: lines, which nothing else in the corpus of fixtures does -- and for
#: round-trip.  Invariant 5 is a promise about files CANDE *accepted*; these
#: were never run, so asserting they validate cleanly would prove nothing and
#: would quietly redefine the invariant.
INCOMPLETE_MODELS = {"level3_concrete_wsd.cid", "level3_aluminum_wsd.cid"}


@pytest.fixture(params=cid_fixtures(), ids=lambda p: p.stem)
def cid_path(request: pytest.FixtureRequest) -> Path:
    """Each ``.cid`` fixture in turn."""
    return cast(Path, request.param)


@pytest.fixture
def accepted_cid_path(cid_path: Path) -> Path:
    """Each fixture that is a complete model CANDE accepted."""
    if cid_path.name in INCOMPLETE_MODELS:
        pytest.skip(f"{cid_path.name} is an input skeleton, not a model CANDE ran")
    return cid_path


@pytest.fixture
def cid_lines(cid_path: Path) -> list[str]:
    return read_lines(cid_path)


@pytest.fixture
def fixture_name(cid_path: Path) -> str:
    return cid_path.name


@pytest.fixture
def fixtures_dir() -> Path:
    """The fixture directory, for tests that need one file by name."""
    return FIXTURES


@pytest.fixture
def level3_lines() -> list[str]:
    return read_lines(FIXTURES / "level3_plastic_asd.cid")


@pytest.fixture
def level3_document_path() -> Path:
    return FIXTURES / "level3_plastic_asd.cid"
