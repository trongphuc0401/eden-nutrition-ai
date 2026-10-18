from __future__ import annotations

import threading
import uuid
import json
import queue
import socket
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.agents.report_graph import report_graph
from app.config import settings
from app.database import SessionLocal
from app.schemas.report_schema import ReportConfirmationRequest, ReportEvent, ReportRequest


NODE_MESSAGES = {
    "validate_request": "Đang kiểm tra yêu cầu và nguyên liệu đã chọn",
    "analyze_profile": "Đang phân tích hồ sơ và mục tiêu",
    "retrieve_ingredient_data": "Đang truy xuất dữ liệu dinh dưỡng có nguồn",
    "generate_recipe": "Đang tạo công thức từ nguyên liệu đã chọn",
    "calculate_nutrition": "Đang tính dinh dưỡng theo định lượng",
    "safety_and_quality_gate": "Đang kiểm tra an toàn và ngưỡng",
    "compose_report": "Đang biên soạn report",
    "compose_report_with_warning": "Đang biên soạn report kèm cảnh báo",
    "render_pdf": "Đang dựng PDF A4 hai trang",
    "finalize": "Report đã hoàn tất",
    "finalize_error": "Yêu cầu bị từ chối bởi kiểm tra an toàn",
}
TERMINAL = {"completed", "review", "rejected", "failed", "cancelled"}


