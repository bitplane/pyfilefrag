class Extent:
    # FIEMAP extent flag constants
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

    def __init__(self, logical, physical, length, flags, device):
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

    # Properties for flags
    @property
    def is_last(self):
        return bool(self.flags & self.FIEMAP_EXTENT_LAST)

    @property
    def is_unknown(self):
        return bool(self.flags & self.FIEMAP_EXTENT_UNKNOWN)

    @property
    def is_unwritten(self):
        return bool(self.flags & self.FIEMAP_EXTENT_UNWRITTEN)

    @property
    def is_shared(self):
        return bool(self.flags & self.FIEMAP_EXTENT_SHARED)

    # Add more properties as needed for other flags

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
        flag_descriptions = []
        if self.is_last:
            flag_descriptions.append("last")
        if self.is_unwritten:
            flag_descriptions.append("unwritten")
        if self.is_shared:
            flag_descriptions.append("shared")
        # Add other flag checks as needed
        return flag_descriptions
