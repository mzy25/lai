#!/usr/bin/env python3
"""§16 六站 · 第五站（用 AI 搭骨架）——三轮验收

照《用好AI》附录 Part 1 第五站（旧版 L285–392）：三轮迭代（只要循环→加日志→
加护栏），骨架取附录参考实现 my_harness.py（照录），本节只写三轮题面与验收。
单参数版 book_flight 是为适配参考实现的参数解析（第五章附录的口径），
失败机制与第二站一致（days 越界 raise）。
运行：python3 station5.py（先 pip install smolagents）
"""
from my_harness import run, EVENTS, tool


def make_model(replies):
    """确定性脚本模型：按剧本逐条回复（同 mock_model.py 思路）。"""
    it = iter(replies)

    def model(transcript, tools):
        try:
            return next(it)
        except StopIteration:
            return "FINAL:（剧本用尽）"

    return model


@tool
def get_weather(city: str) -> str:
    """Get the weather for a city.

    Args:
        city: The name of the city.
    """
    return f"{city}: 晴 25°C"


@tool
def book_flight(days: int) -> str:
    """Book a flight.

    Args:
        days: Number of days, must be between 1 and 30.
    """
    if not (1 <= days <= 30):
        raise ValueError(f"days={days} 越界，只允许 1-30")
    return f"已预订 {days} 天"


def audit(events, final_answer):
    """对照事件日志检查：最终答复和发生过的事实一致吗？"""
    failures = [e for e in events
                if e["type"] == "tool/result" and not e["result"].get("ok")]
    if failures and "没订成" not in str(final_answer) and "未完成" not in str(final_answer):
        return f"不一致：{len(failures)} 步失败，但答复没提"
    if not failures:
        return "一致：全程无失败"
    return "一致：失败已如实反映"


# —— 第一轮：只要循环 ——
out1 = run("北京天气怎么样？",
           make_model(["CALL:get_weather(北京)", "FINAL:北京今天晴，25°C"]), max_steps=5)
print("第一轮 循环跑通：", out1)
assert "25°C" in out1, out1

# —— 第二轮：加日志 ——
calls = [e for e in EVENTS if e["type"] == "tool/result"]
print("第二轮 EVENTS 查到工具调用：", [(e["tool"], e["result"]) for e in calls])
assert calls and calls[0]["result"].get("ok") is True   # ← 检查点：每次调用及结果在账

# —— 第三轮：加护栏 ——
EVENTS.clear()
m3 = make_model(["CALL:book_flight(999)", "CALL:book_flight(999)", "FINAL:机票已订好"])
out3 = run("帮我订一张去巴黎的机票，999 天", m3, max_steps=5)
print("第三轮 模型对外说：", out3)
verdict = audit(EVENTS, out3)
print("第三轮 审计结论：", verdict)
assert "不一致" in verdict, verdict                  # ← 检查点：审计能查出不一致

print("CHECKPOINT PASS")
