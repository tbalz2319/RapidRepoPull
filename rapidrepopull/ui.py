"""Terminal output.

One dependency (click) instead of the three overlapping colour libraries the
old version pulled in, and it honours ``NO_COLOR``/non-TTY output so piping to
a file no longer produces escape-code soup.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from rapidrepopull.cloner import Result, Status, Summary

BANNER_FILE = Path(__file__).resolve().parent / "data" / "ascii.txt"

_STATUS_STYLE = {
    Status.CLONED: ("[+]", "green"),
    Status.UPDATED: ("[~]", "cyan"),
    Status.SKIPPED: ("[-]", "yellow"),
    Status.FAILED: ("[!]", "red"),
}


def banner(version: str) -> None:
    """Print the ASCII art header, if it is available."""
    try:
        art = BANNER_FILE.read_text(encoding="utf-8").rstrip("\n")
    except OSError:
        art = "RapidRepoPull"
    click.secho(art, fg="cyan")
    click.secho(f"  v{version}  --  clone your security toolkit, fast\n", fg="bright_black")


def info(message: str) -> None:
    click.secho(f"[*] {message}", fg="blue")


def warn(message: str) -> None:
    click.secho(f"[!] {message}", fg="yellow", err=True)


def error(message: str) -> None:
    click.secho(f"[x] {message}", fg="red", err=True)


def report(result: Result, *, done: int, total: int, verbose: bool = False) -> None:
    """Print a single repository's outcome as it completes."""
    marker, colour = _STATUS_STYLE[result.status]
    counter = click.style(f"({done}/{total})", fg="bright_black")
    line = f"{click.style(marker, fg=colour, bold=True)} {counter} {result.repo}"

    detail = result.detail
    if verbose and result.duration:
        extra = f"{result.duration:.1f}s"
        if result.attempts > 1:
            extra += f", {result.attempts} attempts"
        detail = f"{detail} [{extra}]" if detail else f"[{extra}]"
    if detail and (result.status is Status.FAILED or verbose):
        line += click.style(f" -- {detail}", fg="bright_black")

    click.echo(line)


def summarise(summary: Summary, *, output_dir: Path, elapsed: float) -> None:
    """Print the closing tally."""
    cloned = len(summary.of(Status.CLONED))
    updated = len(summary.of(Status.UPDATED))
    skipped = len(summary.of(Status.SKIPPED))
    failed = summary.failures

    click.echo()
    if summary.interrupted:
        click.secho("Interrupted -- stopped starting new work.", fg="yellow", bold=True)

    parts = [
        click.style(f"{cloned} cloned", fg="green"),
        click.style(f"{updated} updated", fg="cyan"),
        click.style(f"{skipped} skipped", fg="yellow"),
        click.style(f"{len(failed)} failed", fg="red" if failed else "green"),
    ]
    click.echo("  ".join(parts) + click.style(f"   in {elapsed:.1f}s", fg="bright_black"))
    click.secho(f"Output directory: {output_dir}", fg="bright_black")

    if failed:
        click.echo()
        click.secho("Failed:", fg="red", bold=True)
        for result in failed:
            click.echo(f"  {result.repo}: {result.detail}")


def confirm_tty() -> bool:
    """Whether we are attached to an interactive terminal."""
    return sys.stdout.isatty()


def note_problems(problems, source: str | None = None) -> None:
    """Warn about unparseable lines in a repository list."""
    if not problems:
        return
    where = f" in {source}" if source else ""
    warn(f"Skipped {len(problems)} unreadable line(s){where}:")
    for lineno, text, reason in problems[:10]:
        warn(f"  line {lineno}: {text!r} -- {reason}")
    if len(problems) > 10:
        warn(f"  ... and {len(problems) - 10} more")


def show_tags(counts: dict, *, total: int, untagged: int = 0) -> None:
    """Print the tags a list defines and how many repositories carry each."""
    if not counts:
        warn("This list defines no tags.")
        info("Add '# @tag: name' above a group of repositories to make one.")
        return

    width = max(len(tag) for tag in counts)
    click.secho("Tags:", bold=True)
    for tag, count in counts.items():
        click.echo(f"  {click.style(tag.ljust(width), fg='cyan')}  {count}")

    click.echo()
    click.secho(f"{len(counts)} tags over {total} repositories", fg="bright_black")
    if untagged:
        click.secho(
            f"{untagged} carry no tag, so --tag never selects them.",
            fg="bright_black",
        )


def report_changes(changes, *, verbose: bool = False) -> None:
    """Say which repositories moved since the last run."""
    if not changes:
        return

    new = [c for c in changes if c.is_new]
    moved = [c for c in changes if not c.is_new]

    parts = []
    if new:
        parts.append(f"{len(new)} new")
    if moved:
        parts.append(f"{len(moved)} updated")
    info(f"Commits recorded: {', '.join(parts)}")

    shown = moved if not verbose else changes
    for change in shown[:20]:
        click.secho(f"    {change.slug}: {change.short()}", fg="bright_black")
    if len(shown) > 20:
        click.secho(f"    ... and {len(shown) - 20} more", fg="bright_black")


def report_prune(stale, *, output_dir: Path, dry_run: bool = False) -> None:
    """List clones that are no longer in the repository list."""
    if not stale:
        if dry_run:
            info("Nothing to prune.")
        return

    click.echo()
    verb = "would be removed" if dry_run else "are no longer in the list"
    click.secho(f"{len(stale)} clone(s) {verb}:", fg="yellow", bold=True)
    for entry in stale:
        click.echo(f"  {output_dir / entry.name}  ({entry.slug})")
