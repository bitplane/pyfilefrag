# filefrag

Python library to get FIE and command line tool

## Install

```bash
pip install filefrag
```

## Usage

```python
from filefrag import FileMap

mapping = FileMap('/usr/bin/bash')

print(mapping)
print(extents)
```

## Command line

```bash
pyfilefrag --help

pyfilefrag -j /dev/null
```
