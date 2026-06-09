from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from dataclasses import dataclass


# Modules a solution snippet may import. Everything else (os, sys, socket,
# subprocess, requests, pathlib, ...) is rejected before execution.
ALLOWED_MODULES = {
    "math",
    "cmath",
    "statistics",
    "random",
    "decimal",
    "fractions",
    "numbers",
    "itertools",
    "functools",
    "operator",
    "collections",
    "json",
    "re",
    "datetime",
    "string",
    "textwrap",
}

# Builtins that grant filesystem, network, import, or arbitrary-eval power.
FORBIDDEN_NAMES = {
    "open",
    "exec",
    "eval",
    "compile",
    "input",
    "__import__",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "breakpoint",
    "memoryview",
    "help",
    "exit",
    "quit",
}

CODE_FENCE = re.compile(r"```[a-zA-Z0-9_+\-]*\n(.*?)```", re.DOTALL)
_CODE_MARKERS = ("python", "pandas", "sklearn", "numpy", "print(", "def ", "import ", "for ", "while ")


@dataclass
class SandboxResult:
    ok: bool
    output: str
    reason: str = ""


def looks_like_code(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _CODE_MARKERS)


def extract_code(question: str) -> str | None:
    """Return a runnable Python snippet from a question, or None.

    Prefers an explicit fenced block; falls back to treating the whole input as
    code when it both looks like code and parses as a Python module.
    """
    match = CODE_FENCE.search(question)
    if match:
        return match.group(1).strip() or None
    if looks_like_code(question):
        candidate = question.strip()
        try:
            ast.parse(candidate)
        except SyntaxError:
            return None
        return candidate
    return None


def validate_code(code: str) -> str | None:
    """Static allowlist check. Returns a rejection reason, or None if allowed."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"syntax error: {exc.msg}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_MODULES:
                    return f"import of '{alias.name}' is not allowed"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_MODULES:
                return f"import from '{node.module}' is not allowed"
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                return f"dunder attribute access '{node.attr}' is not allowed"
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                return f"use of '{node.id}' is not allowed"
    return None


def _restricted_env() -> dict[str, str]:
    # Keep only what the interpreter needs to launch; drop API keys and config.
    keep = ("PATH", "SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "LD_LIBRARY_PATH")
    return {key: os.environ[key] for key in keep if key in os.environ}


def run_code(code: str, timeout: float = 5.0) -> SandboxResult:
    """Execute a validated snippet in an isolated subprocess and capture stdout."""
    reason = validate_code(code)
    if reason is not None:
        return SandboxResult(ok=False, output="", reason=reason)

    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_restricted_env(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(ok=False, output="", reason=f"execution exceeded {timeout:g}s timeout")
    except OSError as exc:  # pragma: no cover - platform launch failure
        return SandboxResult(ok=False, output="", reason=f"could not launch sandbox: {exc}")

    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "non-zero exit"
        return SandboxResult(ok=False, output="", reason=detail)
    return SandboxResult(ok=True, output=completed.stdout.strip())
