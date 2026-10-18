"""Progress events for streaming LLM endpoints: fixed stage codes only, never question or model content.

Answers stay fail-closed: text is sent only once, after citation checks and verification, so the
stream carries which step is running instead of unverified model tokens.
"""
import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextvars import ContextVar

from fastapi import HTTPException
from pydantic import BaseModel

STAGES = {
    # Trợ lý chat
    "routing": "Đang xác định câu hỏi",
    "context": "Đang đọc kết quả kiểm tra đã lưu",
    "label_lookup": "Đang tra cứu nhãn thuốc",
    "composing": "Đang soạn câu trả lời từ bằng chứng",
    "revising": "Đang soạn lại cho đúng câu hỏi",
    # Giải thích một cặp tương tác
    "lookup": "Đang tra bản ghi tương tác trong CSDL",
    "explaining": "Đang diễn giải bản ghi bằng tiếng Việt",
    "rewriting": "Đang viết lại các câu chưa bám nguồn",
    # Dùng chung
    "verifying": "Đang đối chiếu từng câu với nguồn",
}

active_progress: ContextVar[Callable[[str], None] | None] = ContextVar("progress", default=None)


def report(stage: str) -> None:
    callback = active_progress.get()
    if callback is not None and stage in STAGES:
        callback(stage)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def progress_events(work: Callable[[], Awaitable[BaseModel]]) -> AsyncIterator[str]:
    """Server-Sent Events: `stage` while `work` runs, then one `done` (its result) or `error`."""
    queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

    async def run() -> None:
        active_progress.set(lambda stage: queue.put_nowait(("stage", {"stage": stage, "label": STAGES[stage]})))
        try:
            queue.put_nowait(("done", (await work()).model_dump(mode="json")))
        except HTTPException as error:
            queue.put_nowait(("error", {"status": error.status_code, "detail": error.detail}))
        except Exception:
            # Fixed message only: exception text may contain query or provider content.
            queue.put_nowait(("error", {"status": 500, "detail": "Hệ thống gặp lỗi. Vui lòng thử lại."}))

    task = asyncio.create_task(run())
    try:
        yield ": ok\n\n"  # Flush headers so the client can show progress immediately.
        while True:
            event, data = await queue.get()
            yield sse(event, data)
            if event != "stage":
                return
    finally:
        if not task.done():
            task.cancel()  # Client left: stop paying for provider calls nobody will read.
