"""Make the project root importable as the ``game`` package.

pytest loads this root-level conftest before collecting any tests, so inserting
the repo root onto ``sys.path`` here guarantees ``import game`` works no matter
how the suite is launched — bare ``pytest``, ``python -m pytest``, an IDE, or CI
— independent of pytest's import mode or the ``pythonpath`` ini option.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
