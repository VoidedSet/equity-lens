"""LLM provider abstractions with exponential backoff, full jitter, and Bedrock Converse support."""

import random
import time
from typing import Any, Callable, List, Optional, Protocol, Sequence, Union

from cloud.common.config import CloudConfig, get_config


class LLMProvider(Protocol):
    """Minimal synchronous text-generation protocol shared by extraction workers."""

    def generate(
        self,
        system_prompt: str,
        user_content: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str: ...


def retry_with_backoff(
    fn: Callable[[], str],
    is_retryable: Callable[[Exception], bool],
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> str:
    """Execute fn with exponential backoff and full jitter on retryable exceptions."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            if attempt >= max_attempts - 1 or not is_retryable(exc):
                raise
            cap = min(max_delay, base_delay * (2**attempt))
            delay = random.uniform(0.0, cap)
            if delay <= 0.0:
                delay = min(max_delay, 0.01 * (2**attempt))
            sleep_fn(delay)

    raise RuntimeError("Unreachable retry state")


def _extract_error_meta(exc: Exception) -> tuple[str, Optional[int]]:
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        code = str(response.get("Error", {}).get("Code", ""))
        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return code, status
    status = getattr(exc, "status_code", None)
    return "", status


def _is_retryable_bedrock_error(exc: Exception) -> bool:
    code, status = _extract_error_meta(exc)
    if code in {
        "ThrottlingException",
        "ServiceUnavailableException",
        "ModelTimeoutException",
        "InternalServerException",
        "TooManyRequestsException",
    }:
        return True
    if status in {429, 500, 502, 503, 504}:
        return True
    msg = f"{type(exc).__name__} {exc}".lower()
    return any(tok in msg for tok in ("throttl", "rate limit", "too many requests", "timeout", "temporarily unavailable"))


def _is_retryable_http_error(exc: Exception) -> bool:
    _, status = _extract_error_meta(exc)
    if status in {429, 500, 502, 503, 504}:
        return True
    msg = f"{type(exc).__name__} {exc}".lower()
    return any(tok in msg for tok in ("429", "rate limit", "timeout", "connection", "502", "503", "504"))


class BedrockProvider:
    """Amazon Bedrock Converse API client with adaptive retries and lazy boto3 import."""

    def __init__(
        self,
        model_id: str,
        region: str = "ap-south-1",
        client: Any = None,
        max_attempts: int = 4,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model_id = model_id
        self.region = region
        self._client = client
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.sleep_fn = sleep_fn

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        import boto3
        from botocore.config import Config

        cfg = Config(region_name=self.region, retries={"max_attempts": 1})
        self._client = boto3.client("bedrock-runtime", config=cfg)
        return self._client

    def generate(
        self,
        system_prompt: str,
        user_content: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        client = self._get_client()

        def _invoke() -> str:
            response = client.converse(
                modelId=self.model_id,
                system=[{"text": system_prompt}],
                messages=[{"role": "user", "content": [{"text": user_content}]}],
                inferenceConfig={"temperature": temperature, "maxTokens": max_tokens},
            )
            blocks = response.get("output", {}).get("message", {}).get("content", [])
            texts = [blk["text"] for blk in blocks if isinstance(blk, dict) and "text" in blk]
            return "\n".join(texts)

        return retry_with_backoff(
            _invoke,
            is_retryable=_is_retryable_bedrock_error,
            max_attempts=self.max_attempts,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            sleep_fn=self.sleep_fn,
        )


class FeatherlessProvider:
    """OpenAI-compatible Featherless AI client wrapped in the LLMProvider interface."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.featherless.ai/v1",
        model_id: str = "google/gemma-3-27b-it",
        client: Any = None,
        max_attempts: int = 4,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model_id = model_id
        self._client = client
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.sleep_fn = sleep_fn

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise RuntimeError("FEATHERLESS_API_KEY is required when LLM_PROVIDER=featherless")
        from openai import OpenAI

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def generate(
        self,
        system_prompt: str,
        user_content: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        client = self._get_client()

        def _invoke() -> str:
            response = client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""

        return retry_with_backoff(
            _invoke,
            is_retryable=_is_retryable_http_error,
            max_attempts=self.max_attempts,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            sleep_fn=self.sleep_fn,
        )


class MockLLMProvider:
    """Deterministic in-memory LLM provider for offline tests."""

    def __init__(
        self,
        responses: Union[str, Sequence[str], Callable[[str, str], str]] = "[]",
    ) -> None:
        self._responses = responses
        self._idx = 0
        self.calls: List[dict] = []

    def generate(
        self,
        system_prompt: str,
        user_content: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_content": user_content,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if callable(self._responses):
            return self._responses(system_prompt, user_content)
        if isinstance(self._responses, str):
            return self._responses
        if self._idx < len(self._responses):
            val = self._responses[self._idx]
            self._idx += 1
            return val
        return "[]"


def get_llm_provider(config: Optional[CloudConfig] = None) -> LLMProvider:
    """Instantiate the configured LLM provider."""
    cfg = config or get_config()
    if cfg.llm_provider == "bedrock":
        return BedrockProvider(model_id=cfg.bedrock_model_id, region=cfg.bedrock_region)
    if cfg.llm_provider == "mock":
        return MockLLMProvider("[]")
    return FeatherlessProvider(
        api_key=cfg.featherless_api_key or "",
        base_url=cfg.featherless_base_url,
        model_id=cfg.gemma_model,
    )
