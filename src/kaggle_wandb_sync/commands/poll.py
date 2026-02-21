"""kaggle-wandb-sync poll: Poll until a kernel reaches a terminal state."""

import time

import click

from kaggle_wandb_sync._utils import find_kaggle, get_kernel_status, is_terminal


@click.command()
@click.argument("kernel_id")
@click.option("--interval", default=30, show_default=True, help="Seconds between status checks.")
@click.option("--max-attempts", default=60, show_default=True, help="Maximum number of status checks before giving up.")
def poll(kernel_id, interval, max_attempts):
    """Poll a Kaggle kernel until it reaches COMPLETE, ERROR, or CANCEL.

    KERNEL_ID format: username/kernel-slug  (e.g. yasunorim/my-notebook)
    """
    kaggle_cmd = find_kaggle()
    if not kaggle_cmd:
        click.echo("Error: kaggle command not found. Run: pip install kaggle", err=True)
        raise SystemExit(1)

    click.echo(f"Polling {kernel_id} (interval={interval}s, max={max_attempts} attempts)...")

    for i in range(max_attempts):
        status = get_kernel_status(kaggle_cmd, kernel_id)
        click.echo(f"  [{i + 1}/{max_attempts}] Status: {status or '(unknown)'}")

        if is_terminal(status):
            click.echo(f"Kernel finished with status: {status}")
            if "ERROR" in status.upper() or "CANCEL" in status.upper():
                raise SystemExit(1)
            return

        time.sleep(interval)

    click.echo(f"Error: kernel did not finish after {max_attempts} attempts.", err=True)
    raise SystemExit(1)