class ReportJobService:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._idempotency: dict[str, str] = {}
        self._lock = threading.RLock()
        self._queue: queue.Queue[str] = queue.Queue()
        self._worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self._worker = threading.Thread(target=self._work, name="report-worker", daemon=True)
        self._restore_jobs()
        self._worker.start()

    def create(self, request: ReportRequest, idempotency_key: str | None = None) -> dict[str, Any]:
        if idempotency_key:
            with self._lock:
                existing = self._idempotency.get(idempotency_key)
                if existing and existing in self._jobs:
                    if self._jobs[existing]["request"] != request.model_dump(by_alias=True, mode="json"):
                        raise ValueError("Idempotency-Key đã được dùng cho một yêu cầu khác.")
                    return self.snapshot(existing)
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        job = {
            "report_id": report_id,
            "thread_id": f"thread_{uuid.uuid4().hex}",
            "run_id": f"run_{uuid.uuid4().hex}",
            "status": "queued",
            "current_node": None,
            "request": request.model_dump(by_alias=True, mode="json"),
            "events": [],
            "state": {},
            "error": None,
            "cancel_requested": False,
            "idempotency_key": idempotency_key,
            "updated_at": now,
        }
        with self._lock:
            self._jobs[report_id] = job
            if idempotency_key:
                self._idempotency[idempotency_key] = report_id
            self._event(job, "queued", "queued", "Đã tiếp nhận yêu cầu tạo report")
            self._persist(job)
        self._queue.put(report_id)
        return self.snapshot(report_id)

    def _work(self) -> None:
        while True:
            report_id = self._queue.get()
            try:
                self.run(report_id)
            finally:
                self._queue.task_done()

    @staticmethod
    def _jsonable(value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))

    def _persist(self, job: dict[str, Any]) -> None:
        if not settings.report_job_persistence_enabled:
            return
        payload = self._jsonable(job)
        try:
            with SessionLocal.begin() as db:
                db.execute(
                    text(
                        """
                        INSERT INTO report_jobs (report_id, idempotency_key, status, payload, updated_at)
                        VALUES (:report_id, :idempotency_key, :status, CAST(:payload AS JSONB), NOW())
                        ON CONFLICT (report_id) DO UPDATE SET
                          status = EXCLUDED.status,
                          payload = EXCLUDED.payload,
                          updated_at = NOW()
                        """
                    ),
                    {
                        "report_id": job["report_id"],
                        "idempotency_key": job.get("idempotency_key"),
                        "status": job["status"],
                        "payload": json.dumps(payload, ensure_ascii=False),
                    },
                )
        except SQLAlchemyError as error:
            raise RuntimeError("Không thể lưu report job vào PostgreSQL.") from error

    def _restore_jobs(self) -> None:
        if not settings.report_job_persistence_enabled:
            return
        try:
            with SessionLocal() as db:
                rows = db.execute(text("SELECT payload FROM report_jobs ORDER BY updated_at DESC LIMIT 500")).scalars()
                for payload in rows:
                    job = payload if isinstance(payload, dict) else json.loads(payload)
                    self._jobs[job["report_id"]] = job
                    if job.get("idempotency_key"):
                        self._idempotency[job["idempotency_key"]] = job["report_id"]
                    if job["status"] in {"queued", "running"}:
                        job["status"] = "queued"
                        self._queue.put(job["report_id"])
        except SQLAlchemyError as error:
            raise RuntimeError("REPORT_JOB_PERSISTENCE_ENABLED=true nhưng bảng report_jobs chưa sẵn sàng.") from error

    def _claim_job(self, report_id: str) -> bool:
        if not settings.report_job_persistence_enabled:
            return True
        try:
            with SessionLocal.begin() as db:
                claimed = db.execute(
                    text(
                        """
                        UPDATE report_jobs
                        SET lease_owner = :owner,
                            lease_expires_at = NOW() + INTERVAL '4 minutes'
                        WHERE report_id = :report_id
                          AND (lease_owner IS NULL OR lease_expires_at < NOW() OR lease_owner = :owner)
                        RETURNING report_id
                        """
                    ),
                    {"owner": self._worker_id, "report_id": report_id},
                ).scalar_one_or_none()
            return claimed is not None
        except SQLAlchemyError as error:
            raise RuntimeError("Không thể claim report job từ PostgreSQL.") from error

    def _release_job(self, report_id: str) -> None:
        if not settings.report_job_persistence_enabled:
            return
        try:
            with SessionLocal.begin() as db:
                db.execute(
                    text(
                        "UPDATE report_jobs SET lease_owner = NULL, lease_expires_at = NULL "
                        "WHERE report_id = :report_id AND lease_owner = :owner"
                    ),
                    {"owner": self._worker_id, "report_id": report_id},
                )
        except SQLAlchemyError:
            return

    def _event(self, job: dict[str, Any], node: str, status: str, message: str) -> None:
        event = ReportEvent(
            sequence=len(job["events"]) + 1,
            node=node,
            status=status,
            message=message,
        )
        job["events"].append(event.model_dump(mode="json"))
        job["updated_at"] = datetime.now(timezone.utc)

    def run(self, report_id: str) -> None:
        if not self._claim_job(report_id):
            return
        with self._lock:
            job = self._jobs[report_id]
            job["status"] = "running"
            self._event(job, "start", "running", "Bắt đầu workflow LangGraph")
            self._persist(job)
            initial = {
                "request": job["request"],
                "report_id": job["report_id"],
                "thread_id": job["thread_id"],
                "run_id": job["run_id"],
                "errors": [],
                "warnings": [],
                "retry_count": 0,
                "execution_metadata": {},
            }
            config = {"configurable": {"thread_id": job["thread_id"]}, "run_id": job["run_id"]}
        aggregate = dict(initial)
        try:
            for update in report_graph.stream(initial, config=config, stream_mode="updates"):
                with self._lock:
                    job = self._jobs[report_id]
                    if job["cancel_requested"]:
                        job["status"] = "cancelled"
                        self._event(job, "cancelled", "cancelled", "Đã dừng workflow theo yêu cầu")
                        self._persist(job)
                        self._release_job(report_id)
                        return
                    for node, values in update.items():
                        if isinstance(values, dict):
                            aggregate.update(values)
                        job["current_node"] = node
                        job["state"] = dict(aggregate)
                        self._event(job, node, "running", NODE_MESSAGES.get(node, node))
                        self._persist(job)
            with self._lock:
                job = self._jobs[report_id]
                decision = aggregate.get("decision")
                if aggregate.get("confirmation_required"):
                    job["status"] = "awaiting_confirmation"
                elif decision == "reject":
                    job["status"] = "rejected"
                elif decision == "review":
                    job["status"] = "review"
                else:
                    job["status"] = "completed"
                job["state"] = aggregate
                self._event(job, "done", job["status"], "Workflow đã kết thúc")
                self._persist(job)
                self._release_job(report_id)
        except Exception as exc:  # The API must expose failure instead of losing a background exception.
            with self._lock:
                job = self._jobs[report_id]
                job["status"] = "failed"
                job["error"] = f"{type(exc).__name__}: {exc}"
                self._event(job, "failed", "failed", "Không thể tạo report")
                self._persist(job)
                self._release_job(report_id)

    def confirm(self, report_id: str, confirmation: ReportConfirmationRequest) -> dict[str, Any]:
        with self._lock:
            job = self._jobs[report_id]
            if job["status"] != "awaiting_confirmation":
                raise ValueError("Report hiện không chờ xác nhận.")
            proposal = job.get("state", {}).get("recipe_proposal") or {}
            if proposal.get("version") != confirmation.proposal_version:
                raise ValueError("Phiên bản đề xuất đã thay đổi; hãy tải lại report.")
            suggested = set(proposal.get("suggested_ingredient_ids") or [])
            accepted = set(confirmation.accepted_ingredient_ids)
            if not accepted.issubset(suggested):
                raise ValueError("Danh sách xác nhận chứa nguyên liệu không thuộc đề xuất.")
            rejected = suggested - accepted
            request = dict(job["request"])
            request["ingredientIds"] = list(dict.fromkeys([*(request.get("ingredientIds") or []), *accepted]))
            request["confirmedIngredientIds"] = sorted(accepted)
            request["rejectedIngredientIds"] = sorted(rejected)
            request["allowSuggestions"] = False
            job["request"] = request
            job["status"] = "queued"
            job["current_node"] = None
            job["state"] = {}
            job["error"] = None
            job["cancel_requested"] = False
            self._event(job, "confirmation", "queued", "Đã ghi nhận lựa chọn nguyên liệu và xếp lại workflow")
            self._persist(job)
        self._queue.put(report_id)
        return self.snapshot(report_id)

    def cancel(self, report_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs[report_id]
            if job["status"] == "awaiting_confirmation":
                job["status"] = "cancelled"
                job["cancel_requested"] = True
                self._event(job, "cancelled", "cancelled", "Đã hủy đề xuất đang chờ xác nhận")
                self._persist(job)
            elif job["status"] not in TERMINAL:
                job["cancel_requested"] = True
                self._event(job, "cancel_requested", "running", "Đã gửi yêu cầu dừng workflow")
                self._persist(job)
        return self.snapshot(report_id)

    def exists(self, report_id: str) -> bool:
        with self._lock:
            return report_id in self._jobs

    def snapshot(self, report_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs[report_id]
            state = job.get("state", {})
            document = state.get("report_document")
            pdf = state.get("pdf_metadata") or {}
            errors = state.get("errors") or []
            warnings = state.get("warnings") or []
            return {
                "report_id": job["report_id"],
                "thread_id": job["thread_id"],
                "run_id": job["run_id"],
                "status": job["status"],
                "current_node": job["current_node"],
                "summary": document.get("summary") if document else None,
                "warning": " ".join(warnings) if warnings else None,
                "error": job.get("error") or (" ".join(errors) if errors else None),
                "decision": state.get("decision"),
                "report": document,
                "pdf_url": f"/v1/reports/{report_id}/pdf" if pdf.get("path") else None,
                "pdf_path": pdf.get("path"),
                "proposal": state.get("recipe_proposal"),
                "confirmation_required": bool(state.get("confirmation_required")),
                "quality_metadata": {
                    key: state.get("execution_metadata", {}).get(key)
                    for key in ("ai_provider", "ai_model", "prompt_version", "repair_count", "model_usage")
                    if state.get("execution_metadata", {}).get(key) is not None
                },
                "updated_at": job["updated_at"],
            }

    def events_after(self, report_id: str, sequence: int) -> tuple[list[dict[str, Any]], str]:
        with self._lock:
            job = self._jobs[report_id]
            return [event for event in job["events"] if event["sequence"] > sequence], job["status"]


report_job_service = ReportJobService()
