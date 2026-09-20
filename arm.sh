#!/usr/bin/env bash
# Install RapidRepoPull into a virtualenv without running it.

source "$(dirname "$0")/_setup.sh"
rrp_setup

echo
echo "${green}RapidRepoPull is ARMED and ready for testing.${reset}"
echo "Activate the environment in your shell with:"
echo "    source $(dirname "$0")/venv/bin/activate"
echo "then run 'rapidrepopull --help' (or 'rrp --help')."
