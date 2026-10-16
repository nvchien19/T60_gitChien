"""Giới hạn số lần gọi theo tài khoản cho các API gọi LLM (tốn tiền, có thể bị lạm dụng).

Bộ đếm nằm trong bộ nhớ của từng tiến trình: chạy nhiều worker thì mỗi worker đếm riêng, khi đó cần
thêm giới hạn ở gateway. Không lưu nội dung yêu cầu, chỉ lưu thời điểm gọi.
"""

import time
from collections import deque

from fastapi import Depends, HTTPException

from interface.backend.db.models.tables import User
from interface.backend.services.auth_service import current_user

_MAX_KEYS = 5000


class PerUserLimit:
    def __init__(self, name: str, limit: int, window: float = 60.0):
        self.name, self.limit, self.window = name, limit, window
        self.calls: dict[int, deque] = {}

    def hit(self, user_id: int, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        cutoff = now - self.window
        if len(self.calls) >= _MAX_KEYS:
            for key in [k for k, v in self.calls.items() if not v or v[-1] <= cutoff]:
                del self.calls[key]
        calls = self.calls.setdefault(user_id, deque())
        while calls and calls[0] <= cutoff:
            calls.popleft()
        if len(calls) >= self.limit:
            retry = max(1, int(calls[0] + self.window - now) + 1)
            raise HTTPException(
                429,
                f"Tối đa {self.limit} lần {self.name} mỗi {int(self.window)} giây. Vui lòng thử lại sau.",
                headers={"Retry-After": str(retry)},
            )
        calls.append(now)

    async def __call__(self, user: User = Depends(current_user)) -> None:
        self.hit(user.id)


chat_limit = PerUserLimit("hỏi trợ lý", limit=20)
explain_limit = PerUserLimit("giải thích", limit=30)
