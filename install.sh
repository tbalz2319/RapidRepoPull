#!/usr/bin/env bash
# Install RapidRepoPull into a virtualenv and run it with the default list.

source "$(dirname "$0")/_setup.sh"
rrp_setup

time rapidrepopull -t 32
