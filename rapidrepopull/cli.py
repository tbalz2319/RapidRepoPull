"""Command line interface.

Every flag the 3.x CLI accepted still works and still means the same thing;
the additions are all opt-in.
"""

from __future__ import annotations

import contextlib
import shutil
import sys
import time
from pathlib import Path

import click

from rapidrepopull import __version__, ui
from rapidrepopull import manifest as manifest_mod
from rapidrepopull.cloner import (
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_WORKERS,
    MAX_WORKERS,
    GitNotFound,
    clone_all,
    find_git,
)
from rapidrepopull.repolist import (
    Repo,
    all_tags,
    dedupe,
    default_list_path,
    filter_by_tags,
    load_list,
)
from rapidrepopull.scraper import ScrapeError, scrape

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"], "max_content_width": 100}


def _split_tags(values: tuple[str, ...]) -> list[str]:
    """Accept both ``--tag a --tag b`` and ``--tag a,b``."""
    out: list[str] = []
    for value in values:
        out.extend(part for part in value.split(",") if part.strip())
    return out


def _prune(stale, *, output_dir: Path, assume_yes: bool) -> list:
    """Offer to delete clones whose entries have left the list."""
    if not stale:
        ui.info("Nothing to prune.")
        return []

    ui.report_prune(stale, output_dir=output_dir, dry_run=False)
    if not assume_yes and not click.confirm(
        f"Remove {len(stale)} director{'y' if len(stale) == 1 else 'ies'}?",
        default=False,
    ):
        ui.info("Left them in place.")
        return []

    removed = []
    for entry in stale:
        target = output_dir / entry.name
        try:
            shutil.rmtree(target)
        except OSError as exc:
            ui.warn(f"Could not remove {target}: {exc}")
        else:
            removed.append(entry)
    ui.info(f"Removed {len(removed)} of {len(stale)}.")
    return removed


def _collect(
    file_path: Path | None,
    url: str | None,
    *,
    timeout: int,
    verify: bool,
    verbose: bool,
) -> list[Repo]:
    """Build the repository list from the requested sources.

    When neither ``-f`` nor ``-u`` is given we fall back to the bundled list.
    Supplying ``-u`` alone no longer silently also clones the default list --
    that was a long-standing surprise in 3.x.
    """
    repos: list[Repo] = []

    if file_path is None and url is None:
        file_path = default_list_path()
        if verbose:
            ui.info(f"No source given, using the bundled list: {file_path}")

    if file_path is not None:
        if not file_path.is_file():
            raise click.FileError(str(file_path), hint="no such repository list")
        found, problems = load_list(file_path)
        ui.note_problems(problems, source=str(file_path))
        if verbose:
            ui.info(f"Read {len(found)} repositories from {file_path}")
        repos.extend(found)

    if url is not None:
        if verbose:
            ui.info(f"Scraping {url}")
        found = scrape(url, timeout=timeout, verify=verify)
        if verbose:
            ui.info(f"Found {len(found)} repositories on the page")
        repos.extend(found)

    return dedupe(repos)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-v", "--verbose", is_flag=True, help="Print detailed progress and timings.")
