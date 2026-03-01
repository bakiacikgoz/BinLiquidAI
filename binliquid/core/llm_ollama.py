from __future__ import annotations

import subprocess
from dataclasses import dataclass
from shutil import which
from typing import Any, Protocol


class LLMClient(Protocol):
    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        ...


class LLMGenerationError(RuntimeError):
    """Raised when LLM generation fails.""" 


class OllamaLLM:
    def __init__(
        self,
        model_name: str,
        temperature: float = 0.2,
        host: str | None = None,
        timeout_s: float = 60.0,
        client: Any | None = None,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.timeout_s = timeout_s

        if client is not None:
            self._client = client
            return

        from ollama import Client

        self._client = Client(host=host, timeout=timeout_s)

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "options": {"temperature": self.temperature},
        }
        if json_mode:
            kwargs["format"] = "json"

        try:
            response = self._client.chat(**kwargs)
            return response.get("message", {}).get("content", "").strip()
        except Exception as exc:
            raise LLMGenerationError(str(exc)) from exc


@dataclass(slots=True)
class StubLLM:
    responses: list[str]
    default_response: str = "OK"

    def generate(self, prompt: str, system: str | None = None, json_mode: bool = False) -> str:
        del prompt, system, json_mode
        if self.responses:
            return self.responses.pop(0)
        return self.default_response


def check_ollama_runtime(model_name: str) -> dict[str, Any]:
    ollama_path = which("ollama")
    runtime_available = ollama_path is not None

    version = "not-found"
    daemon_ok = False
    model_present = False

    if runtime_available:
        version_proc = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if version_proc.returncode == 0:
            version = version_proc.stdout.strip() or "unknown"

        list_proc = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=False)
        daemon_ok = list_proc.returncode == 0
        if daemon_ok:
            model_present = model_name in list_proc.stdout

    return {
        "runtime_available": runtime_available,
        "ollama_path": ollama_path,
        "version": version,
        "daemon_ok": daemon_ok,
        "model_present": model_present,
        "model_name": model_name,
    }
