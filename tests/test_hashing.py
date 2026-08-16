from filefrag.device import Device
from filefrag.extent import Extent


def make_device(device_id, source=None):
    device = Device()
    device.id = device_id
    device.source = source
    return device


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
