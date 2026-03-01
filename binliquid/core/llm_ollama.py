from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

from binliquid.core.providers import (
    ChatProvider,
    OllamaProvider,
    ProviderAttempt,
    ProviderChainReport,
    ProviderGenerationError,
    TransformersProvider,
)


class LLMClient(Protocol):
    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        ...

    def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> Iterator[str]:
        ...


class LLMGenerationError(RuntimeError):
    """Raised when LLM generation fails across all configured providers."""


class OllamaLLM:
    """Provider-backed client kept for backward compatibility with existing imports.

    The class now supports `auto` selection and optional fallback provider chains.
    """

    def __init__(
        self,
        model_name: str,
        temperature: float = 0.2,
        host: str | None = None,
        timeout_s: float = 60.0,
        client: Any | None = None,
        provider_name: str = "auto",
        fallback_provider: str = "transformers",
        fallback_enabled: bool = True,
        hf_model_id: str = "distilgpt2",
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.provider_name = provider_name
        self.fallback_provider = fallback_provider
        self.fallback_enabled = fallback_enabled
        self._last_chain_report = ProviderChainReport(selected_provider=None, attempts=[])

        self._primary = self._build_provider(
            provider_name=provider_name,
            model_name=model_name,
            temperature=temperature,
            host=host,
            timeout_s=timeout_s,
            client=client,
            hf_model_id=hf_model_id,
            device=device,
        )
        self._fallback = None
        if fallback_enabled and fallback_provider and fallback_provider != provider_name:
            self._fallback = self._build_provider(
                provider_name=fallback_provider,
                model_name=model_name,
                temperature=temperature,
                host=host,
                timeout_s=timeout_s,
                client=None,
                hf_model_id=hf_model_id,
                device=device,
            )

    @staticmethod
    def _build_provider(
        *,
        provider_name: str,
        model_name: str,
        temperature: float,
        host: str | None,
        timeout_s: float,
        client: Any | None,
        hf_model_id: str,
        device: str,
    ) -> ChatProvider:
        normalized = provider_name.strip().lower()
        if normalized in {"auto", "ollama"}:
            return OllamaProvider(
                model_name=model_name,
                temperature=temperature,
                host=host,
                timeout_s=timeout_s,
                client=client,
            )
        if normalized in {"transformers", "hf", "huggingface"}:
            return TransformersProvider(
                model_name=model_name,
                temperature=temperature,
                hf_model_id=hf_model_id,
                device=device,
            )
        raise ValueError(f"unsupported provider: {provider_name}")

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        attempts: list[ProviderAttempt] = []

        providers: list[ChatProvider] = []
        if self.provider_name == "auto":
            providers.append(self._primary)
            if self._fallback is not None:
                providers.append(self._fallback)
        else:
            providers.append(self._primary)
            if self._fallback is not None:
                providers.append(self._fallback)

        last_error: str | None = None
        for provider in providers:
            try:
                content = provider.generate(prompt=prompt, system=system, json_mode=json_mode)
                attempts.append(ProviderAttempt(provider=provider.name, success=True, error=None))
                self._last_chain_report = ProviderChainReport(
                    selected_provider=provider.name,
                    attempts=attempts,
                )
                return content
            except ProviderGenerationError as exc:
                last_error = str(exc)
                attempts.append(
                    ProviderAttempt(provider=provider.name, success=False, error=str(exc))
                )
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                attempts.append(
                    ProviderAttempt(provider=provider.name, success=False, error=str(exc))
                )

        self._last_chain_report = ProviderChainReport(selected_provider=None, attempts=attempts)
        raise LLMGenerationError(last_error or "all providers failed")

    def chain_report(self) -> ProviderChainReport:
        return self._last_chain_report

    def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> Iterator[str]:
        attempts: list[ProviderAttempt] = []
        providers: list[ChatProvider] = []
        if self.provider_name == "auto":
            providers.append(self._primary)
            if self._fallback is not None:
                providers.append(self._fallback)
        else:
            providers.append(self._primary)
            if self._fallback is not None:
                providers.append(self._fallback)

        last_error: str | None = None
        for provider in providers:
            try:
                yielded = False
                for token in provider.generate_stream(
                    prompt=prompt,
                    system=system,
                    json_mode=json_mode,
                ):
                    yielded = True
                    yield token
                attempts.append(ProviderAttempt(provider=provider.name, success=True, error=None))
                self._last_chain_report = ProviderChainReport(
                    selected_provider=provider.name,
                    attempts=attempts,
                )
                if yielded:
                    return
            except ProviderGenerationError as exc:
                last_error = str(exc)
                attempts.append(
                    ProviderAttempt(provider=provider.name, success=False, error=str(exc))
                )
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                attempts.append(
                    ProviderAttempt(provider=provider.name, success=False, error=str(exc))
                )

        self._last_chain_report = ProviderChainReport(selected_provider=None, attempts=attempts)
        raise LLMGenerationError(last_error or "all providers failed")


@dataclass(slots=True)
class StubLLM:
    responses: list[str]
    default_response: str = "OK"
    calls: list[dict[str, object]] = field(default_factory=list)

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        self.calls.append({"prompt": prompt, "system": system, "json_mode": json_mode})
        if self.responses:
            return self.responses.pop(0)
        return self.default_response

    def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
    ) -> Iterator[str]:
        content = self.generate(prompt=prompt, system=system, json_mode=json_mode)
        yield from content


def check_ollama_runtime(model_name: str) -> dict[str, object]:
    provider = OllamaProvider(model_name=model_name)
    return provider.health(model_name=model_name)


def check_provider_chain(
    *,
    model_name: str,
    provider_name: str,
    fallback_provider: str,
    fallback_enabled: bool,
    hf_model_id: str,
    device: str,
) -> dict[str, object]:
    primary = OllamaLLM._build_provider(
        provider_name=provider_name,
        model_name=model_name,
        temperature=0.0,
        host=None,
        timeout_s=20.0,
        client=None,
        hf_model_id=hf_model_id,
        device=device,
    )
    report: dict[str, object] = {
        "provider": provider_name,
        "fallback_enabled": fallback_enabled,
        "fallback_provider": fallback_provider,
        "primary": primary.health(model_name=model_name),
        "selected_provider": primary.name,
    }

    if fallback_enabled and fallback_provider and fallback_provider != provider_name:
        secondary = OllamaLLM._build_provider(
            provider_name=fallback_provider,
            model_name=model_name,
            temperature=0.0,
            host=None,
            timeout_s=20.0,
            client=None,
            hf_model_id=hf_model_id,
            device=device,
        )
        report["secondary"] = secondary.health(model_name=model_name)

    if provider_name == "auto":
        primary_health = primary.health(model_name=model_name)
        daemon_ok = primary_health.get("daemon_ok")
        if isinstance(daemon_ok, bool) and not daemon_ok:
            report["selected_provider"] = fallback_provider if fallback_enabled else primary.name
    return report
