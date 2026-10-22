import errno

import pytest

from filefrag.fie import get_extents


@pytest.mark.parametrize("error_number", [errno.ENOTTY, errno.EOPNOTSUPP])
def test_get_extents_translates_unsupported_ioctl_errors(monkeypatch, error_number):
    def unsupported(*args):
        raise OSError(error_number, "FIEMAP unsupported")

    monkeypatch.setattr("filefrag.fie.fcntl.ioctl", unsupported)

    with pytest.raises(NotImplementedError, match="FIEMAP ioctl is not supported"):
        get_extents(42)


def test_get_extents_preserves_other_ioctl_errors(monkeypatch):
    def denied(*args):
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr("filefrag.fie.fcntl.ioctl", denied)

    with pytest.raises(OSError) as exc_info:
        get_extents(42)

    assert exc_info.value.errno == errno.EACCES


@pytest.mark.parametrize("count", [0, 1, 32, 33, 70])
@pytest.mark.parametrize("mark_last", [False, True])
def test_successful_fiemap_pagination(monkeypatch, count, mark_last):
    expected = [
        dict(
            logical=i * 8192,
            physical=(i + 100) * 4096,
            length=4096,
            flags=int(mark_last and i == count - 1),
        )
        for i in range(count)
    ]
    starts = []

    def ioctl(fd, command, fm):
        assert fd == 42
        assert fm.fm_flags == 0
        assert fm.fm_extent_count == 32
        starts.append(fm.fm_start)
        batch = [e for e in expected if e["logical"] >= fm.fm_start][:32]
        fm.fm_mapped_extents = len(batch)
        for i, item in enumerate(batch):
            for name, value in item.items():
                setattr(fm.fm_extents[i], "fe_" + name, value)

    monkeypatch.setattr("filefrag.fie.fcntl.ioctl", ioctl)
    assert get_extents(42) == expected
    assert all(b > a for a, b in zip(starts, starts[1:]))
    batches = (count + 31) // 32
    assert len(starts) == (max(1, batches) if mark_last else batches + 1)
