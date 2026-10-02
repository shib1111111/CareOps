from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from careops.infrastructure.config import PROVIDER_KEYS, RuntimeConfig, runtime_config

T = TypeVar("T", bound=BaseModel)


class AIConfigurationError(RuntimeError):
    pass


class LLMRuntime:
    """Thin, provider-agnostic wrapper around whichever chat model is configured.

    The provider and model come from ``LLM_PROVIDER`` / ``LLM_MODEL`` in ``.env``; the API key
    comes from that provider's own variable (see ``PROVIDER_KEYS``). Nothing downstream needs to
    know which model is in use.
    """

    def __init__(self) -> None:
        config = runtime_config()
        self.provider = config.provider
        self.model = config.model
        self._llm = self._build(config)

    @staticmethod
    def _build(config: RuntimeConfig):
        key_var = config.key_env_var
        if key_var is None:
            supported = ", ".join(sorted(PROVIDER_KEYS))
            raise AIConfigurationError(
                f"Unsupported LLM_PROVIDER '{config.provider}'. Supported: {supported}."
            )
        if not config.api_key:
            raise AIConfigurationError(
                f"{key_var} is not set. Add it to .env (LLM_PROVIDER={config.provider})."
            )
        try:
            from langchain.chat_models import init_chat_model
        except ImportError as exc:  # pragma: no cover - langchain is a core dependency
            raise AIConfigurationError("langchain is not installed.") from exc
        try:
            # The integration package reads the key from the provider's own environment variable.
            return init_chat_model(config.model, model_provider=config.provider, temperature=0.0)
        except ImportError as exc:
            raise AIConfigurationError(
                f"The integration package for provider '{config.provider}' is not installed "
                f"({exc}). Run: python -m pip install -e ."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - bad model name, bad kwargs, etc.
            raise AIConfigurationError(
                f"Could not initialise model '{config.model}' for provider '{config.provider}': {exc}"
            ) from exc

    def _structured(self, schema: type[T]):
        # OpenAI's strict json_schema mode rejects free-form dict fields (e.g. hand-offs), so use
        # tool calling there. Other providers use their default structured-output method.
        if self.provider == "openai":
            return self._llm.with_structured_output(schema, method="function_calling")
        return self._llm.with_structured_output(schema)

    def structured_invoke(self, system_prompt: str, user_payload: str, schema: type[T]) -> T:
        structured = self._structured(schema)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ]
        last_error: Exception | None = None
        for _ in range(2):  # one retry for an occasional empty / malformed structured response
            try:
                response = structured.invoke(messages)
                if response is None:
                    raise ValueError("The model returned no structured output.")
                return schema.model_validate(response)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        raise RuntimeError(
            f"The model did not return a valid response: {last_error}"
        ) from last_error
