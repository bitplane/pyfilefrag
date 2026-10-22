import json
import os
import subprocess
import sys

import pytest

from filefrag.filefrag import main


class StubMap:
    def __init__(self, path):
        if path == "missing":
            raise ValueError("Path missing does not exist.")
        self.path = path

    def __format__(self, spec):
        if "j" in spec.split(":"):
            return json.dumps({"path": self.path, "extents": []}, indent=2)
        return f"{self.path} ({spec})"


@pytest.mark.parametrize("paths", [["first"], ["first", 'second"\nfile']])
def test_json_is_one_complete_document(monkeypatch, capsys, paths):
    monkeypatch.setattr("filefrag.filefrag.FileMap", StubMap)
    monkeypatch.setattr("sys.argv", ["pyfilefrag", "--json", *paths])
    main()
    result = capsys.readouterr()
    data = json.loads(result.out)
    records = [data] if len(paths) == 1 else data
    assert [record["path"] for record in records] == paths
    assert not result.err


def test_json_failure_has_no_partial_output(monkeypatch, capsys):
    monkeypatch.setattr("filefrag.filefrag.FileMap", StubMap)
    monkeypatch.setattr("sys.argv", ["pyfilefrag", "--json", "first", "missing"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    result = capsys.readouterr()
    assert not result.out
    assert "Error processing missing" in result.err


def test_text_output_keeps_multiple_files_and_format_options(monkeypatch, capsys):
    monkeypatch.setattr("filefrag.filefrag.FileMap", StubMap)
    monkeypatch.setattr("sys.argv", ["pyfilefrag", "-x", "-v", "first", "second"])
    main()
    assert capsys.readouterr().out == "first (x:v)\nsecond (x:v)\n"


def test_fifo_does_not_block_cli_or_device_lookup(tmp_path):
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    result = subprocess.run(
        [sys.executable, "-m", "filefrag", str(fifo)],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 1
    assert "not a regular file" in result.stderr
    assert not result.stdout

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from filefrag import Device; import sys; "
            "print(Device.from_path(sys.argv[1]))",
            str(fifo),
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
