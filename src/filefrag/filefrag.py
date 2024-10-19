#!/usr/bin/env python3
import argparse
import sys

from .filemap import FileMap


def main():
    parser = argparse.ArgumentParser(description="Prints details about file fragments")
    parser.add_argument(
        "-x", "--hex", action="store_true", help="Output numbers in hexadecimal"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Display detailed extent information",
    )
    parser.add_argument(
        "-j", "--json", action="store_true", help="Output in JSON format"
    )
    parser.add_argument("files", nargs="+", help="Files to analyze")
    args = parser.parse_args()

    # Build format_spec based on options
    fmt_options = []
    if args.hex:
        fmt_options.append("x")
    if args.verbose:
        fmt_options.append("v")
    if args.json:
        fmt_options.append("j")

    format_spec = ":".join(fmt_options)

    # Process each file
    for filepath in args.files:
        try:
            filemap = FileMap(filepath)
            print(f"{filemap:{format_spec}}")
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
