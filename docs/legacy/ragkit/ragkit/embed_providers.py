import requests
from typing import Callable, List

def make_embed_lmstudio(base_url: str, model: str, timeout: int = 60) -> Callable[[str], List[float]]:
    base = base_url.rstrip("/")
    def _embed(text: str) -> List[float]:
        url = f"{base}/v1/embeddings"
        payload = {"model": model, "input": text}
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data["data"][0]["embedding"]
    return _embed


def make_embed_openai(api_key: str, model: str, base_url: str = "https://api.openai.com/v1", timeout: int = 60) -> Callable[[str], List[float]]:
    base = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    def _embed(text: str) -> List[float]:
        url = f"{base}/embeddings"
        payload = {"model": model, "input": text}
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data["data"][0]["embedding"]
    return _embed
