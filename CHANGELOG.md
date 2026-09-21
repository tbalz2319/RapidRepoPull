# 4.2.0

Curation pass. 4.1 added `--doctor`; running it showed that half the bundled
list had not been touched in years, so this release acts on that.

## Removed from the default list
Sixteen entries are now commented out at the bottom of `default.txt` with a
reason and a last-commit date. They still clone if uncommented.

- Superseded, with the replacement in the active list: `rebootuser/LinEnum`
  (2020-01), `jondonas/linux-exploit-suggester-2` (2022-01),
  `1N3/IntruderPayloads` (2021-09), `foospidy/payloads` (2021-04),
  `Grunny/zap-cli` (2018-12), `skavngr/rapidscan` (2023-08)
- Abandoned with no successor: `tevora-threat/PowerView3-Aggressor` (2018-07),
  `Cn33liz/p0wnedShell` (2018-09), `SpiderLabs/scavenger` (2018-12),
  `paranoidninja/CarbonCopy` (2019-06), `trustedsec/HoneyBadger` (2019-11),
  `SolomonSklash/chomp-scan` (2020-04), `rvrsh3ll/FindFrontableDomains`
  (2021-05, domain fronting is blocked by the major CDNs),
  `byt3bl33d3r/DeathStar` (2023-12, drives the Empire that moved)
- Archived by their authors: `hlldz/Phant0m`, `chryzsh/awesome-windows-security`

## Added
- `peass-ng/PEASS-ng` (linpeas/winpeas), replacing LinEnum
- `mzet-/linux-exploit-suggester`, replacing linux-exploit-suggester-2
- `projectdiscovery/httpx`, alongside httprobe

## Kept deliberately
Finished-but-standard tools are not dropped just for being old:
`tomnomnom/assetfinder` and `httprobe`, `GhostPack/SharpUp`,
`Coalfire-Research/pymetasploit3`, `OWASP/joomscan`, `21y4d/nmapAutomator`.
They are small, they still work, and nothing has replaced them.

## Notes
- The list is 41 entries, down from 54, and every one was confirmed reachable
- The dates above are each project's last commit on its default branch, which
  is not GitHub's `pushed_at`. `pushed_at` moves on a push to any branch, and
  it made several of these look years fresher than they were -- LinEnum
  reported as 3.0 years idle when its default branch had not moved since
  2020-01

# 4.1.0

Four additions aimed at the parts of 4.0 that were still weak: the list had
no way to know it had rotted, no way to clone a subset, no record of what it
had done, and still only cloned.

## Added
- `--doctor` checks every entry against the GitHub API and reports renames,
  archived projects, deletions, private repositories and anything with no push
  in `--stale-days` (default 730). Non-GitHub remotes are checked with
  `git ls-remote`. `--fix` writes the answers back into the list file, editing
  it line by line so comments, ordering and tags survive; re-running it is a
  no-op. Entries that cannot be cloned exit nonzero, so it works as a CI check
- A weekly `list-health` workflow runs `--doctor` with `GITHUB_TOKEN`, and a
  manual dispatch can run `--fix` and open a pull request
- `--tag` and `--list-tags`. A `# @tag: name` directive labels every repository
  after it until the next directive, and a trailing comment tags one line.
  The bundled list's nine sections are now tags: wordlists, recon, web,
  windows, c2, linux, blueteam, frameworks, reading
- `.rapidrepopull.json` in the output directory records the URL, tags and
  checked-out commit of everything cloned, so a later run reports only what
  actually moved. `--no-manifest` turns it off
- `--prune` removes clones whose entries have left the list. It only considers
  directories the manifest says RapidRepoPull created, asks before deleting
  unless `-y/--yes` is given, and compares against the whole list rather than
  the `--tag` subset
- `--install` builds repositories that declare how: `go.mod`, `pyproject.toml`,
  `setup.py`, `requirements.txt` and `package.json`. It does not run a
  repository's own `install.sh`; cmake, gradle, maven, cargo, Makefiles and
  Visual Studio projects are reported as needing manual steps, and pure-data
  repositories as having nothing to build. Python tools go to pipx or a
  virtualenv inside the clone, never system site-packages

## Changed
- A repository listed twice keeps the union of its tags rather than the first
  set seen, which also merges tags when the same repo arrives from a file and
  from a scraped page

## Notes
- Running `--doctor` over the bundled list found 2 archived repositories and 27
  with no push in over two years. They still clone, so they are annotated
  rather than removed

# 4.0.0