@click.option(
    "-f",
    "--file",
    "--fileinput",
    "file_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Text file listing repositories to clone  [default: the bundled list]",
)
@click.option(
    "-u",
    "--url",
    default=None,
    help="Scrape a web page for repository links and clone those.",
)
@click.option(
    "-t",
    "--threads",
    "--thread",
    "workers",
    type=int,
    default=DEFAULT_WORKERS,
    show_default=True,
    help=f"Concurrent git processes (1-{MAX_WORKERS}; 0 or less means the default).",
)
@click.option(
    "-o",
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("repos"),
    show_default=True,
    help="Directory to clone into.",
)
@click.option(
    "--depth",
    type=int,
    default=None,
    help="Make shallow clones with this history depth (much faster; try 1).",
)
@click.option("--ssh", is_flag=True, help="Clone over SSH instead of HTTPS.")
@click.option(
    "--update/--no-update",
    default=True,
    show_default=True,
    help="Fast-forward repositories that are already present.",
)
@click.option(
    "--timeout",
    type=int,
    default=DEFAULT_TIMEOUT,
    show_default=True,
    help="Seconds before a single git operation is abandoned.",
)
@click.option(
    "--retries",
    type=int,
    default=DEFAULT_RETRIES,
    show_default=True,
    help="Extra attempts for network failures.",
)
@click.option(
    "--tag",
    "tags",
    multiple=True,
    metavar="TAG",
    help="Only handle repositories with this tag. Repeatable, or comma-separated.",
)
@click.option(
    "--list-tags",
    is_flag=True,
    help="Print the tags the list defines, with repository counts, and exit.",
)
@click.option(
    "--prune",
    is_flag=True,
    help="Remove clones whose entries have left the list (asks first).",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Answer yes to confirmation prompts, for unattended runs.",
)
@click.option(
    "--no-manifest",
    is_flag=True,
    help=f"Do not write {manifest_mod.MANIFEST_NAME} into the output directory.",
)
@click.option("-n", "--dry-run", is_flag=True, help="List what would be done and exit.")
@click.option(
    "--save-list",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the resolved repository list to this file.",
)
@click.option(
    "--insecure",
    is_flag=True,
    help="Skip TLS verification when scraping (not recommended).",
)
@click.option("--no-banner", is_flag=True, help="Suppress the ASCII art header.")
@click.version_option(__version__, "-V", "--version", prog_name="RapidRepoPull")
def main(
    verbose: bool,
    file_path: Path | None,
    url: str | None,
    workers: int,
    output_dir: Path,
    depth: int | None,
    ssh: bool,
    update: bool,
    timeout: int,
    retries: int,
    tags: tuple[str, ...],
    list_tags: bool,
    prune: bool,
    yes: bool,
    no_manifest: bool,
    dry_run: bool,
    save_list: Path | None,
    insecure: bool,
    no_banner: bool,
) -> None:
    """Clone and maintain a curated list of security repositories, in parallel.

    \b
    Examples:
      rapidrepopull                          clone the bundled list into ./repos
      rapidrepopull -f mytools.txt -t 32     use your own list, 32 at a time
      rapidrepopull --depth 1                shallow clones, much faster
      rapidrepopull --update                 refresh everything already cloned
      rapidrepopull --tag wordlists,recon    clone one group only
      rapidrepopull -u https://example.com/awesome-ctf
    """
    if not no_banner:
        ui.banner(__version__)

    if workers < 1:
        workers = DEFAULT_WORKERS
    if workers > MAX_WORKERS:
        ui.warn(f"Capping concurrency at {MAX_WORKERS}; more does not go faster.")
        workers = MAX_WORKERS
    if depth is not None and depth < 1:
        raise click.BadParameter("--depth must be 1 or greater", param_hint="--depth")
    if timeout < 1:
        raise click.BadParameter("--timeout must be 1 or greater", param_hint="--timeout")
    if retries < 0:
        raise click.BadParameter("--retries cannot be negative", param_hint="--retries")

    try:
        repos = _collect(
            file_path, url, timeout=timeout, verify=not insecure, verbose=verbose
        )
    except ScrapeError as exc:
        ui.error(str(exc))
        sys.exit(2)

    if not repos:
        ui.error("No repositories to process.")
        sys.exit(2)

    if list_tags:
        ui.show_tags(
            all_tags(repos),
            total=len(repos),
            untagged=sum(1 for r in repos if not r.tags),
        )
        return

    # Pruning compares against the whole list, never the --tag subset: a
    # tagged run must not decide that every other tag has "left the list".
    all_repos = list(repos)

    wanted = _split_tags(tags)
    if wanted:
        repos, unknown = filter_by_tags(repos, wanted)
        if unknown:
            ui.warn(f"No repository is tagged {', '.join(unknown)}.")
        if not repos:
            ui.error("No repositories matched the requested tags.")
            ui.info("Run with --list-tags to see what is available.")
            sys.exit(2)
        if verbose:
            ui.info(f"{len(repos)} repositories match {', '.join(sorted(wanted))}")

    if save_list is not None:
        save_list.parent.mkdir(parents=True, exist_ok=True)
        save_list.write_text("\n".join(r.url() for r in repos) + "\n", encoding="utf-8")
        ui.info(f"Wrote {len(repos)} repositories to {save_list}")

    output_dir = output_dir.expanduser()

    if dry_run:
        ui.info(f"{len(repos)} repositories would go to {output_dir.resolve()}:")
        for repo in repos:
            click.echo(f"  {repo.url(ssh=ssh)}")
        if prune:
            stale = manifest_mod.stale(
                manifest_mod.load(output_dir), all_repos, output_dir=output_dir
            )
            ui.report_prune(stale, output_dir=output_dir, dry_run=True)
        return

    ui.info(
        f"Processing {len(repos)} repositories into {output_dir} "
        f"with {min(workers, len(repos))} workers"
    )
    click.echo()

    done = 0
    total = len(repos)

    def on_result(result) -> None:
        nonlocal done
        done += 1
        ui.report(result, done=done, total=total, verbose=verbose)

    started = time.monotonic()
    try:
        summary = clone_all(
            repos,
            output_dir=output_dir,
            workers=workers,
            ssh=ssh,
            depth=depth,
            update=update,
            timeout=timeout,
            retries=retries,
            on_result=on_result,
        )
    except GitNotFound as exc:
        ui.error(str(exc))
        sys.exit(2)

    ui.summarise(summary, output_dir=output_dir.resolve(), elapsed=time.monotonic() - started)

    manifest = manifest_mod.load(output_dir)
    if not no_manifest:
        try:
            git = find_git()
        except GitNotFound:  # pragma: no cover - clone_all would have failed first
            git = None
        if git is not None:
            changes = manifest_mod.record(
                manifest, summary.results, git=git, output_dir=output_dir
            )
            try:
                manifest.save()
            except OSError as exc:
                ui.warn(f"Could not write the manifest: {exc}")
            else:
                ui.report_changes(changes, verbose=verbose)

    if prune:
        stale = manifest_mod.stale(manifest, all_repos, output_dir=output_dir)
        removed = _prune(stale, output_dir=output_dir, assume_yes=yes)
        if removed:
            for entry in removed:
                manifest.entries.pop(entry.slug, None)
            if not no_manifest:
                with contextlib.suppress(OSError):
                    manifest.save()

    sys.exit(summary.exit_code)


if __name__ == "__main__":
    main()
