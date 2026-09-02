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
