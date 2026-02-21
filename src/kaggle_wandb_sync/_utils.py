"""Shared utilities for kaggle-wandb-sync."""

import re
import shutil
import subprocess
import sysconfig
from pathlib import Path


TERMINAL_STATUSES = ("COMPLETE", "ERROR", "CANCEL")


def normalize_path(path_str: str) -> str:
    """Convert Git Bash-style paths (/c/Users/...) to Windows paths (C:/Users/...).

    Git Bash on Windows converts paths to /c/Users/... format, which Python
    does not understand. This function detects and converts them.
    """
    if len(path_str) >= 3 and path_str[0] == '/' and path_str[1].isalpha() and path_str[2] == '/':
        return path_str[1].upper() + ':' + path_str[2:]
    return path_str


def find_kaggle() -> str | None:
    """Find the kaggle executable path."""
    for name in ("kaggle", "kaggle.exe"):
        if found := shutil.which(name):
            return found
    for scheme in ("nt_user", "posix_user", None):
        try:
            scripts = Path(sysconfig.get_path("scripts", scheme) or "")
        except KeyError:
            continue
        for name in ("kaggle.exe", "kaggle"):
            candidate = scripts / name
            if candidate.exists():
                return str(candidate)
    return None


def find_wandb() -> str | None:
    """Find the wandb executable path."""
    for name in ("wandb", "wandb.exe"):
        if found := shutil.which(name):
            return found
    for scheme in ("nt_user", "posix_user", None):
        try:
            scripts = Path(sysconfig.get_path("scripts", scheme) or "")
        except KeyError:
            continue
        for name in ("wandb.exe", "wandb"):
            candidate = scripts / name
            if candidate.exists():
                return str(candidate)
    return None


def parse_kernel_status(raw: str) -> str:
    """Parse kernel status from 'has status "KernelWorkerStatus.COMPLETE"' format."""
    m = re.search(r'has status "([^"]+)"', raw)
    return m.group(1) if m else ""


def is_terminal(status: str) -> bool:
    """Return True if the status is a terminal state (complete/error/cancel)."""
    upper = status.upper()
    return any(s in upper for s in TERMINAL_STATUSES)


def get_kernel_status(kaggle_cmd: str, kernel_id: str) -> str:
    """Run kaggle kernels status and return parsed status string."""
    result = subprocess.run(
        [kaggle_cmd, "kernels", "status", kernel_id],
        capture_output=True,
        text=True,
    )
    raw = result.stdout + result.stderr
    return parse_kernel_status(raw)
