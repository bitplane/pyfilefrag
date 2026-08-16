import json
from types import SimpleNamespace

import pytest

from filefrag.device import Device
from filefrag.filemap import FileMap


def install_filemap_mocks(monkeypatch, path):
    stats = SimpleNamespace(st_dev=123, st_ino=456, st_mtime=789.5)
    device = Device()
    device.id = stats.st_dev
    device.type = "block"
    device.block_size = 4096
    device.source = "/dev/example"
    closed = []

    monkeypatch.setattr("filefrag.filemap.os.stat", lambda target: stats)
    monkeypatch.setattr(Device, "from_path", lambda target: device)
    monkeypatch.setattr("filefrag.filemap.os.open", lambda target, flags: 42)
    monkeypatch.setattr("filefrag.filemap.os.close", closed.append)
    monkeypatch.setattr(
        "filefrag.filemap.fie.get_extents",
        lambda fd: [
            {"logical": 0, "physical": 4096, "length": 4096, "flags": 0},
            {"logical": 4096, "physical": 8192, "length": 4096, "flags": 1},
        ],
    )
    return stats, device, closed


def test_filemap_loads_and_formats_extents(monkeypatch, tmp_path):
    path = tmp_path / "example"
    stats, device, closed = install_filemap_mocks(monkeypatch, path)

    filemap = FileMap(path)

    assert filemap.path == str(path)
    assert filemap.device is device
    assert filemap.inode == stats.st_ino
    assert filemap.mtime == stats.st_mtime
    assert [extent.physical for extent in filemap] == [4096, 8192]
    assert closed == [42]
    assert repr(filemap) == f"<FileMap(path={path}, extents=2)>"

    text = format(filemap, "v")
    assert f"File: {path}" in text
    assert "Number of Extents: 2" in text
    assert "0: Extent(logical=0, physical=4096, length=4096, flags=0x0 [])" in text

    data = json.loads(format(filemap, "j"))
    assert data["device"] == {
        "type": "block",
        "id": 123,
        "block_size": 4096,
        "source": "/dev/example",
    }
    assert data["extents"][1]["flags_readable"] == ["last"]


def test_filemap_rejects_missing_path(monkeypatch):
    def missing(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr("filefrag.filemap.os.stat", missing)

    with pytest.raises(ValueError, match="Path /missing does not exist"):
        FileMap("/missing")


def test_filemap_closes_file_when_extent_lookup_fails(monkeypatch, tmp_path):
    path = tmp_path / "example"
    _, _, closed = install_filemap_mocks(monkeypatch, path)

    def fail(fd):
        raise RuntimeError("ioctl failed")

    monkeypatch.setattr("filefrag.filemap.fie.get_extents", fail)

    with pytest.raises(RuntimeError, match="ioctl failed"):
        FileMap(path)
    assert closed == [42]


def test_filemap_staleness(monkeypatch):
    filemap = FileMap.__new__(FileMap)
    filemap.path = "/data/file"
    filemap.device = Device()
    filemap.device.id = 123
    filemap.inode = 456
    filemap.mtime = 789.5

    monkeypatch.setattr(
        "filefrag.filemap.os.stat",
        lambda path: SimpleNamespace(st_dev=123, st_ino=456, st_mtime=789.5),
    )
    assert filemap.check_stale() is False

    monkeypatch.setattr(
        "filefrag.filemap.os.stat",
        lambda path: SimpleNamespace(st_dev=999, st_ino=456, st_mtime=789.5),
    )
    assert filemap.check_stale() is True

    def missing(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr("filefrag.filemap.os.stat", missing)
    assert filemap.check_stale() is True


def test_filemap_equality():
    first = FileMap.__new__(FileMap)
    second = FileMap.__new__(FileMap)
    first.device = Device()
    second.device = Device()
    first.device.id = second.device.id = 123
    first.inode = second.inode = 456
    first.mtime = second.mtime = 789.5

    assert first == second
    assert first.__eq__(object()) is NotImplemented

    second.mtime = 0
    assert first != second
