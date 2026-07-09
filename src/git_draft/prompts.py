"""Build prompts for commit messages, PR drafts, and retry corrections."""

from __future__ import annotations


# Allowed conventional commit prefixes for generated commit and PR titles.
CONVENTIONAL_TYPES = ("feat", "fix", "docs", "refactor", "test", "chore")

# Shared formatting rules for every generated draft.
COMMON_OUTPUT_RULES = """\
- Keep conventional commit prefixes such as feat:, fix:, docs:, refactor:, test:, or chore: in English.
- Do not wrap the answer in a code block.
- Do not include explanations before or after the draft.
- Generate draft text only; do not run or suggest git commit, git push, or GitHub PR creation commands.
"""

# Required output rules for commit message generation.
COMMIT_OUTPUT_RULES = """\
Output format:
<one-line commit title>

Rules:
- The commit title must start with one conventional commit prefix.
- Choose the prefix from: {types}.
- Prefer a title within 50 characters; never exceed 72 characters.
- Return only the one-line commit title.
""".format(types=", ".join(f"{commit_type}:" for commit_type in CONVENTIONAL_TYPES))

# Required output rules for pull request draft generation.
PR_OUTPUT_RULES = """\
Output format:
<one-line PR title>

## Why
- <bullet>

## What
- <bullet>

## How to Test
- <bullet>

Rules:
- The PR title must be one line and no longer than 80 characters.
- The PR title should start with a conventional commit prefix when it naturally fits.
- Keep the section headers exactly as: Why, What, How to Test.
- Each section must include at least one Markdown bullet.
- Keep the body concise and useful for reviewer context.
"""

# Required output rules for retry prompts after validation failure.
CORRECTION_OUTPUT_RULES = """\
Fix the previous draft so it satisfies every validation rule.
Return only the corrected draft.
Keep the original meaning and Git change context.
Do not add explanations, apologies, or code fences.
"""


def build_commit_prompt(git_context: str) -> str:
    """Build a prompt for generating a commit message draft."""

    return "\n\n".join(
        [
            "You are writing a commit message draft from local Git changes.",
            COMMON_OUTPUT_RULES,
            COMMIT_OUTPUT_RULES,
            "Git change context:",
            git_context.strip(),
        ]
    )


def build_pr_prompt(git_context: str) -> str:
    """Build a prompt for generating a pull request draft."""

    return "\n\n".join(
        [
            "You are writing a pull request title and body draft from local Git changes.",
            COMMON_OUTPUT_RULES,
            PR_OUTPUT_RULES,
            "Git change context:",
            git_context.strip(),
        ]
    )


def build_correction_prompt(
    original_prompt: str,
    invalid_output: str,
    validation_errors: list[str],
) -> str:
    """Build a retry prompt that asks the model to fix validation errors."""

    error_text = "\n".join(f"- {error}" for error in validation_errors)
    return "\n\n".join(
        [
            CORRECTION_OUTPUT_RULES,
            "Validation errors:",
            error_text,
            "Original generation prompt:",
            original_prompt.strip(),
            "Previous invalid draft:",
            invalid_output.strip(),
        ]
    )
