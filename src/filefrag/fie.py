import ctypes
import errno
import fcntl


# Define ioctl-related functions and structures
def _IOC(dir, type, nr, size):
    IOC_NRBITS = 8
    IOC_TYPEBITS = 8
    IOC_SIZEBITS = 14
    IOC_DIRBITS = 2  # noqa

    IOC_NRSHIFT = 0
    IOC_TYPESHIFT = IOC_NRSHIFT + IOC_NRBITS
    IOC_SIZESHIFT = IOC_TYPESHIFT + IOC_TYPEBITS
    IOC_DIRSHIFT = IOC_SIZESHIFT + IOC_SIZEBITS

    return (
        (dir << IOC_DIRSHIFT)
        | (ord(type) << IOC_TYPESHIFT)
        | (nr << IOC_NRSHIFT)
        | (size << IOC_SIZESHIFT)
    )


IOC_NONE = 0
IOC_WRITE = 1
IOC_READ = 2


def _IOWR(type, nr, size):
    return _IOC(IOC_READ | IOC_WRITE, type, nr, size)


class fiemap_extent(ctypes.Structure):
    _fields_ = [
        ("fe_logical", ctypes.c_uint64),
        ("fe_physical", ctypes.c_uint64),
        ("fe_length", ctypes.c_uint64),
        ("fe_reserved64", ctypes.c_uint64 * 2),
        ("fe_flags", ctypes.c_uint32),
        ("fe_reserved", ctypes.c_uint32 * 3),
    ]


# Define the base fiemap structure without fm_extents
class fiemap_base(ctypes.Structure):
    _fields_ = [
        ("fm_start", ctypes.c_uint64),
        ("fm_length", ctypes.c_uint64),
        ("fm_flags", ctypes.c_uint32),
        ("fm_mapped_extents", ctypes.c_uint32),
        ("fm_extent_count", ctypes.c_uint32),
        ("fm_reserved", ctypes.c_uint32),
        # Do not include fm_extents here
    ]


def create_fiemap_struct(extent_count):
    class fiemap(ctypes.Structure):
        _fields_ = [
            ("fm_start", ctypes.c_uint64),
            ("fm_length", ctypes.c_uint64),
            ("fm_flags", ctypes.c_uint32),
            ("fm_mapped_extents", ctypes.c_uint32),
            ("fm_extent_count", ctypes.c_uint32),
            ("fm_reserved", ctypes.c_uint32),
            ("fm_extents", fiemap_extent * extent_count),
        ]

    return fiemap


def get_extents(fd):
    # This function retrieves all extents for a given file descriptor
    extents = []
    last_logical = 0
    # block_size = os.statvfs(fd).f_bsize

    while True:
        extent_count = 32  # Number of extents to retrieve per ioctl call
        fiemap_struct = create_fiemap_struct(extent_count)
        fm = fiemap_struct()
        fm.fm_start = last_logical
        fm.fm_length = ctypes.c_uint64(-1).value  # Equivalent to ULLONG_MAX
        fm.fm_flags = 0
        fm.fm_extent_count = extent_count

        fiemap_base_size = ctypes.sizeof(fiemap_base)
        FS_IOC_FIEMAP = _IOWR("f", 11, fiemap_base_size)

        # Perform the ioctl call
        try:
            fcntl.ioctl(fd, FS_IOC_FIEMAP, fm)
        except OSError as e:
            if e.errno == errno.ENOTTY:
                raise NotImplementedError(
                    "FIEMAP ioctl is not supported on this filesystem"
                )
            else:
                raise

        if fm.fm_mapped_extents == 0:
            break  # No more extents

        for i in range(fm.fm_mapped_extents):
            fe = fm.fm_extents[i]
            extent = {
                "logical": fe.fe_logical,
                "physical": fe.fe_physical,
                "length": fe.fe_length,
                "flags": fe.fe_flags,
            }
            extents.append(extent)
            last_logical = fe.fe_logical + fe.fe_length

        # Check if the last extent has the FIEMAP_EXTENT_LAST flag
        if fm.fm_extents[fm.fm_mapped_extents - 1].fe_flags & 0x1:  # FIEMAP_EXTENT_LAST
            break

    return extents
