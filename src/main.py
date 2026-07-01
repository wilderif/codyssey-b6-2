"""Command-line entry point for AI commit and PR draft generation."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import sys

from ai_client import AiClientError, request_generated_text
from git_utils import GitChangeContext, collect_git_context
from prompts import build_commit_prompt, build_correction_prompt, build_pr_prompt
from validators import ValidationResult, mask_sensitive_text, validate_commit_message, validate_pr_draft


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

# Divider line used to make terminal output copy-friendly.
OUTPUT_DIVIDER = "-" * 48


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


def count_non_empty_lines(text: str) -> int:
    """Return the number of non-empty lines in text."""

    return sum(1 for line in text.splitlines() if line.strip())


def prepare_prompt_context(git_context: GitChangeContext, safe_mode: bool) -> str:
    """Return prompt context, applying masking when safe mode is enabled."""

    prompt_context = git_context.to_prompt_context()
    if safe_mode:
        print("[INFO] safe-mode 활성화: 민감정보 패턴을 마스킹했습니다.")
        return mask_sensitive_text(prompt_context)
    return prompt_context


def get_prompt_builder(command: str) -> Callable[[str], str]:
    """Return the prompt builder for a CLI command."""

    if command == COMMIT_COMMAND:
        return build_commit_prompt
    return build_pr_prompt


def get_validator(command: str) -> Callable[[str], ValidationResult]:
    """Return the output validator for a CLI command."""

    if command == COMMIT_COMMAND:
        return validate_commit_message
    return validate_pr_draft


def get_output_label(command: str) -> str:
    """Return the terminal label for generated draft output."""

    if command == COMMIT_COMMAND:
        return "Commit Message Draft"
    return "Pull Request Draft"


def generate_validated_draft(args: argparse.Namespace, prompt: str) -> tuple[str | None, int, ValidationResult]:
    """Generate a draft and retry once when validation fails."""

    validator = get_validator(args.command)
    request_count = 0

    print("[INFO] AI API 요청 중...")
    request_count += 1
    generated_text = request_generated_text(
        prompt=prompt,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    ).strip()

    validation_result = validator(generated_text)
    if validation_result.is_valid:
        return generated_text, request_count, validation_result

    print("[INFO] 생성 결과가 형식 검증에 실패하여 1회 재요청합니다.")
    correction_prompt = build_correction_prompt(
        original_prompt=prompt,
        invalid_output=generated_text,
        validation_errors=validation_result.errors,
    )

    print("[INFO] AI API 재요청 중...")
    request_count += 1
    corrected_text = request_generated_text(
        prompt=correction_prompt,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    ).strip()

    retry_validation_result = validator(corrected_text)
    if retry_validation_result.is_valid:
        return corrected_text, request_count, retry_validation_result

    return None, request_count, retry_validation_result


def print_draft(command: str, draft_text: str, request_count: int) -> None:
    """Print the final generated draft for user review."""

    print(f"[DONE] {get_output_label(command)} 생성 완료")
    print(f"[INFO] AI API 요청 시도 횟수: {request_count}")
    print()
    print(OUTPUT_DIVIDER)
    print(f"{get_output_label(command)} - 검토용 초안")
    print(OUTPUT_DIVIDER)
    print(draft_text)
    print(OUTPUT_DIVIDER)


def print_validation_failure(validation_result: ValidationResult, request_count: int) -> None:
    """Print validation failure details after the retry is exhausted."""

    print("[ERROR] 생성 결과가 형식 검증을 통과하지 못했습니다.")
    print(validation_result.message())
    print(f"[INFO] AI API 요청 시도 횟수: {request_count}")


def run(args: argparse.Namespace) -> int:
    """Run the selected CLI command."""

    try:
        git_context = collect_git_context()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return 1

    if not git_context.has_changes:
        print("[INFO] 변경 사항이 없습니다.")
        return 0

    print(f"[INFO] Git status 수집 완료: {count_non_empty_lines(git_context.status)}개 항목 변경 감지")
    print(f"[INFO] Git diff 수집 완료: {count_non_empty_lines(git_context.combined_diff())}줄")

    prompt_context = prepare_prompt_context(git_context, args.safe_mode)
    prompt = get_prompt_builder(args.command)(prompt_context)

    try:
        draft_text, request_count, validation_result = generate_validated_draft(args, prompt)
    except AiClientError as exc:
        print(f"[ERROR] {exc}")
        return 1

    if draft_text is None:
        print_validation_failure(validation_result, request_count)
        return 1

    print_draft(args.command, draft_text, request_count)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse command-line arguments and run the CLI."""

    parser = build_parser()
    raw_args = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(normalize_cli_args(raw_args))
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
