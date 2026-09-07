"""__version__ and pyproject.toml must not drift apart."""

import re
from pathlib import Path

from kaggle_wandb_sync import __version__

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _declared_version() -> str:
    for line in PYPROJECT.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^version = "([^"]+)"', line)
        if m:
            return m.group(1)
    raise AssertionError(f"no version line in {PYPROJECT}")


def test_version_matches_pyproject():
    """The version lives in two files; three sibling packages had drifted.

    Compared against the file rather than importlib.metadata on purpose:
    metadata is fixed at install time, so a stale editable install would
    fail this for a reason that has nothing to do with the repo.
    """
    assert __version__ == _declared_version()
