import requests
from typing import Callable

def make_llm_lmstudio(base_url: str, model: str, temperature: float = 0.2, timeout: int = 120) -> Callable[[str], str]:
    base = base_url.rstrip("/")
    def _call(prompt: str) -> str:
        url = f"{base}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Você é um assistente preciso e usa o contexto fornecido."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
    return _call


def make_llm_openai(api_key: str, model: str, base_url: str = "https://api.openai.com/v1",
                    temperature: float = 0.2, timeout: int = 120) -> Callable[[str], str]:
    base = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    def _call(prompt: str) -> str:
        url = f"{base}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a precise assistant that uses the provided context."},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
    return _call
