import os


class Device:
    """
    Represents a device; the backing store of a filesystem.
    """

    def __init__(self):
        self.type = None
        self.id = None
        self.block_size = None
        self.source = None

    @classmethod
    def from_path(cls, path: str) -> "Device":
        instance = cls()

        try:
            # Get file system stats
            file_stats = os.stat(path)
            fs_stats = os.statvfs(path)

            # Populating fields
            instance.id = file_stats.st_dev
            instance.block_size = fs_stats.f_bsize

            # Determine device source using /proc/mounts
            instance.source = cls._get_device_source(path)

            # Determine device type
            instance.type = "block" if instance.source else "virtual"

        except FileNotFoundError as ex:
            raise ValueError(f"Path {path} does not exist.") from ex

        return instance

    @staticmethod
    def _get_device_source(path):
        # We'll store matching mount points and their corresponding devices
        matching_mounts = []

        # Read /proc/mounts to get all mounted filesystems
        with open("/proc/mounts", "r") as mounts_file:
            for line in mounts_file:
                parts = line.split()
                source_device = parts[0]  # The source device (e.g., /dev/sda1)
                mount_point = parts[1]  # The mount point (e.g., /)

                # Check if the given path starts with this mount point
                if path.startswith(mount_point):
                    matching_mounts.append((mount_point, source_device))

        if not matching_mounts:
            return None

        # Sort by the length of the mount point (longest first to ensure deepest match)
        matching_mounts.sort(key=lambda x: len(x[0]), reverse=True)

        # Return the source device for the deepest mount point
        return matching_mounts[0][1]

    def __repr__(self):
        return (
            f"<Device(type={self.type}, id={self.id}, block_size={self.block_size}, "
            f"source={self.source})>"
        )

    def __eq__(self, other):
        return isinstance(other, Device) and self.id == other.id
