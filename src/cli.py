"""Build and normalize command-line arguments for the CLI."""

from __future__ import annotations

import argparse


# Supported CLI command names.
COMMAND_NAMES = ("commit", "pr")

# Default model used for both commit and PR draft generation.
DEFAULT_MODEL = "gpt-5.4-mini"

# Default sampling temperature for stable draft output.
DEFAULT_TEMPERATURE = 0.2

# Default maximum generated token count passed as max_output_tokens.
DEFAULT_MAX_TOKENS = 800

# Command name for commit message draft generation.
COMMIT_COMMAND = "commit"

# Command name for pull request draft generation.
PR_COMMAND = "pr"


def normalize_cli_args(argv: list[str]) -> list[str]:
    """Normalize command names and long option names to lowercase."""

    normalized_args = []
    for index, arg in enumerate(argv):
        if index == 0 and arg.lower() in COMMAND_NAMES:
            normalized_args.append(arg.lower())
            continue

        if arg.startswith("--"):
            option_name, separator, option_value = arg.partition("=")
            normalized_args.append(option_name.lower() + separator + option_value)
            continue

        normalized_args.append(arg)

    return normalized_args


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Generate Korean commit messages and PR drafts from local Git changes.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    shared_options = argparse.ArgumentParser(add_help=False)
    shared_options.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model name.")
    shared_options.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help="Sampling temperature for generated text.",
    )
    shared_options.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Maximum output tokens for the Responses API.",
    )
    shared_options.add_argument(
        "--safe-mode",
        action="store_true",
        help="Mask emails, bearer tokens, and long token-like values before sending diffs.",
    )

    subparsers.add_parser(
        COMMIT_COMMAND,
        parents=[shared_options],
        help="Generate a commit message draft.",
    )
    subparsers.add_parser(
        PR_COMMAND,
        parents=[shared_options],
        help="Generate a pull request draft.",
    )

    return parser
