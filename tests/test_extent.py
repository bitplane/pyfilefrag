import pytest

from filefrag.device import Device
from filefrag.extent import Extent


def make_extent(*, logical=16, physical=32, length=48, flags=0, device_id=123):
    device = Device()
    device.id = device_id
    return Extent(logical, physical, length, flags, device)


@pytest.mark.parametrize(
    ("flag", "property_name", "description"),
    [
        (Extent.FIEMAP_EXTENT_LAST, "is_last", "last"),
        (Extent.FIEMAP_EXTENT_UNKNOWN, "is_unknown", "unknown"),
        (
            Extent.FIEMAP_EXTENT_DELALLOC,
            "is_delayed_allocation",
            "delayed",
        ),
        (Extent.FIEMAP_EXTENT_ENCODED, "is_encoded", "encoded"),
        (Extent.FIEMAP_EXTENT_DATA_ENCRYPTED, "is_encrypted", "encrypted"),
        (Extent.FIEMAP_EXTENT_NOT_ALIGNED, "is_not_aligned", "misaligned"),
        (Extent.FIEMAP_EXTENT_DATA_INLINE, "is_inline", "inline"),
        (Extent.FIEMAP_EXTENT_DATA_TAIL, "is_tail_packed", "tail"),
        (Extent.FIEMAP_EXTENT_UNWRITTEN, "is_unwritten", "unwritten"),
        (Extent.FIEMAP_EXTENT_MERGED, "is_merged", "merged"),
        (Extent.FIEMAP_EXTENT_SHARED, "is_shared", "shared"),
    ],
)
def test_flag_properties_and_descriptions(flag, property_name, description):
    extent = make_extent(flags=flag)

    assert getattr(extent, property_name) is True
    assert extent.get_flag_descriptions() == [description]


def test_extent_equality_and_ordering():
    extent = make_extent()
    equivalent = make_extent(logical=999, flags=Extent.FIEMAP_EXTENT_LAST)

    assert extent == equivalent
    assert hash(extent) == hash(equivalent)
    assert extent != make_extent(physical=33)
    assert extent != make_extent(length=49)
    assert extent != make_extent(device_id=456)
    assert extent < make_extent(physical=33)
    assert extent.__eq__(object()) is NotImplemented
    assert extent.__lt__(object()) is NotImplemented


def test_extent_representations():
    flags = (
        Extent.FIEMAP_EXTENT_LAST
        | Extent.FIEMAP_EXTENT_UNWRITTEN
        | Extent.FIEMAP_EXTENT_SHARED
    )
    extent = make_extent(flags=flags)

    assert repr(extent) == (
        "<Extent(logical=16, physical=32, length=48, flags=0x2801)>"
    )
    assert format(extent, "") == "Extent(logical=16, length=48)"
    assert format(extent, "v") == (
        "Extent(logical=16, physical=32, length=48, "
        "flags=0x2801 [last,unwritten,shared])"
    )
    assert format(extent, "x:v") == (
        "Extent(logical=0x10, physical=0x20, length=0x30, "
        "flags=0x2801 [last,unwritten,shared])"
    )
