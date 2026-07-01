"""Call the OpenAI Responses API with requests."""

from __future__ import annotations

import json
import os
from typing import Any

import requests


# OpenAI Responses API endpoint for text generation.
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

# Environment variable name required by this assignment.
API_KEY_ENV_VAR = "AI_API_KEY"

# Request timeout in seconds to avoid hanging the CLI indefinitely.
REQUEST_TIMEOUT_SECONDS = 60


class AiClientError(Exception):
    """Represent a user-facing AI client failure."""


def get_api_key() -> str:
    """Return the configured AI API key or raise a clear error."""

    api_key = os.getenv(API_KEY_ENV_VAR)
    if not api_key:
        raise AiClientError(
            f"{API_KEY_ENV_VAR} 환경변수가 설정되지 않았습니다. "
            f'예) export {API_KEY_ENV_VAR}="YOUR_KEY"'
        )
    return api_key


def build_response_payload(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Build the JSON payload for the Responses API."""

    return {
        "model": model,
        "input": prompt,
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }


def extract_error_message(response: requests.Response) -> str:
    """Return a safe error message from an API error response."""

    try:
        data = response.json()
    except json.JSONDecodeError:
        return response.text.strip()

    error = data.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message

    return response.text.strip()


def classify_http_error(response: requests.Response) -> str:
    """Return a likely cause for an unsuccessful API response."""

    status_code = response.status_code
    message = extract_error_message(response)
    lower_message = message.lower()

    if status_code in (401, 403):
        cause = "인증 또는 권한 오류입니다. API 키와 프로젝트 접근 권한을 확인하세요."
    elif status_code == 429 and any(term in lower_message for term in ("quota", "credit", "billing")):
        cause = "할당량 또는 결제 한도 오류입니다. API 사용량과 결제 상태를 확인하세요."
    elif status_code == 429:
        cause = "요청 제한(rate limit)에 도달했습니다. 잠시 후 다시 시도하세요."
    elif 400 <= status_code < 500:
        cause = "요청 형식 또는 모델/파라미터 오류입니다."
    elif status_code >= 500:
        cause = "OpenAI 서버 오류입니다. 잠시 후 다시 시도하세요."
    else:
        cause = "알 수 없는 API 오류입니다."

    if message:
        return f"{cause} 상세: {message}"
    return cause


def extract_output_text(response_data: dict[str, Any]) -> str:
    """Extract generated text from a Responses API JSON body."""

    output_text = response_data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    text_parts = []
    output_items = response_data.get("output", [])
    if not isinstance(output_items, list):
        raise AiClientError("OpenAI API 응답 형식이 올바르지 않습니다.")

    for output_item in output_items:
        if not isinstance(output_item, dict):
            continue

        content_items = output_item.get("content", [])
        if not isinstance(content_items, list):
            continue

        for content_item in content_items:
            if not isinstance(content_item, dict):
                continue

            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

    if not text_parts:
        raise AiClientError("OpenAI API 응답에서 생성 텍스트를 찾을 수 없습니다.")

    return "\n".join(text_parts).strip()


def request_generated_text(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call the Responses API and return generated text."""

    api_key = get_api_key()
    payload = build_response_payload(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            OPENAI_RESPONSES_URL,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise AiClientError("네트워크 시간 초과로 OpenAI API 요청에 실패했습니다.") from exc
    except requests.ConnectionError as exc:
        raise AiClientError("네트워크 연결 오류로 OpenAI API 요청에 실패했습니다.") from exc
    except requests.RequestException as exc:
        raise AiClientError(f"OpenAI API 요청 중 네트워크 오류가 발생했습니다: {exc}") from exc

    if not response.ok:
        raise AiClientError(classify_http_error(response))

    try:
        response_data = response.json()
    except json.JSONDecodeError as exc:
        raise AiClientError("OpenAI API 응답을 JSON으로 해석할 수 없습니다.") from exc

    return extract_output_text(response_data)
