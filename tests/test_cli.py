"""kaggle-wandb-sync CLI tests."""

import json

from click.testing import CliRunner

from kaggle_wandb_sync.cli import main
from kaggle_wandb_sync._utils import parse_kernel_status, is_terminal


runner = CliRunner()


def test_version():
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help():
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "push" in result.output
    assert "poll" in result.output
    assert "output" in result.output
    assert "sync" in result.output
    assert "run" in result.output


class TestUtils:
    def test_parse_status_complete(self):
        raw = 'yasunorim/my-notebook has status "KernelWorkerStatus.COMPLETE"'
        assert parse_kernel_status(raw) == "KernelWorkerStatus.COMPLETE"

    def test_parse_status_running(self):
        raw = 'yasunorim/my-notebook has status "KernelWorkerStatus.RUNNING"'
        assert parse_kernel_status(raw) == "KernelWorkerStatus.RUNNING"

    def test_parse_status_empty(self):
        assert parse_kernel_status("some random text") == ""

    def test_is_terminal_complete(self):
        assert is_terminal("KernelWorkerStatus.COMPLETE") is True

    def test_is_terminal_error(self):
        assert is_terminal("KernelWorkerStatus.ERROR") is True

    def test_is_terminal_cancel(self):
        assert is_terminal("KernelWorkerStatus.CANCEL") is True

    def test_is_terminal_running(self):
        assert is_terminal("KernelWorkerStatus.RUNNING") is False

    def test_is_terminal_queued(self):
        assert is_terminal("KernelWorkerStatus.QUEUED") is False

    def test_is_terminal_empty(self):
        assert is_terminal("") is False


class TestPush:
    def _make_dir(self, tmp_path, kernel_id="user/my-notebook"):
        comp_dir = tmp_path / "my-notebook"
        comp_dir.mkdir()
        metadata = {
            "id": kernel_id,
            "title": "My Notebook",
            "code_file": "my-notebook.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": "true",
            "enable_gpu": "false",
            "enable_tpu": "false",
            "enable_internet": "false",
        }
        (comp_dir / "kernel-metadata.json").write_text(json.dumps(metadata))
        (comp_dir / "my-notebook.ipynb").write_text("{}")
        return comp_dir

    def test_dry_run(self, tmp_path):
        comp_dir = self._make_dir(tmp_path)
        result = runner.invoke(main, ["push", str(comp_dir), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "kaggle" in result.output

    def test_missing_metadata(self, tmp_path):
        result = runner.invoke(main, ["push", str(tmp_path)])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestPoll:
    def test_help(self):
        result = runner.invoke(main, ["poll", "--help"])
        assert result.exit_code == 0
        assert "KERNEL_ID" in result.output


class TestOutput:
    def test_help(self):
        result = runner.invoke(main, ["output", "--help"])
        assert result.exit_code == 0
        assert "KERNEL_ID" in result.output


class TestSync:
    def test_missing_dir(self, tmp_path):
        result = runner.invoke(main, ["sync", str(tmp_path / "nonexistent")])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_no_offline_runs(self, tmp_path):
        result = runner.invoke(main, ["sync", str(tmp_path)])
        assert result.exit_code == 1
        assert "No offline-run" in result.output


class TestRun:
    def test_missing_metadata(self, tmp_path):
        result = runner.invoke(main, ["run", str(tmp_path)])
        assert result.exit_code == 1
        assert "not found" in result.output
