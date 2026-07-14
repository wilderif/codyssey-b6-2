# AI Git Commit & PR Draft Generator

Git 로컬 변경사항을 수집해 OpenAI Responses API로 커밋 메시지와 Pull Request 초안을 생성하는 Python CLI 도구입니다.

이 도구는 `git status`, `git diff --cached`, `git diff` 결과를 AI 입력으로 사용하고, 생성된 텍스트를 터미널에 출력합니다. 실제 `git commit`, `git push`, GitHub PR 생성은 수행하지 않습니다.

## 주요 기능

- 로컬 Git 변경 파일 목록과 staged/unstaged diff 수집
- 커밋 메시지 초안 생성
- `Why`, `What`, `How to Test` 구조의 PR 초안 생성
- 생성 결과 형식 검증 및 실패 시 최대 1회 재요청
- `--safe-mode`를 통한 민감정보 패턴 마스킹
- OpenAI Responses API REST 호출

## 폴더 구조

```text
.
├── README.md
├── demo_changes
│   └── demo_file.py
├── pyproject.toml
├── requirements.txt
├── src
│   ├── main.py
│   └── git_draft
│       ├── __init__.py
│       ├── ai_client.py
│       ├── cli.py
│       ├── generator.py
│       ├── git_utils.py
│       ├── prompts.py
│       └── validators.py
└── uv.lock
```

- `src/main.py`: CLI 엔트리 포인트
- `src/git_draft/cli.py`: 명령어와 옵션 파싱
- `src/git_draft/git_utils.py`: `git status`, `git diff` 변경사항 수집
- `src/git_draft/ai_client.py`: OpenAI Responses API REST 요청 처리
- `src/git_draft/prompts.py`: 커밋 메시지와 PR 초안 프롬프트 생성
- `src/git_draft/validators.py`: 생성 결과 형식 검증과 safe-mode 마스킹
- `src/git_draft/generator.py`: Git 수집, AI 호출, 검증, 출력 흐름 조합
- `demo_changes/demo_file.py`: commit/pr 시연용 빈 Python 파일
- `pyproject.toml`, `uv.lock`, `requirements.txt`: 의존성 관리 파일

## 설치

Python 3.10 이상이 필요합니다. `uv`를 사용하는 방법과 일반 Python 가상환경을 사용하는 방법 중 하나를 선택할 수 있습니다.

### uv 사용

```bash
uv sync
```

### 일반 Python 사용

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## API 키 설정

API 키는 `AI_API_KEY` 환경변수로 설정합니다.

### 방법 1: 터미널 환경변수로 설정

```bash
export AI_API_KEY="YOUR_KEY"
```

### 방법 2: `.env` 파일 사용

```bash
cp .env.example .env
```

`.env` 파일에 실제 키를 입력합니다.

```text
AI_API_KEY=YOUR_KEY
```

CLI 실행 시 `python-dotenv`가 `.env` 값을 현재 Python 프로세스 환경변수로 로드합니다.

## 사용법

### uv 사용

커밋 메시지 초안 생성:

```bash
uv run python src/main.py commit
```

PR 초안 생성:

```bash
uv run python src/main.py pr
```

민감정보 마스킹을 켜고 실행:

```bash
uv run python src/main.py commit --safe-mode
uv run python src/main.py pr --safe-mode
```

모델 파라미터를 지정해서 실행:

```bash
uv run python src/main.py commit --model gpt-5.4-mini --temperature 0.2 --max-tokens 800
```

### 일반 Python 사용

가상환경을 활성화한 뒤 실행합니다.

```bash
source .venv/bin/activate
python src/main.py commit
python src/main.py pr
python src/main.py commit --safe-mode
python src/main.py pr --model gpt-5.4-mini --temperature 0.2 --max-tokens 800
```

## CLI 옵션

| 옵션 | 기본값 | 설명 |
| --- | --- | --- |
| `--model` | `gpt-5.4-mini` | OpenAI Responses API에 전달할 모델 이름 |
| `--temperature` | `0.2` | 생성 결과의 무작위성 조절 값 |
| `--max-tokens` | `800` | Responses API의 `max_output_tokens`로 전달되는 최대 출력 토큰 수 |
| `--safe-mode` | 꺼짐 | diff를 AI에 보내기 전에 이메일, Bearer 토큰, 긴 API 키 형태 문자열을 마스킹 |

## Git 변경사항 입력 범위

CLI는 Git이 초기화된 프로젝트 루트에서 실행해야 합니다.

입력으로 사용하는 Git 정보:

- `git status --short`: 변경된 파일 목록과 상태
- `git diff --cached`: staged 변경 내용
- `git diff`: unstaged 변경 내용

변경사항이 없으면 AI API를 호출하지 않고 아래 메시지를 출력합니다.

```text
[INFO] 변경 사항이 없습니다.
```

새로 만든 untracked 파일은 `git status`에는 보이지만, 파일 내용은 `git diff`에 포함되지 않습니다. 새 파일 내용까지 초안 생성에 반영하려면 먼저 staging 하세요.

