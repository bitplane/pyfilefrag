from __future__ import annotations

import json
import os
from collections.abc import Iterator

from . import fie
from .device import Device
from .extent import Extent


class FileMap:
    """
    Contains a mapping of a file to physical locations on the storage device.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path: str = os.fspath(path)
        self.device: Device
        self.inode: int
        self.mtime: float
        self._stat_signature: tuple[int, int, int]
        self.extents: list[Extent] = []
        self.update()

    def update(self) -> None:
        """
        (re)read the data, updating the internal state.
        """
        # abspath() collapses '..' before the kernel can resolve symlinks.
        path = self.path
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)

        try:
            fd = os.open(path, os.O_RDONLY)
        except FileNotFoundError as ex:
            raise ValueError(f"Path {self.path} does not exist.") from ex

        try:
            file_stats = os.fstat(fd)
            device = Device.from_fd(fd, path)
            raw_extents = fie.get_extents(fd)
        finally:
            os.close(fd)

        extents = []
        for raw_extent in raw_extents:
            extent = Extent(
                logical=raw_extent["logical"],
                physical=raw_extent["physical"],
                length=raw_extent["length"],
                flags=raw_extent["flags"],
                device=device,
            )
            extents.append(extent)

        # Commit the refreshed state only after every operation succeeds.
        self.path = path
        self.device = device
        self.inode = file_stats.st_ino
        self.mtime = file_stats.st_mtime
        self._stat_signature = (
            file_stats.st_mtime_ns,
            file_stats.st_ctime_ns,
            file_stats.st_size,
        )
        self.extents = extents

    def check_stale(self) -> bool:
        """
        Re-read the path and compare metadata and extent records.

        Missing paths and unresolved physical locations are stale. This performs
        I/O and may raise filesystem errors. A false result is only a snapshot:
        concurrent writes or filesystem maintenance can invalidate it later.
        """
        if any(e.is_unknown or e.is_delayed_allocation for e in self.extents):
            return True
        try:
            current = FileMap(self.path)
        except ValueError as ex:
            if isinstance(ex.__cause__, FileNotFoundError):
                return True
            raise
        return self != current

    def _extent_state(self) -> list[tuple[int, int, int, int]]:
        # Extent equality deliberately ignores logical offsets and most flags.
        return [(e.logical, e.physical, e.length, e.flags) for e in self.extents]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileMap):
            return NotImplemented
        return (
            self.device == other.device
            and self.inode == other.inode
            and self.mtime == other.mtime
            and self._stat_signature == other._stat_signature
            and self._extent_state() == other._extent_state()
        )

    def __iter__(self) -> Iterator[Extent]:
        """
        Iterates over the extents in the file.
        """
        return iter(self.extents)

    def __repr__(self) -> str:
        return f"<FileMap(path={self.path}, extents={len(self.extents)})>"

    def __format__(self, format_spec: str) -> str:
        fmt_options = set(format_spec.split(":"))
        verbose = "v" in fmt_options
        json_output = "j" in fmt_options

        if json_output:
            # Build JSON representation
            extents_data = [
                {
                    "logical": extent.logical,
                    "physical": extent.physical,
                    "length": extent.length,
                    "flags": extent.flags,
                    "flags_readable": extent.get_flag_descriptions(),
                }
                for extent in self.extents
            ]

            data = {
                "path": self.path,
                "device": {
                    "type": self.device.type,
                    "id": self.device.id,
                    "block_size": self.device.block_size,
                    "source": self.device.source,
                },
                "inode": self.inode,
                "mtime": self.mtime,
                "extents": extents_data,
            }
            return json.dumps(data, indent=2)

        else:
            # Build text output
            output: list[str] = []
            output.append(f"File: {self.path}")
            output.append(f"Device: {self.device}")
            output.append(f"Inode: {self.inode}")
            output.append(f"Modification Time: {self.mtime}")
            output.append(f"Number of Extents: {len(self.extents)}")

            if verbose:
                for idx, extent in enumerate(self.extents):
                    # Remove 'j' option when formatting extents
                    extent_format_spec = ":".join(fmt_options - {"j"})
                    extent_str = format(extent, extent_format_spec)
                    output.append(f"  {idx}: {extent_str}")
            return "\n".join(output)
