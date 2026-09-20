#!/usr/bin/env bash
# Remove the directory RapidRepoPull clones into.
#
# NOTE: this used to be 'rm -Rf -- */', which is no longer safe: since 4.0 the
# source itself lives in rapidrepopull/ and tests/ alongside the clones.

set -euo pipefail

target="${1:-repos}"
root=$(cd "$(dirname "$0")" && pwd)
dest="${root}/${target}"

if [ ! -d "${dest}" ]; then
    echo "Nothing to clean: ${dest} does not exist."
    exit 0
fi

read -r -p "Remove ${dest} and everything in it? [y/N] " reply
case "${reply}" in
    [yY]*) rm -rf -- "${dest}" && echo "Removed ${dest}" ;;
    *)     echo "Aborted." ;;
esac
