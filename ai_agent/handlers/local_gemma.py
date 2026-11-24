"""Local Gemma client for one Ollama container."""

import requests


class LocalGemma:
    """Calls a single Ollama server that hosts one Gemma model."""

    def __init__(self, base_url: str, model: str):
        self.base_url = (base_url or "").rstrip("/")
        self.model = model or ""

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        json_mode: bool = False,
        max_tokens: int = None,
        top_p: float = None,
        top_k: int = None,
    ) -> str:
        if not self.configured:
            raise RuntimeError("Local Gemma URL is not configured")

        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens
        if top_p is not None:
            options["top_p"] = top_p
        if top_k is not None:
            options["top_k"] = top_k

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if json_mode:
            payload["format"] = "json"

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        return (response.json().get("response") or "").strip()
