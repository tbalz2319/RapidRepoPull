#!/usr/bin/env bash
# Fast-forward every repository that has already been cloned.
#
# Since 4.0 this is just RapidRepoPull's own --update mode, which pulls in
# parallel and retries transient network failures.

set -euo pipefail

root=$(cd "$(dirname "$0")" && pwd)
target="${1:-repos}"

if [ -x "${root}/venv/bin/rapidrepopull" ]; then
    rrp="${root}/venv/bin/rapidrepopull"
elif command -v rapidrepopull >/dev/null 2>&1; then
    rrp=rapidrepopull
else
    echo "rapidrepopull is not installed. Run ./arm.sh first." >&2
    exit 1
fi

exec "${rrp}" --update -o "${target}" -v
