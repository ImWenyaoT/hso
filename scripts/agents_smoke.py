"""Minimal HelloAgent smoke：验证 Agents SDK + 我们的 OAuth runtime 能跑通。

ChatGPT 后端强制 stream=True，所以用 ``Runner.run_streamed``。

跑：
    uv run python scripts/agents_smoke.py
"""

from __future__ import annotations

import asyncio

from agents import Agent, Runner, function_tool
from pydantic import BaseModel

from hso.agents import build_runtime, set_default_runtime


class Greeting(BaseModel):
    """structured output schema：让模型返回 type-safe 问候。"""

    word: str
    language: str


@function_tool
def reverse_text(text: str) -> str:
    """把输入字符串反转。

    Args:
        text: 任意字符串。
    """
    return text[::-1]


async def _run(agent: Agent, prompt: str) -> object:
    """跑 stream agent 拿 final_output；丢弃中间 events（demo 简化）。"""
    streaming = Runner.run_streamed(agent, prompt)
    async for _event in streaming.stream_events():
        pass
    return streaming  # streaming 拿 final_output / new_items


async def main() -> None:
    """端到端跑：runtime build → Agent 定义 → Runner.run_streamed → 看输出。"""
    runtime = build_runtime(auth_mode="oauth")
    set_default_runtime(runtime)

    agent_structured = Agent(
        name="HelloAgent",
        instructions="Reply with a friendly greeting.",
        model=runtime.model,
        model_settings=runtime.model_settings,
        output_type=Greeting,
    )

    print("[1/2] 不调工具，要求 structured output (Greeting)")
    streaming = await _run(agent_structured, "Greet me in Japanese.")
    print(f"  → final_output: {streaming.final_output!r}")

    agent_with_tool = Agent(
        name="ToolAgent",
        instructions=(
            "You can call the reverse_text tool. When asked to reverse a string, "
            "call the tool and return the reversed result as your final answer."
        ),
        tools=[reverse_text],
        model=runtime.model,
        model_settings=runtime.model_settings,
    )

    print("\n[2/2] 调用 reverse_text 工具")
    streaming = await _run(agent_with_tool, "Reverse the string 'hello world'.")
    print(f"  → final_output: {streaming.final_output!r}")
    print("  → run items:")
    for item in streaming.new_items:
        print(f"    - {type(item).__name__}")


if __name__ == "__main__":
    asyncio.run(main())