Major rewrite. The single `rapid.py` script is now the `rapidrepopull` package,
with a test suite and a real CLI.

## Added
- Installable package with `rapidrepopull` and `rrp` entry points (`pip install .`)
- `--update` / `--no-update` to fast-forward repositories that are already cloned
- `--depth` for shallow clones (much faster; SecLists alone saves ~1 GB)
- `--ssh` to clone over SSH instead of HTTPS
- `--output-dir` so clones no longer land in the source tree (defaults to `repos/`)
- `--timeout` and `--retries`, with transient network failures retried and
  permanent failures (auth, missing repo) failing fast instead of retrying
- `--dry-run` and `--save-list` to inspect the resolved list without cloning
- `--insecure` and `--no-banner`
- 86 tests, ruff linting, and a GitHub Actions workflow running both on 3.9-3.13

## Changed
- Repository lists now accept `owner/repo`, HTTPS, `.git` and `git@` forms, plus
  `#` comments and blank lines
- The bundled list moved to `rapidrepopull/data/default.txt`; a `default.txt` in
  the working directory still overrides it
- Nonzero exit code when any clone fails, so the tool is usable in scripts
- Thread limit capped at 64 (was unbounded); the default is now 16
- Dockerfile builds the package on python:3.13-alpine and clones to a `/repos`
  volume rather than cloning the source tree into itself
- `clean.sh` no longer runs `rm -Rf -- */` in the source root, which would now
  delete the package itself; it removes the output directory and asks first
- `update_repos.sh` now delegates to `--update` instead of looping `git pull`

## Fixed
- Repositories that had moved or died in the bundled list: BloodHound to
  SpecterOps, Empire to BC-SECURITY, CrackMapExec to Pennyw0rth/NetExec,
  joomscan to OWASP, leonidas to ReversecLabs, Invoke-Phant0m to hlldz/Phant0m,
  awesome-cybersecurity-blueteam to fabacab
- Dropped three dead repositories: bwall/ExtractHosts, Frint0/email-enum,
  vysecurity/ANGRYPUPPY
- Added projectdiscovery/nuclei, j3ssie/Osmedeus and
  chryzsh/awesome-windows-security, which the 3.2.3 notes claimed were in the
  list but which were never actually committed to it

## Removed
- `requirements.txt` (dependencies are declared in `pyproject.toml`)
- `activate_venv.py`, which could not activate a virtualenv in the parent shell
- `.travis.yml`; CI runs on GitHub Actions

## Compatibility
- `python rapid.py ...` still works via a shim, and the legacy `--fileinput` and
  `--thread` flag spellings are still accepted
- Requires Python 3.9 or newer

# 3.2.5
- Fixing issue with giturlparse that using the ssh version of git instead of https
- had to update all default.txt to change all existing repos to match ssh git urls instead of https
- Removed all requirements.txt files which were of no use
# 3.2.4
- Updated the default thread limit from 55 to 65
# 3.2.3
- Adding the https://github.com/j3ssie/Osmedeus repo to the default install list of tools
- Adding the https://github.com/projectdiscovery/nuclei to the default list of tools 
- Adding the https://github.com/chryzsh/awesome-windows-security repo to the default list of tools 
- Update to the readme file 
## 3.2.2

- Adding the https://github.com/FSecureLABS/leonidas repo to the default install list of tools
- Adding the https://github.com/cddmp/enum4linux-ng repo to the default install list of tools
- Update to the readme file
## 3.2.1

- Update to license file date
- Clean up of install.sh script (removed un-needed comments)
- Adding the https://github.com/21y4d/nmapAutomator repo to the default install list of tools

## 3.2.0

- Adding the Linux threat emulation framework "Chain Reactor" to the default
clone list

## 3.1.9

- Update of boot.sh file to increase thread execution of program inside of
Docker container from 75 to 85

## 3.1.8

- Cleanup and maintenance of various comments and spacing issues in various scripts and files

## 3.1.7

- Adding web app recon tools created by @TomNomNom to the default clone list

- The tools are assetfinder and httprobe

## 3.1.6

- Adding John Hammond's CTF Kitana repo to the default clone list

## 3.1.5

- Increasing repo pull threads to 75 from 35 when running the container to pull
  repos

## 3.1.4

- Adding the SpiderLabs Scavenger tool to the default clone list

## 3.1.3

- Adding RapidScan and the foospidy payloads repo for a nice quick
  dir of payloads to have for web application security testing and CTFs

## 3.1.2

- Adding ldapdomaindump tool to default list

