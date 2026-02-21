"""kaggle-wandb-sync sync: Sync W&B offline runs to W&B cloud."""

import subprocess
from pathlib import Path

import click

from kaggle_wandb_sync._utils import find_wandb, normalize_path


@click.command()
@click.argument("output_dir", default="./kaggle_output")
def sync(output_dir):
    """Sync W&B offline runs found in OUTPUT_DIR to W&B cloud.

    Searches OUTPUT_DIR recursively for offline-run-* directories and
    runs 'wandb sync' on each one.

    Requires WANDB_API_KEY environment variable (or prior 'wandb login').
    """
    wandb_cmd = find_wandb()
    if not wandb_cmd:
        click.echo("Error: wandb command not found. Run: pip install wandb", err=True)
        raise SystemExit(1)

    output_path = Path(normalize_path(output_dir))
    if not output_path.exists():
        click.echo(f"Error: {output_path} does not exist.", err=True)
        raise SystemExit(1)

    offline_runs = sorted(output_path.rglob("offline-run-*"))
    offline_runs = [p for p in offline_runs if p.is_dir()]

    if not offline_runs:
        click.echo(f"No offline-run-* directories found in {output_path}/")
        click.echo("Make sure the notebook used WANDB_MODE=offline before importing wandb.")
        raise SystemExit(1)

    click.echo(f"Found {len(offline_runs)} offline run(s):")
    for run_dir in offline_runs:
        click.echo(f"  {run_dir}")

    failed = []
    for run_dir in offline_runs:
        click.echo(f"\nSyncing {run_dir.name}...")
        result = subprocess.run(
            [wandb_cmd, "sync", str(run_dir)],
            capture_output=True,
            text=True,
        )
        if result.stdout:
            click.echo(result.stdout.rstrip())
        if result.stderr:
            click.echo(result.stderr.rstrip(), err=True)

        if result.returncode != 0:
            failed.append(run_dir.name)

    if failed:
        click.echo(f"\nError: {len(failed)} run(s) failed to sync: {failed}", err=True)
        raise SystemExit(1)

    click.echo(f"\nAll {len(offline_runs)} run(s) synced successfully.")
