from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from jarvis.agent.tools import ToolContext, ToolRegistry, mock_tools
from jarvis.memory.store import MemoryStore


@dataclass
class TaskResult:
    task_id: str
    success: bool
    steps: list[dict[str, Any]]
    final_message: str
    metadata: dict[str, Any] = field(default_factory=dict)


PlannerFn = Callable[[str, list[dict[str, Any]]], dict[str, Any]]


def _default_planner(
    task: str,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Placeholder planner: single echo step. Replace with LLM JSON plan in production.
    """
    if not history:
        return {"action": "tool", "tool": "echo", "args": {"message": f"planned:{task}"}}
    last = history[-1].get("observation", "")
    if "planned:" in last and len(history) < 3:
        return {"action": "tool", "tool": "memory_search", "args": {"query": task, "top_k": 3}}
    return {"action": "done", "message": last or "done"}


class TaskAgent:
    """
    Observe → plan → act loop with tool sandbox and episodic memory writes.
    """

    def __init__(
        self,
        memory: MemoryStore,
        tools: ToolRegistry | None = None,
        planner: PlannerFn | None = None,
        max_steps: int = 16,
    ) -> None:
        self.memory = memory
        self.tools = tools or mock_tools()
        self.planner = planner or _default_planner
        self.max_steps = max_steps

    def run(self, task_description: str, task_id: str | None = None) -> TaskResult:
        tid = task_id or str(uuid.uuid4())
        ctx = ToolContext(memory=self.memory, task_id=tid)
        history: list[dict[str, Any]] = []
        self.memory.append_working("user", task_description)

        for _ in range(self.max_steps):
            plan = self.planner(task_description, history)
            action = plan.get("action")
            step_record: dict[str, Any] = {"plan": plan}

            if action == "done":
                msg = str(plan.get("message", "done"))
                step_record["observation"] = msg
                history.append(step_record)
                self.memory.append_working("assistant", msg)
                ep = self.memory.new_episode(
                    task_id=tid,
                    steps=history,
                    outcome="success",
                    metadata={"final_message": msg},
                )
                return TaskResult(
                    task_id=tid,
                    success=True,
                    steps=history,
                    final_message=msg,
                    metadata={"episode_id": ep.episode_id},
                )

            if action == "tool":
                name = str(plan.get("tool", ""))
                args = dict(plan.get("args") or {})
                obs = self.tools.call(name, ctx, args)
                step_record["observation"] = obs
                history.append(step_record)
                self.memory.append_working("tool", f"{name} -> {obs[:2000]}")
                continue

            step_record["observation"] = f"unknown_action:{action}"
            history.append(step_record)

        ep = self.memory.new_episode(
            task_id=tid,
            steps=history,
            outcome="max_steps",
            metadata={},
        )
        return TaskResult(
            task_id=tid,
            success=False,
            steps=history,
            final_message="max_steps",
            metadata={"episode_id": ep.episode_id},
        )
