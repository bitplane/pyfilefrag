from __future__ import annotations

import os
import re
import stat


class Device:
    """
    Represents a device; the backing store of a filesystem.
    """

    def __init__(self) -> None:
        self.type: str | None = None
        self.id: int | None = None
        self.block_size: int | None = None
        self.source: str | None = None

    @classmethod
    def from_path(cls, path: str) -> Device:
        try:
            fd = os.open(path, os.O_RDONLY)
        except FileNotFoundError as ex:
            raise ValueError(f"Path {path} does not exist.") from ex

        try:
            return cls.from_fd(fd, path)
        finally:
            os.close(fd)

    @classmethod
    def from_fd(cls, fd: int, path: str) -> Device:
        instance = cls()
        instance.id = os.fstat(fd).st_dev
        instance.block_size = os.fstatvfs(fd).f_bsize
        instance.source = cls._get_device_source(fd)
        instance.type = cls._get_device_type(instance.id, instance.source)
        return instance

    @staticmethod
    def _get_device_type(device_id: int, source: str | None) -> str | None:
        # sysfs also works when a container cannot see the source device node.
        if os.path.exists(
            f"/sys/dev/block/{os.major(device_id)}:{os.minor(device_id)}"
        ):
            return "block"
        if source is None:
            return None
        if os.path.isabs(source):
            try:
                mode = os.stat(source).st_mode
            except OSError:
                # An inaccessible source is not evidence of a virtual device.
                return None
            return "block" if stat.S_ISBLK(mode) else "virtual"
        return "virtual"

    @staticmethod
    def _get_device_source(fd: int) -> str | None:
        # Match the descriptor's mount, even after a rename or through a symlink.
        mount_id = None
        with open(f"/proc/self/fdinfo/{fd}", "r") as fdinfo:
            for line in fdinfo:
                if line.startswith("mnt_id:"):
                    mount_id = line.split()[1]
                    break
        if mount_id is None:
            return None

        with open("/proc/self/mountinfo", "r") as mounts:
            for line in mounts:
                parts = line.split()
                if parts[0] != mount_id:
                    continue
                separator = parts.index("-")
                source = parts[separator + 2]
                return re.sub(
                    r"\\([0-7]{3})",
                    lambda match: chr(int(match.group(1), 8)),
                    source,
                )
        return None

    def __repr__(self) -> str:
        return (
            f"<Device(type={self.type}, id={self.id}, block_size={self.block_size}, "
            f"source={self.source})>"
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Device) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
