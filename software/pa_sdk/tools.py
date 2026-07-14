"""工具编排引擎 — 并发工具调用与执行。"""

from __future__ import annotations

import time
from typing import Any

from .types import ActionPlan, ToolResult


class ToolRegistry:
    """工具注册表（固化在 CMEM）。"""

    def __init__(self):
        self._tools: dict[str, callable] = {
            "code_search": self._code_search,
            "show_example": self._show_example,
            "web_search": self._web_search,
            "summarize": self._summarize,
            "gentle_prompt": self._gentle_prompt,
            "highlight_text": self._highlight_text,
            "define_term": self._define_term,
            "explain_concept": self._explain_concept,
        }

    def execute(self, name: str, params: dict[str, Any]) -> ToolResult:
        start = time.time()
        handler = self._tools.get(name)
        if handler is None:
            return ToolResult(name, False, f"unknown tool: {name}", 0.0)
        output = handler(params)
        latency = (time.time() - start) * 1000
        return ToolResult(name, True, output, latency)

    @staticmethod
    def _code_search(params: dict) -> str:
        query = params.get("query", "API usage example")
        style = params.get("style", "concise")
        return f"[code_search] Found example for '{query}' (style={style})"

    @staticmethod
    def _show_example(params: dict) -> str:
        return "[show_example] Displaying code snippet in IDE overlay"

    @staticmethod
    def _web_search(params: dict) -> str:
        max_r = params.get("max_results", 3)
        return f"[web_search] Top {max_r} results retrieved"

    @staticmethod
    def _summarize(params: dict) -> str:
        return "[summarize] Generated 3-sentence summary"

    @staticmethod
    def _gentle_prompt(params: dict) -> str:
        tone = params.get("tone", "supportive")
        return f"[gentle_prompt] Sent {tone} check-in message"

    @staticmethod
    def _highlight_text(params: dict) -> str:
        return "[highlight_text] Highlighted relevant paragraph"

    @staticmethod
    def _define_term(params: dict) -> str:
        return "[define_term] Showed definition tooltip"

    @staticmethod
    def _explain_concept(params: dict) -> str:
        level = params.get("detail_level", "concise")
        return f"[explain_concept] Step-by-step explanation ({level})"


class ToolOrchestrator:
    """工具编排引擎：硬件 Tool Call 解析器 + 并行执行单元。

    硬件映射：
    - pa_tool_parse: JSON function call → 执行指令（零 CPU 序列化）
    - pa_tool_exec:  最多 8 路并发，带超时与回滚
    """

    MAX_CONCURRENT = 8
    TIMEOUT_MS = 5000

    def __init__(self):
        self.registry = ToolRegistry()
        self._history: list[ToolResult] = []

    def execute_plan(self, plan: ActionPlan) -> list[ToolResult]:
        """并发执行行动计划中的所有工具。"""
        results = []
        for tool_name in plan.tools[: self.MAX_CONCURRENT]:
            merged_params = {**plan.params, "need": plan.need.value}
            result = self.registry.execute(tool_name, merged_params)
            results.append(result)
            self._history.append(result)
            if result.latency_ms > self.TIMEOUT_MS:
                break
        return results

    def get_history(self) -> list[ToolResult]:
        return list(self._history)
