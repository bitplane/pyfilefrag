from io import StringIO
from types import SimpleNamespace

import pytest

from filefrag.device import Device


def test_from_path_populates_device(monkeypatch):
    monkeypatch.setattr(
        "filefrag.device.os.stat", lambda path: SimpleNamespace(st_dev=123)
    )
    monkeypatch.setattr(
        "filefrag.device.os.statvfs", lambda path: SimpleNamespace(f_bsize=4096)
    )
    monkeypatch.setattr(Device, "_get_device_source", lambda path: "/dev/example")

    device = Device.from_path("/data/file")

    assert device.id == 123
    assert device.block_size == 4096
    assert device.source == "/dev/example"
    assert device.type == "block"
    assert repr(device) == (
        "<Device(type=block, id=123, block_size=4096, source=/dev/example)>"
    )


def test_from_path_marks_filesystem_without_source_as_virtual(monkeypatch):
    monkeypatch.setattr(
        "filefrag.device.os.stat", lambda path: SimpleNamespace(st_dev=123)
    )
    monkeypatch.setattr(
        "filefrag.device.os.statvfs", lambda path: SimpleNamespace(f_bsize=4096)
    )
    monkeypatch.setattr(Device, "_get_device_source", lambda path: None)

    assert Device.from_path("/data/file").type == "virtual"


def test_from_path_rejects_missing_path(monkeypatch):
    def missing(path):
        raise FileNotFoundError(path)

    monkeypatch.setattr("filefrag.device.os.stat", missing)

    with pytest.raises(ValueError, match="Path /missing does not exist"):
        Device.from_path("/missing")


def test_get_device_source_uses_deepest_mount(monkeypatch):
    mounts = """/dev/root / ext4 rw 0 0
/dev/data /mnt/data ext4 rw 0 0
"""
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: StringIO(mounts))

    assert Device._get_device_source("/mnt/data/file") == "/dev/data"


def test_get_device_source_returns_none_without_match(monkeypatch):
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: StringIO("/dev/data /mnt/data ext4 rw 0 0\n"),
    )

    assert Device._get_device_source("relative/path") is None
