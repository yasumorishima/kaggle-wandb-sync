"""kaggle-wandb-sync push: Push a Kaggle Notebook (with 409 protection)."""

import json
import subprocess
import time
from pathlib import Path

import click

from kaggle_wandb_sync._utils import find_kaggle, get_kernel_status, is_terminal


@click.command()
@click.argument("directory", default=".")
@click.option("--wait-interval", default=30, show_default=True, help="Seconds between status checks when waiting for a running kernel.")
@click.option("--max-wait", default=20, show_default=True, help="Maximum number of status checks before giving up on waiting.")
@click.option("--dry-run", is_flag=True, default=False, help="Show the command without executing it.")
def push(directory, wait_interval, max_wait, dry_run):
    """Push a Kaggle Notebook to Kaggle.

    DIRECTORY must contain kernel-metadata.json.
    If the kernel is currently running, waits until it finishes to avoid a 409 conflict.
    """
    dir_path = Path(directory)
    metadata_path = dir_path / "kernel-metadata.json"

    if not metadata_path.exists():
        click.echo(f"Error: {metadata_path} not found.", err=True)
        raise SystemExit(1)

    with open(metadata_path) as f:
        metadata = json.load(f)

    kernel_id = metadata.get("id", "")

    kaggle_cmd = find_kaggle()
    if not kaggle_cmd:
        click.echo("Error: kaggle command not found. Run: pip install kaggle", err=True)
        raise SystemExit(1)

    click.echo(f"Kernel: {kernel_id}")

    if dry_run:
        click.echo(f"Dry run: {kaggle_cmd} kernels push -p {dir_path}")
        return

    # Wait for any running kernel to finish (409 protection)
    for i in range(max_wait):
        status = get_kernel_status(kaggle_cmd, kernel_id)
        if not status or is_terminal(status):
            break
        click.echo(f"  Kernel is {status}, waiting {wait_interval}s... ({i + 1}/{max_wait})")
        time.sleep(wait_interval)

    # Push
    click.echo("Pushing to Kaggle...")
    result = subprocess.run(
        [kaggle_cmd, "kernels", "push", "-p", str(dir_path)],
        capture_output=True,
        text=True,
    )

    if result.stdout:
        click.echo(result.stdout.rstrip())
    if result.stderr:
        click.echo(result.stderr.rstrip(), err=True)

    if result.returncode != 0:
        raise SystemExit(result.returncode)

    click.echo("Push complete.")
    click.echo(f"  Check status: kaggle-wandb-sync poll {kernel_id}")
