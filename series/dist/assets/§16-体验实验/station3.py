#!/usr/bin/env python3
"""§16 六站 · 第三站（20 分钟 · 让报错回到模型那里）

照《用好AI》附录 Part 1 第三站代码逐字照录（含检查点断言）。
运行：python3 station3.py（先 pip install smolagents）
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
    # ── 改的就是这 4 行 ──
    if not (1 <= days <= 30):
        return {"ok": False, "error": f"days={days} 越界，只允许 1-30",
                "hint": "先跟用户确认正确的天数"}
    # ── 改动结束 ──
    return {"ok": True, "booking": f"{destination} {days} 天"}


script = [
    "Thought: 直接下单\nCode:\n```py\nr = book_flight(destination='巴黎', days=999)\nprint(r)\n```",
    "Thought: 工具说参数越界，我不能假装成功\nCode:\n```py\nfinal_answer('没订成：天数 999 超出允许范围（1-30），请确认天数')\n```",
]

agent = CodeAgent(tools=[book_flight], model=MockModel(script), max_steps=3)
out = agent.run("帮我订一张去巴黎的机票，999 天")
print("\n>>> 改后模型说：", out)

assert "999" in str(out)   # ← 检查点：它如实说了
print("CHECKPOINT PASS")
