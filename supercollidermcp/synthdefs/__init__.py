"""Compiled SynthDefs shipped with the package.

The source is ``synthdefs.scd`` in this directory; rebuild the ``.scsyndef``
files with ``python scripts/build_synthdefs.py`` after changing it.
"""

from __future__ import annotations

from pathlib import Path

SYNTHDEF_DIR = Path(__file__).resolve().parent


def compiled_synthdefs() -> dict[str, bytes]:
    """Return ``{synthdef name: compiled bytes}`` for every shipped SynthDef."""
    defs = {path.stem: path.read_bytes() for path in sorted(SYNTHDEF_DIR.glob("*.scsyndef"))}
    if not defs:
        raise RuntimeError(f"no compiled SynthDefs found in {SYNTHDEF_DIR}; run scripts/build_synthdefs.py")
    return defs
