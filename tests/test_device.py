import os
import stat
from io import StringIO
from types import SimpleNamespace

import pytest

from filefrag.device import Device


def test_from_path_populates_device(monkeypatch):
    monkeypatch.setattr("filefrag.device.os.open", lambda path, flags: 42)
    monkeypatch.setattr(
        "filefrag.device.os.fstat", lambda fd: SimpleNamespace(st_dev=123)
    )
    monkeypatch.setattr(
        "filefrag.device.os.fstatvfs", lambda fd: SimpleNamespace(f_bsize=4096)
    )
    closed = []
    monkeypatch.setattr("filefrag.device.os.close", closed.append)
    monkeypatch.setattr(Device, "_get_device_source", lambda path: "/dev/example")
    monkeypatch.setattr(Device, "_get_device_type", lambda device_id, source: "block")

    device = Device.from_path("/data/file")

    assert device.id == 123
    assert device.block_size == 4096
    assert device.source == "/dev/example"
    assert device.type == "block"
    assert repr(device) == (
        "<Device(type=block, id=123, block_size=4096, source=/dev/example)>"
    )
    assert closed == [42]


def test_from_path_leaves_unavailable_device_type_unknown(monkeypatch):
    monkeypatch.setattr("filefrag.device.os.open", lambda path, flags: 42)
    monkeypatch.setattr(
        "filefrag.device.os.fstat", lambda fd: SimpleNamespace(st_dev=123)
    )
    monkeypatch.setattr(
        "filefrag.device.os.fstatvfs", lambda fd: SimpleNamespace(f_bsize=4096)
    )
    monkeypatch.setattr("filefrag.device.os.close", lambda fd: None)
    monkeypatch.setattr(Device, "_get_device_source", lambda path: None)
    monkeypatch.setattr("filefrag.device.os.path.exists", lambda path: False)

    assert Device.from_path("/data/file").type is None


def test_from_path_rejects_missing_path(monkeypatch):
    def missing(path, flags):
        raise FileNotFoundError(path)

    monkeypatch.setattr("filefrag.device.os.open", missing)

    with pytest.raises(ValueError, match="Path /missing does not exist"):
        Device.from_path("/missing")


def mock_proc_files(monkeypatch, fdinfo, mountinfo):
    def read_proc(path, *args, **kwargs):
        if path == "/proc/self/fdinfo/42":
            return StringIO(fdinfo)
        assert path == "/proc/self/mountinfo"
        return StringIO(mountinfo)

    monkeypatch.setattr("builtins.open", read_proc)


def test_get_device_source_matches_descriptor_mount(monkeypatch):
    mock_proc_files(
        monkeypatch,
        "pos: 0\nmnt_id: 12\n",
        """11 1 8:1 / / rw - ext4 /dev/root rw
12 11 8:2 /subdir /mnt/bind rw shared:4 - ext4 /dev/data rw
13 11 8:3 / /mnt/bind rw - ext4 /dev/overmounted rw
""",
    )
    assert Device._get_device_source(42) == "/dev/data"


def test_get_device_source_decodes_source_escapes(monkeypatch):
    mock_proc_files(
        monkeypatch,
        "mnt_id: 12\n",
        r"12 1 8:2 / /mnt/data rw - ext4 /dev/my\040disk rw" + "\n",
    )
    assert Device._get_device_source(42) == "/dev/my disk"


@pytest.mark.parametrize("fdinfo", ["pos: 0\n", "mnt_id: 99\n"])
def test_get_device_source_returns_none_without_mount(monkeypatch, fdinfo):
    mock_proc_files(monkeypatch, fdinfo, "11 1 8:1 / / rw - ext4 /dev/root rw\n")
    assert Device._get_device_source(42) is None


def test_from_path_resolves_relative_paths_and_symlinks(monkeypatch, tmp_path):
    target = tmp_path / "file"
    target.touch()
    monkeypatch.chdir(tmp_path)
    assert Device.from_path("file").source == Device.from_path(str(target)).source
    link = tmp_path / "proc-link"
    link.symlink_to("/proc/version")
    actual = Device.from_path(str(link))
    expected = Device.from_path("/proc/version")
    assert actual.id == expected.id
    assert actual.source == expected.source


def test_source_lookup_survives_unlink(tmp_path):
    path = tmp_path / "file"
    path.touch()
    expected = Device.from_path(str(path))
    fd = os.open(path, os.O_RDONLY)
    try:
        path.unlink()
        actual = Device.from_fd(fd, str(path))
        assert actual.source == expected.source
        assert actual.id == expected.id
    finally:
        os.close(fd)


@pytest.mark.parametrize("source", ["proc", "tmpfs", "overlay", "server:/export"])
def test_virtual_mount_sources_are_not_block_devices(monkeypatch, source):
    monkeypatch.setattr("filefrag.device.os.path.exists", lambda path: False)
    assert Device._get_device_type(123, source) == "virtual"


def test_block_device_is_detected_without_source_node(monkeypatch):
    monkeypatch.setattr(
        "filefrag.device.os.path.exists", lambda path: path == "/sys/dev/block/8:1"
    )
    assert Device._get_device_type(os.makedev(8, 1), "/dev/missing") == "block"


@pytest.mark.parametrize(
    "mode,expected", [(stat.S_IFBLK, "block"), (stat.S_IFREG, "virtual")]
)
def test_source_node_type_is_checked(monkeypatch, mode, expected):
    monkeypatch.setattr("filefrag.device.os.path.exists", lambda path: False)
    monkeypatch.setattr(
        "filefrag.device.os.stat", lambda path: SimpleNamespace(st_mode=mode)
    )
    assert Device._get_device_type(123, "/dev/source") == expected


def test_inaccessible_source_type_is_unknown(monkeypatch):
    monkeypatch.setattr("filefrag.device.os.path.exists", lambda path: False)

    def inaccessible(path):
        raise PermissionError(path)

    monkeypatch.setattr("filefrag.device.os.stat", inaccessible)
    assert Device._get_device_type(123, "/dev/source") is None


def test_proc_is_virtual():
    assert Device.from_path("/proc/version").type == "virtual"


@pytest.mark.parametrize("restricted", ["/proc/self/fdinfo/", "/proc/self/mountinfo"])
def test_restricted_mount_metadata_does_not_prevent_device_lookup(
    monkeypatch, tmp_path, restricted
):
    path = tmp_path / "file"
    path.touch()
    real_open = open

    def restricted_open(target, *args, **kwargs):
        if str(target).startswith(restricted):
            raise PermissionError("mount metadata restricted")
        return real_open(target, *args, **kwargs)

    monkeypatch.setattr("builtins.open", restricted_open)
    device = Device.from_path(str(path))
    assert device.id == path.stat().st_dev
    assert device.source is None
