from dataclasses import FrozenInstanceError, replace

import pytest

from filefrag.device import Device
from filefrag.extent import Extent


def make_device(device_id, source=None):
    return Device(id=device_id, source=source)


def test_equal_devices_have_equal_hashes():
    first = make_device(123, source="/dev/first")
    second = make_device(123, source="/dev/second")

    assert first == second
    assert hash(first) == hash(second)


def test_extent_is_hashable():
    extent = Extent(
        logical=0,
        physical=4096,
        length=4096,
        flags=Extent.FIEMAP_EXTENT_LAST,
        device=make_device(123),
    )

    assert hash(extent) == hash((extent.device, extent.physical, extent.length))


@pytest.mark.parametrize(
    "field,value",
    [
        ("physical", 8192),
        ("length", 8192),
        ("flags", 2),
        ("device", Device(id=456)),
        ("logical", 8192),
    ],
)
def test_extent_keys_cannot_be_mutated(field, value):
    extent = Extent(0, 4096, 4096, 1, Device(id=123))
    lookup = {extent: "saved"}
    with pytest.raises(FrozenInstanceError):
        setattr(extent, field, value)
    assert lookup[extent] == "saved"
    with pytest.raises(FrozenInstanceError):
        del extent.physical
    assert lookup[extent] == "saved"


def test_device_identity_cannot_invalidate_nested_extent_keys():
    device = Device(id=123)
    extent = Extent(0, 4096, 4096, 1, device)
    lookup = {device: "device", extent: "extent"}
    with pytest.raises(FrozenInstanceError):
        device.id = 456
    assert lookup[device] == "device"
    assert lookup[extent] == "extent"
    assert replace(device, id=456) != device
