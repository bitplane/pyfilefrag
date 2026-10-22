import json
import os
import stat
from types import SimpleNamespace

import pytest

from filefrag.device import Device
from filefrag.filemap import FileMap


def install_filemap_mocks(monkeypatch, path):
    stats = SimpleNamespace(
        st_mode=stat.S_IFREG,
        st_dev=123,
        st_ino=456,
        st_mtime=789.5,
        st_mtime_ns=789500000000,
        st_ctime_ns=789500000000,
        st_size=8192,
    )
    device = Device(
        id=stats.st_dev, type="block", block_size=4096, source="/dev/example"
    )
    closed = []

    monkeypatch.setattr("filefrag.filemap.os.fstat", lambda fd: stats)
    monkeypatch.setattr(Device, "from_fd", lambda fd, target: device)
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
    def missing(path, flags):
        raise FileNotFoundError(path)

    monkeypatch.setattr("filefrag.filemap.os.open", missing)

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


def test_failed_update_preserves_existing_state(monkeypatch, tmp_path):
    path = tmp_path / "example"
    install_filemap_mocks(monkeypatch, path)
    filemap = FileMap(path)
    original_state = (
        filemap.path,
        filemap.device,
        filemap.inode,
        filemap.mtime,
        filemap.extents,
    )

    monkeypatch.setattr(
        "filefrag.filemap.os.fstat",
        lambda fd: SimpleNamespace(
            st_mode=stat.S_IFREG, st_dev=999, st_ino=888, st_mtime=777
        ),
    )
    replacement_device = Device(id=999)
    monkeypatch.setattr(Device, "from_fd", lambda fd, target: replacement_device)

    def fail(fd):
        raise RuntimeError("ioctl failed")

    monkeypatch.setattr("filefrag.filemap.fie.get_extents", fail)

    with pytest.raises(RuntimeError, match="ioctl failed"):
        filemap.update()

    assert (
        filemap.path,
        filemap.device,
        filemap.inode,
        filemap.mtime,
        filemap.extents,
    ) == original_state


def test_filemap_staleness(monkeypatch, tmp_path):
    path = tmp_path / "example"
    stats, _, _ = install_filemap_mocks(monkeypatch, path)
    mapping = FileMap(path)
    assert mapping.check_stale() is False
    stats.st_ctime_ns += 1
    assert mapping.check_stale() is True

    def missing(path, flags):
        raise FileNotFoundError(path)

    monkeypatch.setattr("filefrag.filemap.os.open", missing)
    assert mapping.check_stale() is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("logical", 512),
        ("physical", 12288),
        ("length", 2048),
        ("flags", 2048),
    ],
)
def test_staleness_detects_layout_changes_without_timestamp_changes(
    monkeypatch, tmp_path, field, value
):
    path = tmp_path / "example"
    install_filemap_mocks(monkeypatch, path)
    mapping = FileMap(path)
    changed = [
        {"logical": 0, "physical": 4096, "length": 4096, "flags": 0},
        {"logical": 4096, "physical": 8192, "length": 4096, "flags": 1},
    ]
    changed[0][field] = value
    monkeypatch.setattr("filefrag.filemap.fie.get_extents", lambda fd: changed)

    assert mapping.check_stale() is True
    assert mapping != FileMap(path)
    assert mapping.extents[0].physical == 4096


@pytest.mark.parametrize("flags", [2, 4, 7, 0x301])
def test_unresolved_mapping_is_stale(monkeypatch, tmp_path, flags):
    path = tmp_path / "example"
    install_filemap_mocks(monkeypatch, path)
    monkeypatch.setattr(
        "filefrag.filemap.fie.get_extents",
        lambda fd: [
            {"logical": 0, "physical": 0, "length": 4096, "flags": flags},
        ],
    )
    assert FileMap(path).check_stale() is True


def test_filemap_equality(monkeypatch, tmp_path):
    path = tmp_path / "example"
    stats, _, _ = install_filemap_mocks(monkeypatch, path)
    first, second = FileMap(path), FileMap(path)
    assert first == second
    assert first.__eq__(object()) is NotImplemented
    stats.st_mtime_ns += 1
    assert first != FileMap(path)


@pytest.mark.parametrize("relative", [False, True])
def test_symlink_parent_path_opens_requested_inode(monkeypatch, tmp_path, relative):
    target = tmp_path / "outer" / "sub"
    target.mkdir(parents=True)
    (tmp_path / "link").symlink_to(target, target_is_directory=True)
    intended = tmp_path / "outer" / "file"
    intended.write_text("intended")
    (tmp_path / "file").write_text("wrong")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("filefrag.filemap.fie.get_extents", lambda fd: [])
    path = "link/../file" if relative else str(tmp_path / "link/../file")

    mapping = FileMap(path)

    assert mapping.inode == intended.stat().st_ino
    assert os.stat(mapping.path).st_ino == intended.stat().st_ino
    assert mapping.check_stale() is False
    mapping.update()
    assert mapping.inode == intended.stat().st_ino


def test_replacing_file_with_directory_makes_map_stale(monkeypatch, tmp_path):
    path = tmp_path / "file"
    path.touch()
    monkeypatch.setattr("filefrag.filemap.fie.get_extents", lambda fd: [])
    mapping = FileMap(path)
    path.unlink()
    path.mkdir()
    assert mapping.check_stale() is True


def test_directory_mapping_is_supported(monkeypatch, tmp_path):
    monkeypatch.setattr("filefrag.filemap.fie.get_extents", lambda fd: [])
    mapping = FileMap(tmp_path)
    assert mapping.inode == tmp_path.stat().st_ino
    assert mapping.check_stale() is False
