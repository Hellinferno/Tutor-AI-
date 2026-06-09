from __future__ import annotations

import json
import os
from pathlib import Path


def _prompts_dir() -> Path:
    override = os.getenv("STUDYLAB_PROMPTS_DIR")
    if override:
        return Path(override)
    # packages/studylab_core/studylab_core/prompts.py -> packages/prompts
    return Path(__file__).resolve().parents[2] / "prompts"


def _registry() -> dict[str, dict[str, str]]:
    registry_path = _prompts_dir() / "registry.json"
    return json.loads(registry_path.read_text(encoding="utf-8"))


def list_prompts() -> list[str]:
    return sorted(_registry().keys())


def load_prompt(name: str) -> str:
    """Return the raw template text for a registered prompt name."""
    registry = _registry()
    if name not in registry:
        raise KeyError(f"Unknown prompt: {name}. Available: {', '.join(sorted(registry))}")
    template_path = _prompts_dir() / registry[name]["file"]
    return template_path.read_text(encoding="utf-8")


def render_prompt(name: str, **values: object) -> str:
    """Load a prompt and substitute ``{{placeholder}}`` tokens with provided values."""
    template = load_prompt(name)
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template
