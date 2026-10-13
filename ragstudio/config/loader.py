"""Configuration: tracked defaults (config.ini) + local file (config.local.ini) + RAGSTUDIO_* environment."""
from __future__ import annotations

import configparser
import os
from typing import Any

from ..core import paths
from ..core.errors import ConfigError

SECRET_KEYS = {("openai", "api_key")}


class Config:
    def __init__(self) -> None:
        self._defaults = configparser.ConfigParser(interpolation=None)
        self._defaults.read(paths.default_config_path(), encoding="utf-8")
        self._local = configparser.ConfigParser(interpolation=None)
        local = paths.local_config_path()
        if local.is_file():
            self._local.read(local, encoding="utf-8")

    # ------------------------------------------------------------------ reads
    def get(self, section: str, key: str, default: str = "") -> str:
        env = os.environ.get(f"RAGSTUDIO_{section.upper()}_{key.upper()}")
        if env is not None:
            return env
        if self._local.has_option(section, key):
            return self._local.get(section, key).strip()
        if self._defaults.has_option(section, key):
            return self._defaults.get(section, key).strip()
        return default

    def get_int(self, section: str, key: str, default: int = 0) -> int:
        raw = self.get(section, key, "")
        try:
            return int(raw) if raw != "" else default
        except ValueError as exc:
            raise ConfigError(f"[{section}] {key} must be an integer, got {raw!r}") from exc

    def get_float(self, section: str, key: str, default: float = 0.0) -> float:
        raw = self.get(section, key, "")
        try:
            return float(raw) if raw != "" else default
        except ValueError as exc:
            raise ConfigError(f"[{section}] {key} must be a number, got {raw!r}") from exc

    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        raw = self.get(section, key, "")
        return default if raw == "" else raw.lower() in ("1", "true", "yes", "on", "sim")

    def get_list(self, section: str, key: str) -> list[str]:
        return [item.strip() for item in self.get(section, key, "").split(",") if item.strip()]

    def provider(self) -> str:
        """Resolved provider name: mock | lmstudio | ollama | openai."""
        chosen = (os.environ.get("RAGSTUDIO_PROVIDER") or self.get("provider", "default", "auto")).lower()
        if chosen in ("mock", "openai", "lmstudio", "ollama"):
            return chosen
        if chosen in ("lm_studio", "lm-studio"):
            return "lmstudio"
        if chosen != "auto":
            raise ConfigError(f"unknown provider '{chosen}' (use auto, mock, openai, lmstudio or ollama)")
        if self.get("lm_studio", "base_url"):
            return "lmstudio"
        if self.get("ollama", "base_url"):
            return "ollama"
        return "openai"

    def as_dict(self, mask_secrets: bool = True) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        sections = list(dict.fromkeys(self._defaults.sections() + self._local.sections()))
        for section in sections:
            keys = set(self._defaults.options(section) if self._defaults.has_section(section) else [])
            keys |= set(self._local.options(section) if self._local.has_section(section) else [])
            out[section] = {}
            for key in sorted(keys):
                value = self.get(section, key)
                if mask_secrets and (section, key) in SECRET_KEYS and value:
                    value = value[:3] + "…" + value[-4:] if len(value) > 8 else "***"
                out[section][key] = value
        out["provider"]["resolved"] = self.provider()
        return out

    # ----------------------------------------------------------------- writes
    def set(self, section: str, key: str, value: str) -> None:
        if not self._defaults.has_option(section, key):
            raise ConfigError(f"unknown configuration key [{section}] {key}")
        if not self._local.has_section(section):
            self._local.add_section(section)
        self._local.set(section, key, str(value))

    def save(self) -> str:
        path = paths.local_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            self._local.write(fh)
        return str(path)


def load() -> Config:
    return Config()
