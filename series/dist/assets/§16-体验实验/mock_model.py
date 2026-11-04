# mock_model.py
# 摘自《用好AI》附录「动手路径与九条原则」准备节（书内 2026-10 版），逐字照录。
from smolagents.models import ChatMessage, Model


class MockModel(Model):
    """确定性假模型：按脚本逐句回复，不需要 API key。"""

    def __init__(self, replies):
        super().__init__()
        self.replies = list(replies)
        self.calls = 0

    def generate(self, messages, stop_sequences=None,
                 response_format=None, tools_to_call_from=None, **kwargs):
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return ChatMessage(role="assistant", content=reply)
