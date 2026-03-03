"""Generate the Commands section of README.md from Click command definitions.

Usage:
    python scripts/gen_commands_doc.py

Updates README.md between the markers:
    <!-- commands:start -->
    <!-- commands:end -->
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import click
from kaggle_wandb_sync.cli import cli


BEGIN_MARKER = "<!-- commands:start -->"
END_MARKER = "<!-- commands:end -->"


def option_row(param: click.Option) -> str:
    names = ", ".join(f"`{n}`" for n in param.opts)
    default = f" (default: `{param.default}`)" if param.default not in (None, False) else ""
    return f"| {names} | {param.help or ''}{default} |"


def generate_commands_section(cmd_group: click.Group) -> str:
    lines = []
    for name, cmd in sorted(cmd_group.commands.items()):
        lines.append(f"### `kaggle-wandb-sync {name}`")
        lines.append("")
        if cmd.help:
            lines.append(cmd.help.split("\n")[0])
            lines.append("")
        options = [p for p in cmd.params if isinstance(p, click.Option)]
        args = [p for p in cmd.params if isinstance(p, click.Argument)]
        if args:
            arg_names = " ".join(f"[{a.name.upper()}]" for a in args)
            lines.append(f"```\nkaggle-wandb-sync {name} {arg_names} [OPTIONS]\n```")
            lines.append("")
        if options:
            lines.append("| Option | Default | Description |")
            lines.append("|---|---|---|")
            for opt in options:
                default = f"`{opt.default}`" if opt.default not in (None, False) else ""
                names = ", ".join(f"`{n}`" for n in opt.opts)
                lines.append(f"| {names} | {default} | {opt.help or ''} |")
            lines.append("")
    return "\n".join(lines)


def update_readme(readme_path: Path, new_section: str) -> bool:
    content = readme_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"{re.escape(BEGIN_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL,
    )
    replacement = f"{BEGIN_MARKER}\n\n{new_section}\n{END_MARKER}"
    new_content, count = pattern.subn(replacement, content)
    if count == 0:
        print(f"ERROR: markers not found in {readme_path}", file=sys.stderr)
        return False
    if new_content == content:
        print("README.md is already up to date.")
        return False
    readme_path.write_text(new_content, encoding="utf-8")
    print("README.md updated.")
    return True


if __name__ == "__main__":
    readme = Path(__file__).parent.parent / "README.md"
    section = generate_commands_section(cli)
    update_readme(readme, section)
