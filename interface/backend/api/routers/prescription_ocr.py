import json
import time
from collections import deque

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from interface.backend.schemas.prescription_ocr import OcrImageRequest, OcrResponse
from interface.backend.services.auth_service import current_user
from interface.backend.services.prescription_ocr import recognize_prescription

router = APIRouter(tags=['prescription-ocr'])
# Per-process bound: up to five calls/minute/account, no payload storage.
_calls: dict[int, deque] = {}


@router.post('/prescription-ocr', response_model=OcrResponse)
async def prescription_ocr(request: Request, user=Depends(current_user)):
    now = time.monotonic()
    for key in list(_calls):
        if not _calls[key] or _calls[key][-1] <= now - 60:
            del _calls[key]
    calls = _calls.setdefault(user.id, deque())
    while calls and calls[0] <= now - 60:
        calls.popleft()
    if len(calls) >= 5:
        raise HTTPException(429, 'Tối đa 5 lần OCR mỗi phút. Vui lòng thử lại sau.', headers={'Retry-After': '60'})
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        raise HTTPException(415, 'OCR yêu cầu JSON chứa ảnh.')
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 5700000:
            raise HTTPException(413, 'Ảnh OCR quá lớn. Chọn vùng thuốc nhỏ hơn.')
    try:
        req = OcrImageRequest.model_validate(json.loads(body))
    except (ValueError, ValidationError):
        raise HTTPException(422, 'Yêu cầu OCR không hợp lệ; chỉ nhận ảnh PNG, JPG hoặc WebP.') from None
    calls.append(now)
    return await recognize_prescription(req)
