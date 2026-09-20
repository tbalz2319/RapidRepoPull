#!/usr/bin/env python3
"""Backwards-compatible entry point.

The implementation moved into the :mod:`rapidrepopull` package in 4.0.  This
shim keeps ``python rapid.py ...`` working exactly as before; new installs get
the ``rapidrepopull`` (or ``rrp``) command instead.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rapidrepopull.cli import main

if __name__ == "__main__":
    main()
