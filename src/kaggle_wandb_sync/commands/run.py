"""kaggle-wandb-sync run: Push, poll, download, and sync in one step."""

import json
import time
from pathlib import Path

import click

from kaggle_wandb_sync._utils import find_kaggle, find_wandb, get_kernel_status, is_terminal
from kaggle_wandb_sync.commands.push import push as push_cmd
from kaggle_wandb_sync.commands.poll import poll as poll_cmd
from kaggle_wandb_sync.commands.output import output as output_cmd
from kaggle_wandb_sync.commands.sync import sync as sync_cmd


@click.command()
@click.argument("directory", default=".")
@click.option("--kernel-id", "-k", default=None, help="Kernel ID (default: read from kernel-metadata.json).")
@click.option("--output-dir", "-o", default="./kaggle_output", show_default=True, help="Directory to save downloaded output.")
@click.option("--poll-interval", default=30, show_default=True, help="Seconds between status checks.")
@click.option("--max-attempts", default=60, show_default=True, help="Maximum poll attempts.")
@click.option("--skip-push", is_flag=True, default=False, help="Skip push (re-run output+sync only).")
@click.option("--skip-sync", is_flag=True, default=False, help="Skip wandb sync (download output only).")
def run(directory, kernel_id, output_dir, poll_interval, max_attempts, skip_push, skip_sync):
    """Run the full pipeline: push → poll → output → wandb sync.

    DIRECTORY must contain kernel-metadata.json.
    Requires WANDB_API_KEY environment variable (or prior 'wandb login').
    """
    dir_path = Path(directory)
    metadata_path = dir_path / "kernel-metadata.json"

    if not metadata_path.exists():
        click.echo(f"Error: {metadata_path} not found.", err=True)
        raise SystemExit(1)

    if kernel_id is None:
        with open(metadata_path) as f:
            metadata = json.load(f)
        kernel_id = metadata.get("id", "")
        if not kernel_id:
            click.echo("Error: 'id' not found in kernel-metadata.json.", err=True)
            raise SystemExit(1)

    kaggle_cmd = find_kaggle()
    if not kaggle_cmd:
        click.echo("Error: kaggle command not found. Run: pip install kaggle", err=True)
        raise SystemExit(1)

    if not skip_sync:
        wandb_cmd = find_wandb()
        if not wandb_cmd:
            click.echo("Error: wandb command not found. Run: pip install wandb", err=True)
            raise SystemExit(1)

    ctx = click.get_current_context()

    # Step 1: Push
    if not skip_push:
        click.echo("=" * 50)
        click.echo("Step 1/4: Push")
        click.echo("=" * 50)
        ctx.invoke(push_cmd, directory=directory)

    # Step 2: Poll
    click.echo("")
    click.echo("=" * 50)
    click.echo("Step 2/4: Poll")
    click.echo("=" * 50)
    ctx.invoke(poll_cmd, kernel_id=kernel_id, interval=poll_interval, max_attempts=max_attempts)

    # Step 3: Download output
    click.echo("")
    click.echo("=" * 50)
    click.echo("Step 3/4: Download output")
    click.echo("=" * 50)
    ctx.invoke(output_cmd, kernel_id=kernel_id, output_dir=output_dir)

    # Step 4: Sync
    if not skip_sync:
        click.echo("")
        click.echo("=" * 50)
        click.echo("Step 4/4: W&B sync")
        click.echo("=" * 50)
        ctx.invoke(sync_cmd, output_dir=output_dir)

    click.echo("")
    click.echo("Pipeline complete.")
