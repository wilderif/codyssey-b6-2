"""Run Git collection, AI generation, validation, and terminal output."""

from __future__ import annotations

import argparse

from git_draft.ai_client import AiClientError, request_generated_text
from git_draft.cli import COMMIT_COMMAND
from git_draft.git_utils import GitChangeContext, collect_git_context
from git_draft.prompts import build_commit_prompt, build_correction_prompt, build_pr_prompt
from git_draft.validators import (
    ValidationResult,
    mask_sensitive_text,
    validate_commit_message,
    validate_pr_draft,
)


# Divider line used to make terminal output copy-friendly.
OUTPUT_DIVIDER = "-" * 48


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


def build_prompt(command: str, prompt_context: str) -> str:
    """Build the correct prompt for the selected command."""

    if command == COMMIT_COMMAND:
        return build_commit_prompt(prompt_context)
    return build_pr_prompt(prompt_context)


def validate_draft(command: str, draft_text: str) -> ValidationResult:
    """Validate generated text for the selected command."""

    if command == COMMIT_COMMAND:
        return validate_commit_message(draft_text)
    return validate_pr_draft(draft_text)


def generate_validated_draft(args: argparse.Namespace, prompt: str) -> tuple[str | None, int, ValidationResult]:
    """Generate a draft and retry once when validation fails."""

    request_count = 0

    print("[INFO] AI API 요청 중...")
    request_count += 1
    generated_text = request_generated_text(
        prompt=prompt,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    ).strip()

    validation_result = validate_draft(args.command, generated_text)
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

    retry_validation_result = validate_draft(args.command, corrected_text)
    if retry_validation_result.is_valid:
        return corrected_text, request_count, retry_validation_result

    return None, request_count, retry_validation_result


def get_output_label(command: str) -> str:
    """Return the terminal label for generated draft output."""

    if command == COMMIT_COMMAND:
        return "Commit Message Draft"
    return "Pull Request Draft"


def print_draft(command: str, draft_text: str, request_count: int) -> None:
    """Print the final generated draft for user review."""

    label = get_output_label(command)
    print(f"[DONE] {label} 생성 완료")
    print(f"[INFO] AI API 요청 시도 횟수: {request_count}")
    print()
    print(OUTPUT_DIVIDER)
    print(f"{label} - 검토용 초안")
    print(OUTPUT_DIVIDER)
    print(draft_text)
    print(OUTPUT_DIVIDER)


def print_validation_failure(validation_result: ValidationResult, request_count: int) -> None:
    """Print validation failure details after the retry is exhausted."""

    print("[ERROR] 생성 결과가 형식 검증을 통과하지 못했습니다.")
    print(validation_result.message())
    print(f"[INFO] AI API 요청 시도 횟수: {request_count}")


def run_generation(args: argparse.Namespace) -> int:
    """Run the Git-to-AI draft generation flow."""

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
    prompt = build_prompt(args.command, prompt_context)

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
