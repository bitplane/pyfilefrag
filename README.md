# filefrag

Python library to get FIE and command line tool

## Install

See [the video](https://asciinema.org/a/681791) for a demo including installing
from source, but you can install with pip:

```sh
pip install filefrag
```

## Usage

Run `pyfilefrag` on the command line. See `--help` for details. It has
`--verbose`, and `--json` outputs for your parsing pleasure.

To use the library, just call filefrag.FileMap('/path/whatever') to build a map
of the extents in the file using ioctl’s interface. Then you can poke about in
the guts of a file:

* ⛓️‍💥 inspect fragmentation
* 🔍 find out where data is on your physical drive
* 🟰 compare extents between paths
* 📔 use them as dict keys
* 🕳️ check files for holes, like before and after hole punching
* ✅ verify your deduplication strategy, write your own stats tool
* 💩 dump file layouts to json (`print(f"{filemap:j}"`)
* ⚠️ break your disk because you believed the outputs of this alpha release!

Comes with a Device class to do comparisons, so it ought to work with fragments
in files on different mountpoints, bind mounts and so on (unfortunately not
snap’s FUSE mounts; they’re far too abstract and piped in via a socket)

## Example

```python
from filefrag import FileMap

mapping = FileMap('/usr/bin/bash')

print(mapping)
print(extents)
```

## License

Licensed under the WTFPL with one additional clause:

1. Don't blame me.

Do whatever the fuck you want, just don't blame me.

## Contributing

Not that this thing will ever be big enough to need a code of conduct, but it's
a good excuse to pimp out my
[common fucking sense code of conduct](https://github.com/bitplane/CFS-CoC/blob/main/code_of_conduct.md).
