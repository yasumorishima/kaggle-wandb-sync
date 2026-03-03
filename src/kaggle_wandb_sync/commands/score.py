"""kaggle-wandb-sync score: Log Kaggle submission scores to a W&B run."""

import re

import click


def _parse_run_path(run_id: str) -> str:
    """Parse run_id into W&B run path (entity/project/run_id).

    Accepts:
      - Full URL: https://wandb.ai/entity/project/runs/abc123
      - Path:     entity/project/abc123
      - ID only:  abc123  (requires --project)
    """
    # Full W&B URL
    m = re.match(r'https?://wandb\.ai/([^/]+)/([^/]+)/runs/([^/?]+)', run_id)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

    # entity/project/run_id
    if run_id.count('/') == 2:
        return run_id

    # Bare run ID — caller must pass --project
    return run_id


@click.command()
@click.argument("run_id")
@click.option("--project", "-p", default=None, help="W&B project path (entity/project). Required if RUN_ID is a bare ID.")
@click.option("--score", "kaggle_score", type=float, default=None, help="Kaggle public LB score.")
@click.option("--rank", type=int, default=None, help="Leaderboard rank.")
@click.option("--metric", "-m", multiple=True, metavar="KEY=VALUE", help="Additional metric (can be repeated, e.g. -m auc=0.95 -m loss=0.3).")
def score(run_id, project, kaggle_score, rank, metric):
    """Log Kaggle submission scores to a W&B run.

    RUN_ID can be:
      - Full W&B URL:  https://wandb.ai/entity/project/runs/abc123
      - Path:          entity/project/abc123
      - Bare ID:       abc123  (requires --project entity/project)

    Examples:

      kaggle-wandb-sync score https://wandb.ai/me/my-proj/runs/abc123 --score 0.127 --rank 200

      kaggle-wandb-sync score abc123 --project me/my-proj --score 0.127

      kaggle-wandb-sync score abc123 --project me/my-proj -m auc=0.95 -m loss=0.3
    """
    try:
        import wandb
    except ImportError:
        click.echo("Error: wandb not found. Run: pip install wandb", err=True)
        raise SystemExit(1)

    # Build run path
    run_path = _parse_run_path(run_id)

    # Bare ID needs --project
    if '/' not in run_path:
        if not project:
            click.echo(
                "Error: RUN_ID is a bare ID. Provide --project entity/project or use a full URL.",
                err=True,
            )
            raise SystemExit(1)
        run_path = f"{project}/{run_path}"

    # Parse --metric KEY=VALUE pairs
    extra = {}
    for m in metric:
        if '=' not in m:
            click.echo(f"Error: --metric must be KEY=VALUE, got: {m!r}", err=True)
            raise SystemExit(1)
        key, val = m.split('=', 1)
        # Try to cast to float, fall back to string
        try:
            extra[key] = float(val)
        except ValueError:
            extra[key] = val

    if kaggle_score is None and rank is None and not extra:
        click.echo("Error: provide at least one of --score, --rank, or --metric.", err=True)
        raise SystemExit(1)

    # Update run summary
    try:
        api = wandb.Api()
        run = api.run(run_path)
    except Exception as e:
        click.echo(f"Error: could not find W&B run '{run_path}': {e}", err=True)
        raise SystemExit(1)

    updates = {'submitted': True}
    if kaggle_score is not None:
        updates['kaggle_score'] = kaggle_score
    if rank is not None:
        updates['kaggle_rank'] = rank
    updates.update(extra)

    run.summary.update(updates)

    click.echo(f"Updated run: {run.name} ({run_path})")
    for k, v in updates.items():
        click.echo(f"  {k} = {v}")
