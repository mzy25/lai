#!/usr/bin/env python3
"""§16 六站 · 第一站（10 分钟 · 让它跑起来）

照《用好AI》附录 Part 1 第一站代码逐字照录（含检查点断言）。
运行：python3 station1.py（先 pip install smolagents）
"""
from smolagents import CodeAgent, tool
from mock_model import MockModel


@tool
def get_weather(city: str) -> str:
    """Get the weather for a city.

    Args:
        city: The name of the city.
    """
    return f"{city}: 晴 25°C"


script = [
    "Thought: 我需要查天气\nCode:\n```py\nr = get_weather(city='北京')\nprint(r)\n```",
    "Thought: 拿到了结果\nCode:\n```py\nfinal_answer('北京今天晴，25°C')\n```",
]

agent = CodeAgent(tools=[get_weather], model=MockModel(script), max_steps=3)
out = agent.run("北京天气怎么样？")
print(out)

assert "25°C" in str(out), out          # ← 检查点：真的跑通了
print("CHECKPOINT PASS")
