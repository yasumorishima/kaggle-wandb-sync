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
kaggle-wandb-sync poll   yasunorim/my-notebook             # wait for COMPLETE
kaggle-wandb-sync output yasunorim/my-notebook             # download output
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

### `run` — Full pipeline (recommended)

```
kaggle-wandb-sync run [DIRECTORY] [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--kernel-id`, `-k` | from metadata | Kernel ID (`username/slug`) |
| `--output-dir`, `-o` | `./kaggle_output` | Directory for downloaded files |
| `--poll-interval` | `30` | Seconds between status checks |
| `--max-attempts` | `60` | Max poll attempts (30min total) |
| `--skip-push` | off | Skip push step (use when notebook has already finished running) |
| `--skip-sync` | off | Download output only, skip W&B sync |

### `push` — Push notebook

```
kaggle-wandb-sync push [DIRECTORY] [OPTIONS]
```

Waits for any currently running kernel to finish before pushing (prevents 409 Conflict errors).

### `poll` — Wait for completion

```
kaggle-wandb-sync poll KERNEL_ID [--interval 30] [--max-attempts 60]
```

Exits with code 1 if the kernel finishes with ERROR or CANCEL.

### `output` — Download output

```
kaggle-wandb-sync output KERNEL_ID [--output-dir ./kaggle_output]
```

### `sync` — Sync to W&B

```
kaggle-wandb-sync sync [OUTPUT_DIR]
```

Finds all `offline-run-*` directories and runs `wandb sync` on each.

## Known Issues

- **Windows encoding:** Prefix commands with `PYTHONUTF8=1` if you see encoding errors on Windows.

- **Windows PATH (Microsoft Store Python):** If `kaggle-wandb-sync: command not found` in Git Bash, add the Scripts directory to your PATH:
  ```bash
  # Add to ~/.bashrc
  export PATH="$PATH:/c/Users/<your-username>/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0/LocalCache/local-packages/Python312/Scripts"
  ```

## License

MIT
