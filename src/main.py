"""Command-line entry point for AI commit and PR draft generation."""

from __future__ import annotations

import argparse
import sys

from cli import build_parser, normalize_cli_args
from generator import run_generation


def run(args: argparse.Namespace) -> int:
    """Run the selected CLI command."""

    return run_generation(args)


def main(argv: list[str] | None = None) -> int:
    """Parse command-line arguments and run the CLI."""

    parser = build_parser()
    # Use terminal arguments by default, but allow tests to pass argv directly.
    raw_args = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(normalize_cli_args(raw_args))
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
