from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Protocol

from jarvis.memory.store import MemoryStore


@dataclass
class ToolContext:
    memory: MemoryStore
    task_id: str


class ToolFn(Protocol):
    def __call__(self, ctx: ToolContext, **kwargs: Any) -> str: ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        self._tools[name] = fn

    def call(self, name: str, ctx: ToolContext, args: dict[str, Any]) -> str:
        if name not in self._tools:
            return f"unknown_tool:{name}"
        return self._tools[name](ctx, **args)

    def names(self) -> list[str]:
        return sorted(self._tools.keys())


def _tool_echo(ctx: ToolContext, message: str = "") -> str:
    return message


def _tool_memory_search(ctx: ToolContext, query: str = "", top_k: int = 5) -> str:
    hits = ctx.memory.search_long_term(query, top_k=top_k)
    if not hits:
        return "(no hits)"
    lines = [f"- {h.doc_id}: {h.text[:500]}" for h in hits]
    return "\n".join(lines)


def _tool_python_sandbox(ctx: ToolContext, code: str = "") -> str:
    """
    Restricted execution: expression-only eval in isolated dict.
    For real workloads use a container or remote sandbox.
    """
    safe_builtins = {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "round": round,
        "sorted": sorted,
    }
    g: dict[str, Any] = {"__builtins__": safe_builtins}
    try:
        return str(eval(code, g, {}))
    except Exception as e:
        return f"error:{type(e).__name__}:{e}"


def _tool_shell_allowlist(ctx: ToolContext, argv: str = "") -> str:
    """
    Only allows `python -c ...` style one-liners for demos; extend allowlist carefully.
    """
    parts = argv.strip().split(maxsplit=2)
    if len(parts) >= 2 and parts[0] == sys.executable and parts[1] == "-c":
        code = parts[2] if len(parts) > 2 else ""
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.stdout + proc.stderr
    return "denied:only `python -c` is allowed in this sandbox"


def mock_tools() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("echo", _tool_echo)
    reg.register("memory_search", _tool_memory_search)
    reg.register("python_sandbox", _tool_python_sandbox)
    reg.register("shell", _tool_shell_allowlist)
    return reg
