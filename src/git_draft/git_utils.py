"""Collect local Git status and diff context for AI prompts."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass
class GitChangeContext:
    """Store Git status and staged/unstaged diff text."""

    status: str
    staged_diff: str
    unstaged_diff: str

    @property
    def has_changes(self) -> bool:
        """Return whether Git status reports any local changes."""

        return bool(self.status.strip())

    def combined_diff(self) -> str:
        """Return staged and unstaged diffs as one labeled text block."""

        sections = []

        if self.staged_diff.strip():
            sections.append("## Staged diff\n" + self.staged_diff.strip())

        if self.unstaged_diff.strip():
            sections.append("## Unstaged diff\n" + self.unstaged_diff.strip())

        return "\n\n".join(sections)

    def to_prompt_context(self) -> str:
        """Return Git status and diff text formatted for an AI prompt."""

        diff_text = self.combined_diff()
        if not diff_text:
            diff_text = "변경 파일은 있지만 git diff로 표시되는 변경 내용은 없습니다."

        return "\n\n".join(
            [
                "## Git status",
                self.status.strip(),
                diff_text,
            ]
        )


def run_git_command(args: list[str]) -> str:
    """Run a Git command and return stdout text."""

    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("git 명령을 찾을 수 없습니다.") from exc
    except subprocess.CalledProcessError as exc:
        error_message = (exc.stderr or exc.stdout or "").strip()
        if not error_message:
            error_message = "알 수 없는 오류"
        raise RuntimeError(f"git {' '.join(args)} 실행 실패: {error_message}") from exc

    return result.stdout


def get_git_status() -> str:
    """Return short Git status output."""

    return run_git_command(["status", "--short"])


def get_staged_diff() -> str:
    """Return the diff for staged changes."""

    return run_git_command(["diff", "--cached"])


def get_unstaged_diff() -> str:
    """Return the diff for unstaged changes."""

    return run_git_command(["diff"])


def collect_git_context() -> GitChangeContext:
    """Collect Git status plus staged and unstaged diffs."""

    status = get_git_status()
    return GitChangeContext(
        status=status,
        staged_diff=get_staged_diff(),
        unstaged_diff=get_unstaged_diff(),
    )
