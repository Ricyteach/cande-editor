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


@pytest.fixture(params=cid_fixtures(), ids=lambda p: p.stem)
def cid_path(request: pytest.FixtureRequest) -> Path:
    """Each ``.cid`` fixture in turn."""
    return cast(Path, request.param)


@pytest.fixture
def cid_lines(cid_path: Path) -> list[str]:
    return read_lines(cid_path)


@pytest.fixture
def fixture_name(cid_path: Path) -> str:
    return cid_path.name


@pytest.fixture
def level3_lines() -> list[str]:
    return read_lines(FIXTURES / "level3_plastic_asd.cid")


@pytest.fixture
def level3_document_path() -> Path:
    return FIXTURES / "level3_plastic_asd.cid"
