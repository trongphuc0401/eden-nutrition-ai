from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.auth_routes import require_user
from app.schemas.profile_schema import ProfileInput
from app.services.chat.models import FREE_CHAT_MODELS, default_chat_model, llm_chat_enabled, resolve_chat_model
from app.services.chat.service import run_turn
from app.services.chat.store import chat_store

router = APIRouter(prefix="/v1/chat", tags=["chat"])
CurrentUser = Depends(require_user)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    thread_id: str | None = Field(default=None, max_length=64)
    profile: ProfileInput | None = None
    selectedIngredientIds: list[str] = Field(default_factory=list, max_length=8)
    model: str | None = Field(default=None, max_length=64)


class CreateThreadRequest(BaseModel):
    title: str = Field(default="Đoạn chat mới", max_length=160)


class UpdateThreadRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    report_id: str | None = Field(default=None, max_length=64)


@router.get("/models")
def chat_models(user: dict = CurrentUser) -> dict:
    # `enabled` is false in template mode: answers then come from data only and the choice has no effect
    return {"models": FREE_CHAT_MODELS, "default": default_chat_model(), "enabled": llm_chat_enabled()}


@router.post("")
def chat(request: ChatRequest, user: dict = CurrentUser) -> StreamingResponse:
    profile = request.profile.model_dump() if request.profile else {}
    stream = run_turn(owner_id=user["id"], message=request.message.strip(), profile=profile,
                      thread_id=request.thread_id, selected_ids=request.selectedIngredientIds,
                      model=resolve_chat_model(request.model))
    return StreamingResponse(stream, media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/threads")
def list_threads(user: dict = CurrentUser) -> dict:
    return {"threads": chat_store.list_threads(user["id"])}


@router.post("/threads")
def create_thread(request: CreateThreadRequest | None = None, user: dict = CurrentUser) -> dict:
    title = request.title if request and request.title else "Đoạn chat mới"
    thread_id = chat_store.create_thread(user["id"], title)
    return {"thread_id": thread_id, "title": title}


@router.get("/threads/{thread_id}")
def thread_messages(thread_id: str, user: dict = CurrentUser) -> dict:
    # another user's thread reads as missing so ids cannot be probed
    if not chat_store.owns(thread_id, user["id"]):
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện")
    thread_data = chat_store.get_thread(thread_id, user["id"])
    return {
        "thread_id": thread_id,
        "title": thread_data.get("title") if thread_data else None,
        "report_id": thread_data.get("report_id") if thread_data else None,
        "messages": chat_store.history(thread_id),
    }


@router.delete("/threads/{thread_id}")
def delete_thread(thread_id: str, user: dict = CurrentUser) -> dict:
    if not chat_store.owns(thread_id, user["id"]):
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện")
    chat_store.delete_thread(thread_id, user["id"])
    return {"success": True, "thread_id": thread_id}


@router.patch("/threads/{thread_id}")
def update_thread(thread_id: str, request: UpdateThreadRequest, user: dict = CurrentUser) -> dict:
    if not chat_store.owns(thread_id, user["id"]):
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện")
    if request.title:
        chat_store.rename_thread(thread_id, user["id"], request.title)
    if request.report_id:
        chat_store.attach_report(thread_id, user["id"], request.report_id)
    return {"success": True, "thread_id": thread_id}

