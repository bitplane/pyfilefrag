import json
import os

from . import fie
from .device import Device
from .extent import Extent


class FileMap:
    """
    Contains a mapping of a file to physical locations on the storage device.
    """

    def __init__(self, path: str):
        self.path = path
        self.device = None
        self.inode = None
        self.mtime = None
        self.extents = []
        self.update()

    def update(self):
        """
        (re)read the data, updating the internal state.
        """
        try:
            file_stats = os.stat(self.path)
        except FileNotFoundError as ex:
            raise ValueError(f"Path {self.path} does not exist.") from ex

        # update path
        self.path = os.path.abspath(self.path)

        self.device = Device.from_path(self.path)
        self.inode = file_stats.st_ino
        self.mtime = file_stats.st_mtime

        # Get extents
        fd = os.open(self.path, os.O_RDONLY)
        try:
            raw_extents = fie.get_extents(fd)
        finally:
            os.close(fd)

        # Update extents list
        self.extents = []
        for raw_extent in raw_extents:
            extent = Extent(
                logical=raw_extent["logical"],
                physical=raw_extent["physical"],
                length=raw_extent["length"],
                flags=raw_extent["flags"],
                device=self.device,
            )
            self.extents.append(extent)

    def check_stale(self) -> bool:
        """
        Returns true is the data the path points to is different to when it
        was loaded.
        """
        try:
            file_stats = os.stat(self.path)
        except FileNotFoundError:
            return True

        if self.path != os.path.abspath(self.path):
            return True

        if (
            self.device.id != file_stats.st_dev
            or self.inode != file_stats.st_ino
            or self.mtime != file_stats.st_mtime
        ):

            return True

        return False

    def __eq__(self, other):
        if not isinstance(other, FileMap):
            return NotImplemented
        return (
            self.device == other.device
            and self.inode == other.inode
            and self.mtime == other.mtime
        )

    def __iter__(self):
        """
        Iterates over the extents in the file.
        """
        return iter(self.extents)

    def __repr__(self):
        return f"<FileMap(path={self.path}, extents={len(self.extents)})>"

    def __format__(self, format_spec):
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
            output = []
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
