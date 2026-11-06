"""Compile supercollidermcp/synthdefs/synthdefs.scd into .scsyndef files.

Needs sclang (SuperCollider 3.10+). It runs headless, so no IDE or display is needed.

    python scripts/build_synthdefs.py

Environment overrides:
    SCLANG       path to the sclang binary (default: found on PATH)
    SCLANG_CONF  path to a sclang_conf.yaml, passed as `sclang -l`
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SYNTHDEF_DIR = Path(__file__).resolve().parent.parent / "supercollidermcp" / "synthdefs"
SOURCE = SYNTHDEF_DIR / "synthdefs.scd"


def main() -> int:
    sclang = os.environ.get("SCLANG") or shutil.which("sclang")
    if not sclang:
        print("sclang not found: install SuperCollider or set SCLANG=/path/to/sclang", file=sys.stderr)
        return 1

    for old in SYNTHDEF_DIR.glob("*.scsyndef"):
        old.unlink()

    cmd = [sclang]
    if conf := os.environ.get("SCLANG_CONF"):
        cmd += ["-l", conf]
    cmd += [str(SOURCE), str(SYNTHDEF_DIR)]

    env = {**os.environ, "QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")}
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
    output = result.stdout + result.stderr
    built = sorted(p.name for p in SYNTHDEF_DIR.glob("*.scsyndef"))
    wrote = re.search(r"wrote (\d+) SynthDefs", output)

    # Judge success by what sclang reports and writes, not by its exit code: headless
    # sclang 3.13 often segfaults while shutting down, after the files are written.
    if "ERROR" in output or not wrote or int(wrote.group(1)) != len(built):
        print(output, file=sys.stderr)
        print("SynthDef build failed", file=sys.stderr)
        return 1

    print(f"built {len(built)} SynthDefs in {SYNTHDEF_DIR}:")
    for name in built:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
