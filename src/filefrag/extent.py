from .device import Device


class Extent:
    """
    Represents a range of data inside a file.

    These have a logical position in the file, and a physical position on the
    device. The length of an extent can't be smaller than the block size of the
    filesystem holding it, so the length of all extents might be a bit longer
    than the file it represents.
    """

    FIEMAP_EXTENT_LAST = 0x00000001
    FIEMAP_EXTENT_UNKNOWN = 0x00000002
    FIEMAP_EXTENT_DELALLOC = 0x00000004
    FIEMAP_EXTENT_ENCODED = 0x00000008
    FIEMAP_EXTENT_DATA_ENCRYPTED = 0x00000080
    FIEMAP_EXTENT_NOT_ALIGNED = 0x00000100
    FIEMAP_EXTENT_DATA_INLINE = 0x00000200
    FIEMAP_EXTENT_DATA_TAIL = 0x00000400
    FIEMAP_EXTENT_UNWRITTEN = 0x00000800
    FIEMAP_EXTENT_MERGED = 0x00001000
    FIEMAP_EXTENT_SHARED = 0x00002000

    def __init__(
        self, logical: int, physical: int, length: int, flags: int, device: Device
    ):
        self.logical = logical
        self.physical = physical
        self.length = length
        self.flags = flags
        self.device = device  # Device object

    def __repr__(self):
        return (
            f"<Extent(logical={self.logical}, physical={self.physical}, "
            f"length={self.length}, flags=0x{self.flags:X})>"
        )

    @property
    def is_last(self) -> bool:
        """
        True if this is the last extent in the file map.
        """
        return bool(self.flags & self.FIEMAP_EXTENT_LAST)

    @property
    def is_unknown(self) -> bool:
        """
        If the extent is unknown, the physical location and other details
        returned are unreliable.
        """
        return bool(self.flags & self.FIEMAP_EXTENT_UNKNOWN)

    @property
    def is_delayed_allocation(self) -> bool:
        """
        True if the extent is in the process of being allocated, so the physical
        location will be set to 0 for the moment. Check again later
        """
        return bool(self.flags & self.FIEMAP_EXTENT_DELALLOC)

    @property
    def is_encoded(self) -> bool:
        """
        An extent may be encoded in some way, like being compressed or stored in
        a way where it'll need to be decoded before it can be read.
        """
        return bool(self.flags & self.FIEMAP_EXTENT_ENCODED)

    @property
    def is_encrypted(self) -> bool:
        """
        If so, the extent contains encrypted data, you'll need to decrypt it if
        you want the data inside.
        """
        return bool(self.flags & self.FIEMAP_EXTENT_DATA_ENCRYPTED)

    @property
    def is_not_aligned(self) -> bool:
        """
        True if the extent is misaligned with the filesystem's block or cluster
        sizes, if True then expect degraded performance.
        """
        return bool(self.flags & self.FIEMAP_EXTENT_NOT_ALIGNED)

    @property
    def is_inline(self) -> bool:
        """
        True if the extent is stored with the filesystem's metadata rather than
        in the data section.
        """
        return bool(self.flags & self.FIEMAP_EXTENT_DATA_INLINE)

    @property
    def is_tail_packed(self) -> bool:
        """
        True if the extent is the leftover bits at the end of a file that have
        been packed together with other extents to save space. If this is true,
        it's likely not_aligned too.
        """
        return bool(self.flags & self.FIEMAP_EXTENT_DATA_TAIL)

    @property
    def is_unwritten(self) -> bool:
        """
        True if the data was allocated, but not yet written to the device.
        """
        return bool(self.flags & self.FIEMAP_EXTENT_UNWRITTEN)

    @property
    def is_merged(self) -> bool:
        """
        If so, the extent is merged with other extents for reporting purposes.
        How this is done is filesystem-dependent.
        """
        return bool(self.flags & self.FIEMAP_EXTENT_MERGED)

    @property
    def is_shared(self) -> bool:
        """
        This extent might share a physical location with other extents. Seen in
        copy-on-write filesystems with deduplication or snapshots (btrfs, zfs)
        """
        return bool(self.flags & self.FIEMAP_EXTENT_SHARED)

    def __eq__(self, other):
        if not isinstance(other, Extent):
            return NotImplemented
        return (
            self.device == other.device
            and self.physical == other.physical
            and self.length == other.length
        )

    def __lt__(self, other):
        if not isinstance(other, Extent):
            return NotImplemented
        # Compare based on physical offset
        return self.physical < other.physical

    def __hash__(self):
        return hash((self.device, self.physical, self.length))

    def __format__(self, format_spec):
        fmt_options = set(format_spec.split(":"))
        use_hex = "x" in fmt_options
        verbose = "v" in fmt_options
        # json_output = 'j' in fmt_options  # Not implemented

        # Prepare the extent data
        logical = self.logical
        physical = self.physical
        length = self.length
        flags = self.flags

        # Format numbers in hexadecimal if requested
        if use_hex:
            logical_str = f"0x{logical:X}"
            physical_str = f"0x{physical:X}"
            length_str = f"0x{length:X}"
            flags_str = f"0x{flags:X}"
        else:
            logical_str = str(logical)
            physical_str = str(physical)
            length_str = str(length)
            flags_str = f"0x{flags:X}"

        # Interpret flags
        flag_descriptions = []
        if self.is_last:
            flag_descriptions.append("last")
        if self.is_unwritten:
            flag_descriptions.append("unwritten")
        if self.is_shared:
            flag_descriptions.append("shared")
        flags_readable = ",".join(flag_descriptions) if flag_descriptions else ""

        # Build output
        if verbose:
            output = (
                f"Extent(logical={logical_str}, physical={physical_str}, "
                f"length={length_str}, flags={flags_str} [{flags_readable}])"
            )
        else:
            output = f"Extent(logical={logical_str}, length={length_str})"

        return output

    def get_flag_descriptions(self):
        flags = []
        if self.is_last:
            flags.append("last")
        if self.is_unknown:
            flags.append("unknown")
        if self.is_delayed_allocation:
            flags.append("delayed")
        if self.is_encoded:
            flags.append("encoded")
        if self.is_encrypted:
            flags.append("encrypted")
        if self.is_not_aligned:
            flags.append("misaligned")
        if self.is_inline:
            flags.append("inline")
        if self.is_tail_packed:
            flags.append("tail")
        if self.is_unwritten:
            flags.append("unwritten")
        if self.is_merged:
            flags.append("merged")
        if self.is_shared:
            flags.append("shared")

        return flags
