#!/usr/bin/env bash
# Shared virtualenv setup, sourced by install.sh, arm.sh and option4.sh.
# Leaves an activated venv with RapidRepoPull installed on PATH as `rapidrepopull` / `rrp`.

set -euo pipefail

green=$(tput setaf 2 2>/dev/null || true)
cyan=$(tput setaf 6 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

rrp_setup() {
    local root
    root=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

    echo "${green}Setting up Python3 virtual env${reset}"
    python3 -m venv "${root}/venv"

    echo "${cyan}Activating virtual env${reset}"
    # shellcheck disable=SC1091
    source "${root}/venv/bin/activate"

    echo "${cyan}Upgrading pip${reset}"
    pip install --quiet --upgrade pip

    echo "${cyan}Installing RapidRepoPull${reset}"
    pip install --quiet "${root}"
}
