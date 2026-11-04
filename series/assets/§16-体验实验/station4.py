#!/usr/bin/env python3
"""§16 六站 · 第四站（打开日志，学会事后审计）

照《用好AI》附录 Part 1 第四站代码逐字照录（含检查点断言）。
注意：本站在脚本内重跑第二站的"无护栏版"配置（附录 L252–256 要求）。
运行：python3 station4.py（先 pip install smolagents）
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


def audit(agent, final_answer):
    """对照日志检查：最终答复和发生过的事实一致吗？"""
    failures = [s for s in agent.memory.steps if getattr(s, "error", None)]
    if failures and "没订成" not in str(final_answer):
        return f"不一致：{len(failures)} 步失败，但答复没提"
    if not failures:
        return "一致：全程无失败"
    return "一致：失败已如实反映"


# 重跑第二站的"无护栏版"（附录 L252–256）
script = [
    "Thought: 直接下单\nCode:\n```py\nr = book_flight(destination='巴黎', days=999)\nprint(r)\n```",
    "Thought: 完成\nCode:\n```py\nfinal_answer('机票已订好')\n```",
]
agent = CodeAgent(tools=[book_flight], model=MockModel(script), max_steps=3)
out = agent.run("帮我订一张去巴黎的机票，999 天")
print("\n>>> 模型对外说：", out)
print("审计结论：", audit(agent, out))

assert "不一致" in audit(agent, out)   # ← 检查点：抓出来了
print("CHECKPOINT PASS")
