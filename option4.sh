#!/usr/bin/env bash
# Install RapidRepoPull into a virtualenv and show the options.

source "$(dirname "$0")/_setup.sh"
rrp_setup

echo
rapidrepopull --help
echo
echo "${green}Activate the environment in your shell with:${reset}"
echo "    source $(dirname "$0")/venv/bin/activate"
