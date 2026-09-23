"""Make `pytest` work from a fresh clone, with nothing installed.

The package lives in `src/`, so `import urdunlp` only resolves after
`pip install -e .`. CI does that, which is why CI was green while cloning the
repository and running `pytest` produced:

    ModuleNotFoundError: No module named 'urdunlp'

A project whose whole claim is "zero dependencies, nothing to download" should
not need an install step before its own tests run. If the package IS installed,
this changes nothing - the installed copy is found first either way.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
