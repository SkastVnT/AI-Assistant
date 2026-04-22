"""Pytest wrapper that runs the Node-based tests for static/js/modules/timeline.js.

The timeline module is pure JS (no DOM, no fetch), and the test file lives at
``tests/test_timeline.mjs``. Here we just shell out to ``node`` and assert
the exit code. If node is not available we skip — the JS code still works
in the browser; the test just cannot run in this environment.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
TEST_FILE = Path(__file__).parent / "test_timeline.mjs"


@pytest.mark.skipif(NODE is None, reason="node executable not on PATH")
def test_timeline_module_passes_node_suite():
    assert TEST_FILE.exists(), f"missing {TEST_FILE}"
    proc = subprocess.run(
        [NODE, str(TEST_FILE)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    # Always show node output so failures are debuggable in CI.
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print("STDERR:", proc.stderr)
    assert proc.returncode == 0, (
        f"timeline node tests failed (exit {proc.returncode}). "
        f"See captured stdout above."
    )
