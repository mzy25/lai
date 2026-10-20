#!/usr/bin/env python3
"""§16 六站 · 第二站（15 分钟 · 让它失败一下）

照《用好AI》附录 Part 1 第二站代码逐字照录（含两个检查点断言）。
运行：python3 station2.py（先 pip install smolagents）
"""
from smolagents import CodeAgent, tool
from mock_model import MockModel


@tool
def book_flight(destination: str, days: int) -> str:
    """Book a flight.

    Args:
        destination: Destination city.
        days: Number of days, must be between 1 and 30.
    """
    if not (1 <= days <= 30):
        raise ValueError(f"days={days} 越界，只允许 1-30")
    return f"已预订 {destination} {days} 天"


script = [
    "Thought: 直接下单\nCode:\n```py\nr = book_flight(destination='巴黎', days=999)\nprint(r)\n```",
    "Thought: 完成\nCode:\n```py\nfinal_answer('机票已订好')\n```",
]

agent = CodeAgent(tools=[book_flight], model=MockModel(script), max_steps=3)
out = agent.run("帮我订一张去巴黎的机票，999 天")
print("\n>>> 模型对外说：", out)

errors = [s for s in agent.memory.steps if getattr(s, "error", None)]
print(f"内部记录到 {len(errors)} 步失败")
assert len(errors) == 1        # ← 检查点：内部知道失败了
assert "999" not in str(out)   # ← 检查点：但对外一个字没提
print("CHECKPOINT PASS")
