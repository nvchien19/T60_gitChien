"""Chỉ dùng khi chạy dev bằng `npm run dev` (scripts/dev.mjs đặt DEV_PARENT_PID).

Trên Windows, worker uvicorn `--reload` là tiến trình multiprocessing riêng: khi trình khởi chạy bị kill đột ngột
(đóng cửa sổ, dừng tác vụ), worker không chết theo mà tiếp tục giữ cổng 8000 với mã cũ. Luồng này chờ tiến trình
cha kết thúc rồi thoát worker.
"""

import os
import sys
import threading
import time


def _wait_windows(pid: int) -> None:
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not handle:
        return  # không mở được (đã chết hoặc không có quyền): không đoán, để nguyên
    kernel32.WaitForSingleObject(handle, 0xFFFFFFFF)  # INFINITE
    os._exit(0)


def _wait_posix(pid: int) -> None:
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            os._exit(0)
        except PermissionError:
            pass
        time.sleep(2)


def start() -> None:
    try:
        pid = int(os.environ.get("DEV_PARENT_PID", ""))
    except ValueError:
        return
    target = _wait_windows if sys.platform == "win32" else _wait_posix
    threading.Thread(target=target, args=(pid,), name="dev-parent-watchdog", daemon=True).start()
