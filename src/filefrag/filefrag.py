#!/usr/bin/env python3
import argparse
import sys

from .filemap import FileMap


def main() -> None:
    """
    Entrypoint for command line app.
    """
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

    # Buffer JSON so a later failure cannot leave a partial document on stdout.
    json_results = []
    for filepath in args.files:
        try:
            filemap = FileMap(filepath)
            output = format(filemap, format_spec)
            if args.json:
                json_results.append(output)
            else:
                print(output)
        except Exception as e:
            print(f"Error processing {filepath}: {e}", file=sys.stderr)
            sys.exit(1)

    if args.json:
        # Preserve the existing single-file object format.
        print(
            json_results[0]
            if len(json_results) == 1
            else "[\n" + ",\n".join(json_results) + "\n]"
        )


if __name__ == "__main__":
    main()
