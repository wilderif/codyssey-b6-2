"""Validate generated drafts and mask sensitive text before AI requests."""

from __future__ import annotations

from dataclasses import dataclass
import re


# Maximum allowed character count for a commit title.
MAX_COMMIT_TITLE_LENGTH = 72

# Maximum allowed character count for a PR title.
MAX_PR_TITLE_LENGTH = 80

# Required Markdown section headers for PR drafts.
REQUIRED_PR_SECTIONS = ("Why", "What", "How to Test")

# Matches common email addresses that may appear in diffs.
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Matches Authorization header values that use the Bearer scheme.
BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")

# Matches OpenAI-style keys and other long token-like values.
LONG_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])(?:sk-[A-Za-z0-9_-]{20,}|[A-Za-z0-9][A-Za-z0-9_-]{31,})(?![A-Za-z0-9_-])"
)

# Matches Markdown bullet lines with visible content.
BULLET_PATTERN = re.compile(r"^\s*[-*]\s+\S+")


@dataclass
class ValidationResult:
    """Store validation errors for generated draft text."""

    errors: list[str]

    @property
    def is_valid(self) -> bool:
        """Return whether no validation errors were found."""

        return not self.errors

    def message(self) -> str:
        """Return a readable validation summary."""

        if self.is_valid:
            return "검증을 통과했습니다."
        return "\n".join(f"- {error}" for error in self.errors)


def split_title_and_body(text: str) -> tuple[str, str]:
    """Split generated text into the first non-empty title line and body."""

    lines = text.strip().splitlines()
    for index, line in enumerate(lines):
        title = line.strip()
        if title:
            body = "\n".join(lines[index + 1 :]).strip()
            return title, body
    return "", ""


def validate_commit_message(text: str) -> ValidationResult:
    """Validate commit title length and one-line format."""

    errors = []
    title, remaining_text = split_title_and_body(text)

    if not title:
        errors.append("커밋 제목이 필요합니다.")
    elif len(title) > MAX_COMMIT_TITLE_LENGTH:
        errors.append(f"커밋 제목은 최대 {MAX_COMMIT_TITLE_LENGTH}자여야 합니다.")

    if remaining_text:
        errors.append("커밋 메시지는 한 줄 제목만 포함해야 합니다.")

    return ValidationResult(errors)


def normalize_section_header(line: str) -> str | None:
    """Return the PR section name when a line is a required section header."""

    stripped = line.strip().rstrip(":").strip()
    stripped = stripped.lstrip("#").strip()
    if stripped in REQUIRED_PR_SECTIONS:
        return stripped
    return None


def split_pr_sections(body: str) -> dict[str, list[str]]:
    """Split a PR body into required section content lines."""

    sections: dict[str, list[str]] = {}
    current_section = None

    for line in body.splitlines():
        section_name = normalize_section_header(line)
        if section_name:
            current_section = section_name
            sections.setdefault(current_section, [])
            continue

        if current_section:
            sections[current_section].append(line)

    return sections


def section_has_bullet(lines: list[str]) -> bool:
    """Return whether section lines contain at least one bullet."""

    return any(BULLET_PATTERN.match(line) for line in lines)


def validate_pr_draft(text: str) -> ValidationResult:
    """Validate PR title length, required sections, and section bullets."""

    errors = []
    title, body = split_title_and_body(text)

    if not title:
        errors.append("PR 제목이 필요합니다.")
    elif len(title) > MAX_PR_TITLE_LENGTH:
        errors.append(f"PR 제목은 최대 {MAX_PR_TITLE_LENGTH}자여야 합니다.")

    sections = split_pr_sections(body)
    for section_name in REQUIRED_PR_SECTIONS:
        if section_name not in sections:
            errors.append(f"PR 본문에 {section_name} 섹션이 필요합니다.")
        elif not section_has_bullet(sections[section_name]):
            errors.append(f"PR 본문의 {section_name} 섹션에는 최소 1개 불릿이 필요합니다.")

    return ValidationResult(errors)


def mask_sensitive_text(text: str) -> str:
    """Mask emails, bearer tokens, and long API-key-like tokens."""

    masked = EMAIL_PATTERN.sub("[EMAIL_MASKED]", text)
    masked = BEARER_TOKEN_PATTERN.sub("Bearer [TOKEN_MASKED]", masked)
    return LONG_TOKEN_PATTERN.sub("[TOKEN_MASKED]", masked)
