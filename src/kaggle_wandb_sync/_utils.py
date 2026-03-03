"""Shared utilities for kaggle-wandb-sync."""

import json
import os
import re
import shutil
import subprocess
import sysconfig
import tempfile
import urllib.request
from pathlib import Path


TERMINAL_STATUSES = ("COMPLETE", "ERROR", "CANCEL")


def notify_discord(message: str) -> None:
    """Send a message to Discord via DISCORD_WEBHOOK_URL env var. No-op if not set."""
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return
    try:
        data = json.dumps({"content": message}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass  # notifications are best-effort


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


def wait_and_record_score(
    kaggle_cmd: str,
    competition_slug: str,
    output_dir: str,
    poll_interval: int = 30,
    max_attempts: int = 240,
) -> None:
    """Poll Kaggle submissions until a new scored entry appears, then record to W&B.

    Waits up to max_attempts * poll_interval seconds (default 2 hours).
    Reads W&B entity/project/run_id from wandb-metadata.json in output_dir.
    """
    import time

    print(f"Waiting for a new submission to '{competition_slug}' ...")
    print("Please submit via browser now. This step will wait up to 2 hours.")
    notify_discord(f"⚡ **W&B sync完了！ブラウザで提出してください**\nCompetition: `{competition_slug}`")

    def get_submissions():
        result = subprocess.run(
            [kaggle_cmd, "competitions", "submissions", "list",
             "-c", competition_slug, "--csv"],
            capture_output=True, text=True,
        )
        return [l for l in result.stdout.splitlines() if l.strip()][1:]  # skip header

    before_count = len(get_submissions())
    print(f"Current submission count: {before_count}")

    score = None
    for i in range(1, max_attempts + 1):
        time.sleep(poll_interval)
        lines = get_submissions()
        if len(lines) > before_count:
            for line in lines:
                parts = line.split(",")
                if len(parts) >= 5:
                    status = parts[3].strip().lower()
                    pub_score = parts[4].strip()
                    if status == "complete" and pub_score not in ("", "None", "none"):
                        score = pub_score
                        break
            if score:
                print(f"New submission detected! publicScore={score}")
                break
        print(f"Attempt {i}/{max_attempts}: waiting for submission...")

    if not score:
        print("No new scored submission detected. Skipping W&B score recording.")
        return

    metadata_path = next(Path(output_dir).rglob("wandb-metadata.json"), None)
    if not metadata_path:
        print("No wandb-metadata.json found. Skipping W&B recording.")
        return

    meta = json.loads(metadata_path.read_text())
    entity = meta.get("entity", "")
    project = meta.get("project", "")
    run_id = meta.get("run_id", "")
    if not (entity and project and run_id):
        print(f"Incomplete W&B metadata: {meta}. Skipping.")
        return

    run_path = f"{entity}/{project}/{run_id}"
    print(f"Recording to W&B run: {run_path}")
    try:
        import wandb
        api = wandb.Api()
        run = api.run(run_path)
        run.summary.update({"submitted": True, "kaggle_score": float(score)})
        print(f"  kaggle_score = {score}")
        print(f"  submitted = True")
        notify_discord(
            f"✅ **スコア記録完了！**\nCompetition: `{competition_slug}`\n"
            f"Score: `{score}`\nW&B: https://wandb.ai/{run_path}"
        )
    except Exception as e:
        print(f"Error recording to W&B: {e}")


def show_kernel_diagnostics(kaggle_cmd: str, kernel_id: str) -> None:
    """Download kernel output and print stdout + last 30 stderr lines.

    Useful for diagnosing kernel failures without opening the Kaggle UI.
    kernel_id format: username/kernel-slug
    """
    slug = kernel_id.split("/")[-1]
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [kaggle_cmd, "kernels", "output", kernel_id, "-p", tmpdir],
            capture_output=True,
        )
        log_file = Path(tmpdir) / f"{slug}.log"
        if not log_file.exists():
            print("(no kernel log found)")
            return

        entries = json.loads(log_file.read_text())

        stdout_lines = [e["data"] for e in entries if e.get("stream_name") == "stdout"]
        if stdout_lines:
            print("--- kernel stdout ---")
            print("".join(stdout_lines), end="")

        stderr_lines = [e["data"] for e in entries if e.get("stream_name") == "stderr"]
        if stderr_lines:
            print("\n--- last 30 stderr lines ---")
            print("".join(stderr_lines[-30:]), end="")
