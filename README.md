# RapidRepoPull

![os](https://img.shields.io/badge/OS-Linux,%20macOS-yellow.svg)
![rapidrepoinstallver](https://img.shields.io/badge/version-4.0.0-red.svg)
![python](https://img.shields.io/badge/python-3.9+-blue.svg)
[![Twitter](https://img.shields.io/badge/twitter-@xtbalz-blue.svg)](https://twitter.com/xtbalz)
[![CodeFactor](https://www.codefactor.io/repository/github/tbalz2319/rapidrepopull/badge)](https://www.codefactor.io/repository/github/tbalz2319/rapidrepopull)
[![tests](https://github.com/tbalz2319/RapidRepoPull/actions/workflows/tests.yml/badge.svg)](https://github.com/tbalz2319/RapidRepoPull/actions/workflows/tests.yml)

![alt text](https://github.com/tbalz2319/RapidRepoPull/blob/master/rrp.png)

## Created and Maintained by

- Talal Balouch (Twitter @xtbalz)

## Description

RapidRepoPull clones and maintains a curated list of security repositories in
parallel. Point it at the bundled list, your own text file, or any web page full
of GitHub links, and it will clone everything at once -- then fast-forward it all
later with a single `--update`.

It is particularly useful for the corpus repositories that no package manager
covers: SecLists, PayloadsAllTheThings, Yara rules, payload collections and
awesome-lists, which go stale silently and are tedious to refresh by hand.

## Requirements

- Python 3.9 or newer
- `git` on your PATH

    ```sudo apt-get install git python3-venv```

## Install

```bash
git clone https://github.com/tbalz2319/RapidRepoPull.git
cd RapidRepoPull
pip install .
```

This puts two identical commands on your PATH: `rapidrepopull` and the short
alias `rrp`.

To install into a virtualenv instead, run `./arm.sh`, which creates `venv/`,
installs the package and tells you how to activate it.

## Usage

```
Usage: rapidrepopull [OPTIONS]

Options:
  -v, --verbose                   Print detailed progress and timings.
  -f, --file, --fileinput FILE    Text file listing repositories to clone
                                  [default: the bundled list]
  -u, --url TEXT                  Scrape a web page for repository links and
                                  clone those.
  -t, --threads, --thread INTEGER Concurrent git processes (1-64).  [default: 16]
  -o, --output-dir DIRECTORY      Directory to clone into.  [default: repos]
  --depth INTEGER                 Make shallow clones with this history depth
                                  (much faster; try 1).
  --ssh                           Clone over SSH instead of HTTPS.
  --update / --no-update          Fast-forward repositories that are already
                                  present.  [default: update]
  --timeout INTEGER               Seconds before a single git operation is
                                  abandoned.  [default: 600]
  --retries INTEGER               Extra attempts for network failures.  [default: 2]
  -n, --dry-run                   List what would be done and exit.
  --save-list FILE                Write the resolved repository list to this file.
  --insecure                      Skip TLS verification when scraping.
  --no-banner                     Suppress the ASCII art header.
  -V, --version                   Show the version and exit.
  -h, --help                      Show this message and exit.
```

### Examples

Clone the bundled list into `./repos`:

```bash
rapidrepopull
```

Shallow clones, which is dramatically faster and smaller (SecLists alone is
over a gigabyte with full history):

```bash
rapidrepopull --depth 1
```

Use your own list, 32 clones at a time:

```bash
rapidrepopull -f mytools.txt -t 32
```

Refresh everything already cloned:

```bash
rapidrepopull --update
```

Scrape a page and clone every repository it links to:

```bash
rapidrepopull -v -u https://apsdehal.in/awesome-ctf
```

See what would happen without touching the disk:

```bash
rapidrepopull --dry-run
```

### Repository list format

One repository per line. Blank lines and `#` comments are ignored, and any of
these forms work:

```
owner/repo
https://github.com/owner/repo
https://github.com/owner/repo.git
git@github.com:owner/repo.git
```

The bundled list lives at `rapidrepopull/data/default.txt`. A `default.txt` in
your working directory overrides it, or pass your own with `-f`.

## Docker

```bash
docker-compose up --build
```

Clones land in `./repos` on the host.

## Helper scripts

| Script | |
|---|---|
| `./install.sh` | create a venv, install, and run against the default list |
| `./arm.sh` | create a venv and install, without running |
| `./option4.sh` | create a venv, install, and print the options |
| `./update_repos.sh` | fast-forward everything already cloned |
| `./clean.sh` | remove the `repos/` directory (asks first) |

## Development

```bash
pip install -e '.[dev]'
pytest
ruff check .
```

## Contribute

- Pull requests welcomed
- Repositories that have moved or gone dead are the most useful fixes; the
  bundled list rots faster than the code does
