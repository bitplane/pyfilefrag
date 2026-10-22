import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("status", [0, 1, 5])
def test_coverage_script_propagates_test_status(tmp_path, status):
    summary = tmp_path / "htmlcov" / "missing_coverage.txt"
    summary.parent.mkdir()
    summary.write_text("obsolete summary")
    activate = tmp_path / ".venv" / "bin" / "activate"
    activate.parent.mkdir(parents=True)
    activate.write_text("")
    pytest_stub = activate.parent / "pytest"
    pytest_stub.write_text(
        f"#!/bin/sh\necho 'Missing coverage summary'\nexit {status}\n"
    )
    pytest_stub.chmod(0o755)
    env = dict(os.environ, PATH=f"{activate.parent}:{os.environ['PATH']}")

    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "coverage.sh"), "filefrag"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == status
    assert summary.read_text() == "Missing coverage summary\n"
    assert "Missing coverage summary" in result.stdout
    assert (
        "Missing coverage summary"
        in (tmp_path / "htmlcov" / "coverage_report.txt").read_text()
    )
