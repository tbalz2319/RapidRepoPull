#!/usr/bin/env bash
# Fast-forward every repository that has already been cloned.
#
# This only touches what is already on disk: it reads each clone's origin
# remote and feeds that list back to RapidRepoPull, so nothing new is
# fetched. To clone missing repositories as well, run rapidrepopull directly.

set -euo pipefail

root=$(cd "$(dirname "$0")" && pwd)
target="${1:-repos}"
dest="${root}/${target}"

if [ ! -d "${dest}" ]; then
    echo "Nothing to update: ${dest} does not exist." >&2
    exit 0
fi

if [ -x "${root}/venv/bin/rapidrepopull" ]; then
    rrp="${root}/venv/bin/rapidrepopull"
elif command -v rapidrepopull >/dev/null 2>&1; then
    rrp=rapidrepopull
else
    echo "rapidrepopull is not installed. Run ./arm.sh first." >&2
    exit 1
fi

list=$(mktemp)
trap 'rm -f "${list}"' EXIT

for dir in "${dest}"/*/; do
    [ -d "${dir}/.git" ] || continue
    url=$(git -C "${dir}" config --get remote.origin.url 2>/dev/null) || continue
    [ -n "${url}" ] && printf '%s\n' "${url}" >> "${list}"
done

count=$(wc -l < "${list}" | tr -d ' ')
if [ "${count}" -eq 0 ]; then
    echo "No git repositories found in ${dest}."
    exit 0
fi

echo "Updating ${count} repositories in ${dest}..."
exec "${rrp}" -f "${list}" -o "${target}" --update -v
