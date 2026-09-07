# kaggle-wandb-sync

[![PyPI version](https://badge.fury.io/py/kaggle-wandb-sync.svg)](https://pypi.org/project/kaggle-wandb-sync/)
[![Test](https://github.com/yasumorishima/kaggle-wandb-sync/actions/workflows/test.yml/badge.svg)](https://github.com/yasumorishima/kaggle-wandb-sync/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A CLI tool to sync [Weights & Biases](https://wandb.ai) offline runs from Kaggle Notebooks to W&B cloud — fully automated via GitHub Actions.

## Why?

Kaggle Notebooks run in an isolated environment with internet access disabled for competition submissions. This means you can't push W&B metrics in real time. **kaggle-wandb-sync** solves this by:

1. Running your notebook with `WANDB_MODE=offline` (logs saved locally on Kaggle)
2. Downloading the output via `kaggle kernels output`
3. Syncing the offline runs to W&B cloud with `wandb sync`

## Installation

```bash
pip install kaggle-wandb-sync
```

**Prerequisites:** [Kaggle API credentials](https://www.kaggle.com/docs/api) (`~/.kaggle/kaggle.json`) and a W&B API key (`WANDB_API_KEY` env var, or run `wandb login` once to save credentials to `~/.netrc`).

## Quick Start

### All-in-one command

```bash
# Set your W&B API key
export WANDB_API_KEY=your_api_key

# Push notebook, wait for completion, download output, sync to W&B
kaggle-wandb-sync run my-notebook/
```

### Step by step

```bash
kaggle-wandb-sync push   my-notebook/                      # push (with 409 protection)
kaggle-wandb-sync poll   username/my-notebook              # wait for COMPLETE
kaggle-wandb-sync output username/my-notebook              # download output
kaggle-wandb-sync sync   ./kaggle_output                   # wandb sync
```

## Notebook Setup

Add these lines **before** importing wandb in your Kaggle Notebook:

```python
import os
os.environ['WANDB_MODE'] = 'offline'   # must be set before import
os.environ['WANDB_PROJECT'] = 'my-project'

import wandb
wandb.init()
# ... your training code ...
wandb.log({"loss": 0.1, "accuracy": 0.95})
wandb.finish()
```

> **Important:** Set `WANDB_MODE=offline` *before* `import wandb`, not after.

## GitHub Actions Integration

Add this workflow to your Kaggle repo (`.github/workflows/kaggle-wandb-sync.yml`):

```yaml
name: Kaggle W&B Sync

on:
  workflow_dispatch:
    inputs:
      notebook_dir:
        description: "Notebook directory (e.g. my-competition)"
        required: true
      kernel_id:
        description: "Kernel ID (e.g. username/my-competition-baseline)"
        required: true

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install kaggle-wandb-sync
        run: pip install kaggle-wandb-sync

      - name: Set up Kaggle credentials
        run: |
          mkdir -p ~/.kaggle
          echo '${{ secrets.KAGGLE_API_TOKEN }}' > ~/.kaggle/kaggle.json
          chmod 600 ~/.kaggle/kaggle.json

      - name: Run pipeline
        env:
          WANDB_API_KEY: ${{ secrets.WANDB_API_KEY }}
        run: |
          kaggle-wandb-sync run ${{ inputs.notebook_dir }} \
            --kernel-id ${{ inputs.kernel_id }}
```

**Required secrets:** `KAGGLE_API_TOKEN` (JSON content of `~/.kaggle/kaggle.json`) and `WANDB_API_KEY`.

## Commands

<!-- commands:start -->

### `kaggle-wandb-sync output`

Download output files from a completed Kaggle kernel.

```
kaggle-wandb-sync output KERNEL_ID [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--output-dir`, `-o` | `./kaggle_output` | Directory to save downloaded files. |

### `kaggle-wandb-sync poll`

Poll a Kaggle kernel until it reaches COMPLETE, ERROR, or CANCEL.

```
kaggle-wandb-sync poll KERNEL_ID [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--interval` | `30` | Seconds between status checks. |
| `--max-attempts` | `60` | Maximum number of status checks before giving up. |

### `kaggle-wandb-sync push`

Push a Kaggle Notebook to Kaggle.

```
kaggle-wandb-sync push [DIRECTORY] [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--wait-interval` | `30` | Seconds between status checks when waiting for a running kernel. |
| `--max-wait` | `20` | Maximum number of status checks before giving up on waiting. |
| `--dry-run` |  | Show the command without executing it. |

### `kaggle-wandb-sync run`

Run the full pipeline: push → poll → output → wandb sync → wait for submission → record LB score.

```
kaggle-wandb-sync run [DIRECTORY] [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--kernel-id`, `-k` |  | Kernel ID (default: read from kernel-metadata.json). |
| `--output-dir`, `-o` | `./kaggle_output` | Directory to save downloaded output. |
| `--poll-interval` | `30` | Seconds between status checks. |
| `--max-attempts` | `60` | Maximum poll attempts. |
| `--skip-push` |  | Skip push (re-run output+sync only). |
| `--skip-sync` |  | Skip wandb sync (download output only). |
| `--competition-slug` |  | Competition slug to auto-record LB score after submission (e.g. march-machine-learning-mania-2026). |

### `kaggle-wandb-sync score`

Log Kaggle submission scores to a W&B run.

```
kaggle-wandb-sync score RUN_ID [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--project`, `-p` |  | W&B project path (entity/project). Required if RUN_ID is a bare ID. |
| `--score` |  | Kaggle public LB score. |
| `--rank` |  | Leaderboard rank. |
| `--metric`, `-m` |  | Additional metric (can be repeated, e.g. -m auc=0.95 -m loss=0.3). |

### `kaggle-wandb-sync sync`

Sync W&B offline runs found in OUTPUT_DIR to W&B cloud.

```
kaggle-wandb-sync sync [OUTPUT_DIR] [OPTIONS]
```

<!-- commands:end -->

### Command notes

Behaviour that is not visible in the option tables above:

- **`run` is the one to reach for** — it is the full pipeline (push → poll → output → sync → score). The generated list above is alphabetical, so it does not read in that order.
- **`push`** waits for any currently running kernel to finish before pushing, which prevents 409 Conflict errors.
- **`run`'s** `--max-attempts` (60) times `--poll-interval` (30s) is the give-up point: 30 minutes by default. `--skip-push` is for a notebook that has already finished running.
- **`poll`** exits with code 1 if the kernel finishes with ERROR or CANCEL. Since v0.1.5 it also downloads the kernel log on those outcomes and prints stdout plus the last 30 stderr lines, so you can diagnose a failure without opening the Kaggle UI.
- **`sync`** finds every `offline-run-*` directory under the output dir and runs `wandb sync` on each.
- **`score`** takes `--metric KEY=VALUE` (repeatable), and a full run URL, an `entity/project/id` path, or a bare id with `--project`:

  ```bash
  kaggle-wandb-sync score https://wandb.ai/me/my-proj/runs/abc123 --score 0.127 --rank 200
  ```

> The section above `Command notes` is generated from the Click definitions by
> `scripts/gen_commands_doc.py`, and CI rewrites it on every push that changes
> `src/`. It is ordered alphabetically, not by pipeline order. Put anything
> hand-written here, below `<!-- commands:end -->`, or it will be overwritten.

## Known Issues

- **Windows encoding:** Prefix commands with `PYTHONUTF8=1` if you see encoding errors on Windows.

- **Windows PATH (Microsoft Store Python):** If `kaggle-wandb-sync: command not found` in Git Bash, add the Scripts directory to your PATH:
  ```bash
  # Add to ~/.bashrc
  export PATH="$PATH:/c/Users/<your-username>/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0/LocalCache/local-packages/Python312/Scripts"
  ```

- **Git Bash path format (fixed in v0.1.2):** Git Bash converts paths like `C:/Users/...` to `/c/Users/...`, which Python cannot resolve. As of v0.1.2, all path arguments are automatically converted to Windows format.

## License

MIT
