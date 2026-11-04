"""my_harness.py —— 最小骨架：循环 + 工具注册表 + 事件日志

照《用好AI》附录 Part 1 第五站"参考实现"（旧版 L338–390）落盘；**2026-10-10 试跑
发现原文参数解析一处 bug**：`eval(arg.strip().strip("'\""))` 对裸字符串参数
（如"北京"）先剥引号再 eval，必报 NameError（查天气场景跑不通）。本版做最小
修正：eval 失败时按裸字符串取值——只动取值一行，循环、注册表、日志结构与
附录一致。留档：run_log_正式.txt（站 5 第一轮 FAIL 记录＋修正后 PASS）。
"""

EVENTS = []
TOOLS = {}


def log(event_type: str, **payload):
    event = {"type": event_type, "seq": len(EVENTS), **payload}
    EVENTS.append(event)
    return event


def tool(fn):
    TOOLS[fn.__name__] = fn
    return fn


def run(task: str, model, max_steps: int = 5):
    log("turn/start", task=task)
    transcript = [f"任务：{task}"]

    for step in range(max_steps):
        log("step/start", step=step)
        reply = model(transcript, list(TOOLS))

        if reply.startswith("FINAL:"):
            answer = reply[6:].strip()
            log("step/final", answer=answer)
            log("turn/end", steps=step + 1)
            return answer

        if reply.startswith("CALL:"):
            body = reply[5:].strip()
            name = body.split("(")[0]
            if name not in TOOLS:
                result = {"ok": False, "error": f"没有这个工具：{name}"}
            else:
                try:
                    arg = body[len(name) + 1:body.rfind(")")]
                    raw = arg.strip()
                    try:
                        value = eval(raw, {"__builtins__": {}})
                    except (SyntaxError, NameError, ValueError):
                        value = raw.strip("'\"")   # 裸字符串参数（如"北京"）
                    result = {"ok": True, "value": TOOLS[name](value)}
                except Exception as e:
                    # 第三站的护栏：错误即消息
                    result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            log("tool/result", tool=name, result=result)
            transcript.append(f"调用 {name} → {result}")
            continue

        transcript.append(reply)

    log("turn/end", reason="达到步数上限")
    return "未完成"
