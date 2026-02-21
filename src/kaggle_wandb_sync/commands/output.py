"""kaggle-wandb-sync output: Download kernel output files."""

import subprocess
from pathlib import Path

import click

from kaggle_wandb_sync._utils import find_kaggle, normalize_path


@click.command()
@click.argument("kernel_id")
@click.option("--output-dir", "-o", default="./kaggle_output", show_default=True, help="Directory to save downloaded files.")
def output(kernel_id, output_dir):
    """Download output files from a completed Kaggle kernel.

    KERNEL_ID format: username/kernel-slug  (e.g. yasunorim/my-notebook)

    Downloads all output files including wandb/ offline run directories.
    """
    kaggle_cmd = find_kaggle()
    if not kaggle_cmd:
        click.echo("Error: kaggle command not found. Run: pip install kaggle", err=True)
        raise SystemExit(1)

    output_path = Path(normalize_path(output_dir))
    output_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"Downloading output from {kernel_id} to {output_path}...")

    result = subprocess.run(
        [kaggle_cmd, "kernels", "output", kernel_id, "-p", str(output_path)],
        capture_output=True,
        text=True,
    )

    if result.stdout:
        click.echo(result.stdout.rstrip())
    if result.stderr:
        click.echo(result.stderr.rstrip(), err=True)

    if result.returncode != 0:
        raise SystemExit(result.returncode)

    # Show downloaded files
    files = list(output_path.rglob("*"))
    click.echo(f"Downloaded {len([f for f in files if f.is_file()])} file(s) to {output_path}/")