```bash
git add path/to/new_file.py
git diff --cached
```

## 출력 예시

### 커밋 메시지

```text
[INFO] Git status 수집 완료: 2개 항목 변경 감지
[INFO] Git diff 컨텍스트 수집 완료: 48줄
[INFO] AI API 요청 중...
[DONE] Commit Message Draft 생성 완료
[INFO] AI API 요청 시도 횟수: 1

------------------------------------------------
Commit Message Draft - 검토용 초안
------------------------------------------------
feat: Add Git-based commit message generation
------------------------------------------------
```

### PR 초안

```text
[INFO] Git status 수집 완료: 3개 항목 변경 감지
[INFO] Git diff 컨텍스트 수집 완료: 72줄
[INFO] safe-mode 활성화: 민감정보 패턴을 마스킹했습니다.
[INFO] AI API 요청 중...
[DONE] Pull Request Draft 생성 완료
[INFO] AI API 요청 시도 횟수: 1

------------------------------------------------
Pull Request Draft - 검토용 초안
------------------------------------------------
feat: Add Git-based PR draft generation

## Why
- Reviewers need concise PR context based on local Git changes.

## What
- Collect staged and unstaged diffs for the AI prompt context.
- Include the required PR title and body section structure in the prompt.

## How to Test
- Run `uv run python src/main.py pr --safe-mode` and confirm a PR draft is printed.
------------------------------------------------
```

생성 결과는 검토용 초안입니다. 실제 커밋 메시지나 PR 본문에 적용하기 전에 반드시 내용을 확인하세요.

## 오류 예시

API 키가 없을 때:

```text
[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다. 예) export AI_API_KEY="YOUR_KEY"
```

API 요청 실패 시에는 가능한 원인을 포함해 메시지를 출력합니다. 예를 들어 인증/권한 오류, 요청 제한, 네트워크 오류, 응답 형식 오류 등이 표시될 수 있습니다.

## 운영 및 보안 참고사항

- `git diff`에는 API 키, 인증 토큰, 이메일 주소, 개인정보, 내부 구현 정보가 포함될 수 있습니다.
- 민감정보가 포함될 가능성이 있으면 `--safe-mode`를 사용하세요.
- `--safe-mode`는 API 키처럼 보이는 긴 토큰, Bearer 토큰, 이메일 주소를 마스킹한 뒤 AI API로 전송합니다.
- 마스킹은 보조 안전장치입니다. 전송 전 diff 내용을 직접 확인하는 것이 가장 안전합니다.
- `commit` 또는 `pr` 실행 시 기본적으로 AI API 요청은 1회이며, 출력 형식 검증 실패 시 최대 1회 더 요청합니다.

## 수동 확인 방법

### 시연용 변경사항 만들기

`commit`, `pr`, `--safe-mode`를 테스트하려면 아래 예시를 `demo_changes/demo_file.py`에 복사해 넣은 뒤 실행하세요. 예시에 포함된 이메일과 토큰은 모두 가짜 값이며, `--safe-mode` 마스킹 확인용입니다.

```python
"""Provide a tiny demo function for CLI draft testing."""


DEMO_SUPPORT_EMAIL = "demo.user@example.com"
DEMO_AUTH_HEADER = "Bearer demo_token_for_safe_mode_testing_1234567890"
DEMO_API_KEY = "sk-demo1234567890abcdef1234567890abcdef"


def greet_user(name: str) -> str:
    """Return a short greeting message."""

    return f"Hello, {name}!"


def build_demo_summary(name: str) -> str:
    """Return a demo summary that includes fake sensitive values."""

    greeting = greet_user(name)
    return (
        f"{greeting} Contact {DEMO_SUPPORT_EMAIL}. "
        f"Auth={DEMO_AUTH_HEADER}. Key={DEMO_API_KEY}."
    )


if __name__ == "__main__":
    print(build_demo_summary("Codyssey"))
```

복사 후 변경사항이 diff에 잡히는지 확인합니다.

```bash
git diff demo_changes/demo_file.py
```

`--safe-mode`를 켜면 diff 안의 이메일, Bearer 토큰, 긴 API 키 형태 문자열을 마스킹한 뒤 AI API로 전송합니다.

### 확인 명령

```bash
uv sync
uv run python src/main.py commit
uv run python src/main.py commit --safe-mode
uv run python src/main.py pr
uv run python src/main.py pr --safe-mode
uv run python src/main.py pr --model gpt-5.4-mini --temperature 0.2 --max-tokens 16
```

확인할 항목:

- Git 변경사항이 없을 때 AI API를 호출하지 않는지 확인
- `AI_API_KEY`가 없을 때 명확한 오류가 출력되는지 확인
- 커밋 초안에 한 줄 제목만 포함되는지 확인
- PR 초안에 `Why`, `What`, `How to Test` 섹션과 각 섹션 bullet이 포함되는지 확인
- `--safe-mode` 실행 시 민감정보 마스킹 안내가 출력되는지 확인