## 3.1.1

- Upgrade of all pip packages in requirements.txt

- Added the gobuster tool to the default.txt clone list

- Addressed potential security vulnerability in urllib3

## 3.1.0

- Adding LinEnum, and joomscan to .gitignore

## 3.0.9

- Fixed comment typo in rapid.py and increased the num of pools in the url parser

## 3.0.8

- Adding Joomscan and LinEnum to the default.txt repos to clone

## 3.0.7

- Update to install.sh to use the Cyan color in the script

- Update to install.sh to replace backticks with $() per codefactor

## 3.0.6

- Removed bob.txt and added useful repos to demo.txt

## 3.0.5

- Bash script fixups implemented and testing recommended by codefactor

## 3.0.4

- Removed demo.txt file

- Added rm -f red.txt in clean.sh

## 3.0.3

- Fixed typos in main rapid.py file

- Created a demo.txt file

- Updated dockerfile to specify python3 instead of python

- Updated boot.sh for Docker container to run a minimal number of repositories for demo purposes

## 3.0.2

- Cleaned up @click section comments based on input provided by Codefactor

- Provided comment on second worker_data=[] list purpose

## 3.0.1

- Updated readme file "Use case" section

## 3.0.0

- Updated master branch with new features

- Added the ability to scrape a given url with the -u flag and clone any Github repos which are existing as links

- Added the pip huepy library to the program to help with user cli notifications with colors

## 2.1.4

- Adding rvrsh3ll/FindFrontableDomains to the clone list

## 2.1.3

- Rapid.py file is cleaned up with useful comments on what specific lines of code are doing

## 2.1.2

- Updates to contribute section of readme

## 2.1.1

- Adding the chompscan repo to the default.txt file to be cloned

## 2.1.0

- Externalised repos to text file called default.txt

- Code refacotring optimizations thanks to diego95root!

## 2.0.3

- Adding patator and girurlparse repos to .gitignore file

## 2.0.2

- Uncommented the mass scan repo which was taken out during dev testing

## 2.0.1

- Adding in minor Linter code fixes

## 2.0.0

- New 2.0.0 release includes the following new features

- New CLI based help menu with multiple options

- Ability to Specify user defined text file with custom repos for RapidRepoPull to clone

- Ability to specify how many threads the script takes advantage of

- Code refactored and additional comments added for clarity

- New use option script (option4.sh) created to install dependencies and get script ready for user

- specified text file and the specification for the number of threads to use

## 1.8.5

- Adding the hlldz/Invoke-Phant0m repo to the clone list

## 1.8.4

- Adding jondonas/ in front of broken repo pull for linux-exploit-suggester-2

- Adding the following dirs to .gitignore linux-exploit-suggester-2, CarbonCopy

- Hamburglar email-enum added to .gitignore as well

## 1.8.3

- Adding the "linux-exploit-suggester-2" repo to the clone list

## 1.8.2

- Minor issue fix in repo related to missing ','

## 1.8.1

- Added the Hamburgler tool to the clone list

## 1.8.0

- Added the email-enum tool to the clone list

## 1.7.9

- Added the CarbonCopy tool to the clone list

## 1.7.8

- Install script updated to detect OS and install specific dependencies

- So far, this only works for Kali/Ubuntu/Debian Linux distros

## 1.7.7

- Added image of running program in readme file

## 1.7.6

- Added support for green colored echo statements in update_repos.sh

## 1.7.5

- Green colored text added to echo statements in install.sh

## 1.7.4

- Added support to mass update all repos already cloned instead of re-cloning

## 1.7.3

- Adding support for terminal colors

## 1.7.2

- Added an install.sh to install all dependencies and run script

## 1.7.1

- Added an update.sh script to keep the program updated via Github

## 1.7.0

- Created docker-compose file to build dockerfile

- Cleaned up print statement outputs

- Various updates to readme for clarity

## 1.6.0

- Created a dockerfile for the script

- Created a cleanup bash script

## 1.5.0

- Megreged pull request that fixed up code : "Removed git output, added controlled output with locks"

## 1.4.1

- The repo for Windows Exploit Suggester NG has been added

## 1.4.0

- Cleaned up readme instructions

- Added Massscn to repo list

- Removed un-needed import library

## 1.3.2

- Multiple code fixes and adding in missing ","

- Added a new ASCII text for "RapidRepoPull" displayed after program execution completes

## 1.3.1

- First release version of codebase

## 1.2.1

- code cleanup, removing .git from every entry in list and adding to loop
