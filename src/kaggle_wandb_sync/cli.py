"""CLI entry point for kaggle-wandb-sync."""

import click

from kaggle_wandb_sync import __version__
from kaggle_wandb_sync.commands.push import push
from kaggle_wandb_sync.commands.poll import poll
from kaggle_wandb_sync.commands.output import output
from kaggle_wandb_sync.commands.sync import sync
from kaggle_wandb_sync.commands.run import run
from kaggle_wandb_sync.commands.score import score


@click.group()
@click.version_option(version=__version__)
def main():
    """Sync W&B offline runs from Kaggle Notebooks to W&B cloud.

    Full pipeline: push notebook → poll until complete → download output → wandb sync

    Typical usage:
        kaggle-wandb-sync run my-notebook/   # all-in-one
        kaggle-wandb-sync run my-notebook/ --skip-push  # re-sync only
    """
    pass


main.add_command(push)
main.add_command(poll)
main.add_command(output)
main.add_command(sync)
main.add_command(run)
main.add_command(score)
