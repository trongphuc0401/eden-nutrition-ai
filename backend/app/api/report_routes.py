from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from app.api.auth_routes import require_user
from app.schemas.report_schema import ReportConfirmationRequest, ReportCreatedResponse, ReportRequest, ReportStatusResponse
from app.services.report_job_service import TERMINAL, RateLimitError, report_job_service


router = APIRouter(prefix="/v1/reports", tags=["reports"])
CurrentUser = Depends(require_user)


def _require(report_id: str, user: dict) -> dict:
    # Another user's report is reported as missing so IDs cannot be probed.
    if not report_job_service.exists(report_id) or report_job_service.owner_id(report_id) != user["id"]:
        raise HTTPException(status_code=404, detail="Không tìm thấy report")
    return report_job_service.snapshot(report_id)


@router.post("", response_model=ReportCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
def create_report(
    request: ReportRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: dict = CurrentUser,
) -> dict:
    try:
        return report_job_service.create(request, idempotency_key=idempotency_key, owner_id=user["id"])
    except RateLimitError as error:
        raise HTTPException(status_code=429, detail={"code": "rate_limited", "message": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail={"code": "idempotency_conflict", "message": str(error)}) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail={"code": "persistence_unavailable", "message": str(error)}) from error


@router.get("/{report_id}", response_model=ReportStatusResponse)
def get_report(report_id: str, user: dict = CurrentUser) -> dict:
    return _require(report_id, user)


@router.post("/{report_id}/cancel", response_model=ReportStatusResponse)
def cancel_report(report_id: str, user: dict = CurrentUser) -> dict:
    _require(report_id, user)
    return report_job_service.cancel(report_id)


@router.post("/{report_id}/confirmation", response_model=ReportStatusResponse)
def confirm_report(report_id: str, confirmation: ReportConfirmationRequest, user: dict = CurrentUser) -> dict:
    _require(report_id, user)
    try:
        return report_job_service.confirm(report_id, confirmation)
    except ValueError as error:
        raise HTTPException(status_code=409, detail={"code": "confirmation_conflict", "message": str(error)}) from error


@router.get("/{report_id}/events")
async def report_events(report_id: str, after: int = 0, user: dict = CurrentUser) -> StreamingResponse:
    _require(report_id, user)

    async def stream():
        sequence = max(after, 0)
        while True:
            events, current_status = report_job_service.events_after(report_id, sequence)
            for event in events:
                sequence = event["sequence"]
                yield f"id: {sequence}\nevent: report\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            if current_status in TERMINAL or current_status == "awaiting_confirmation":
                yield f"event: close\ndata: {json.dumps({'status': current_status})}\n\n"
                break
            await asyncio.sleep(0.35)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.get("/{report_id}/pdf")
def download_pdf(report_id: str, user: dict = CurrentUser) -> FileResponse:
    job = _require(report_id, user)
    if job["status"] not in {"completed", "review"} or not job.get("pdf_path"):
        raise HTTPException(status_code=409, detail="PDF chưa sẵn sàng")
    path = Path(job["pdf_path"])
    if not path.exists():
        raise HTTPException(status_code=410, detail="File PDF không còn tồn tại")
    return FileResponse(path, media_type="application/pdf", filename=f"{report_id}.pdf")
