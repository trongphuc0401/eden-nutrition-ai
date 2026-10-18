"""Chat threads and messages: Supabase (chat_threads / chat_messages) with an in-memory fallback.

The fallback keeps the chat usable when the database is down or persistence is disabled (tests); it is per-process.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

logger = logging.getLogger(__name__)


class ChatStore:
    def __init__(self) -> None:
        self._threads: dict[str, dict[str, Any]] = {}
        self._messages: dict[str, list[dict[str, Any]]] = {}
        self._lock = Lock()
        self._db_ok = True

    # ------------------------------------------------------------------ helpers
    def _use_db(self) -> bool:
        return settings.chat_persistence_enabled and self._db_ok

    def _db_failed(self, error: Exception) -> None:
        logger.warning("Chat persistence unavailable, using memory: %s", type(error).__name__)
        self._db_ok = False

    # ------------------------------------------------------------------ threads
    def create_thread(self, owner_id: str, title: str) -> str:
        title = (title.strip() or "Cuộc trò chuyện mới")[:160]
        if self._use_db():
            try:
                from app.database import engine

                with engine.begin() as conn:
                    return str(conn.execute(text(
                        "INSERT INTO chat_threads (owner_id, title) VALUES (:o, :t) RETURNING id"), {"o": owner_id, "t": title}).scalar_one())
            except SQLAlchemyError as error:
                self._db_failed(error)
        thread_id = str(uuid.uuid4())
        with self._lock:
            self._threads[thread_id] = {"id": thread_id, "owner_id": owner_id, "title": title}
            self._messages[thread_id] = []
        return thread_id

    def owns(self, thread_id: str, owner_id: str) -> bool:
        with self._lock:
            if thread_id in self._threads:
                return self._threads[thread_id]["owner_id"] == owner_id
        if self._use_db():
            try:
                uuid.UUID(thread_id)
                from app.database import engine

                with engine.connect() as conn:
                    return bool(conn.execute(text("SELECT 1 FROM chat_threads WHERE id = CAST(:i AS uuid) AND owner_id = :o"),
                                             {"i": thread_id, "o": owner_id}).scalar())
            except ValueError:
                return False
            except SQLAlchemyError as error:
                self._db_failed(error)
        return False

    # ------------------------------------------------------------------ messages
    def append(self, thread_id: str, role: str, content: str, intent: str | None = None,
               metadata: dict[str, Any] | None = None) -> int | None:
        metadata = metadata or {}
        with self._lock:
            if thread_id in self._messages:
                message_id = sum(len(items) for items in self._messages.values()) + 1
                self._messages[thread_id].append({
                    "id": message_id, "role": role, "content": content, "intent": intent, "metadata": metadata,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                return message_id
        if self._use_db():
            try:
                from app.database import engine

                with engine.begin() as conn:
                    message_id = conn.execute(text("""
                        INSERT INTO chat_messages (thread_id, role, content, intent, metadata)
                        VALUES (CAST(:t AS uuid), :r, :c, :i, CAST(:m AS jsonb)) RETURNING id"""),
                        {"t": thread_id, "r": role, "c": content, "i": intent,
                         "m": json.dumps(metadata, ensure_ascii=False, default=str)}).scalar_one()
                    conn.execute(text("UPDATE chat_threads SET updated_at = NOW() WHERE id = CAST(:t AS uuid)"), {"t": thread_id})
                    return int(message_id)
            except SQLAlchemyError as error:
                self._db_failed(error)
        return None

    def history(self, thread_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        limit = limit or 200
        with self._lock:
            if thread_id in self._messages:
                return [dict(item) for item in self._messages[thread_id][-limit:]]
        if self._use_db():
            try:
                from app.database import engine

                with engine.connect() as conn:
                    rows = conn.execute(text("""
                        SELECT id, role, content, intent, metadata, created_at FROM (
                            SELECT * FROM chat_messages WHERE thread_id = CAST(:t AS uuid) ORDER BY id DESC LIMIT :n
                        ) recent ORDER BY id"""), {"t": thread_id, "n": limit}).mappings().all()
                return [{**dict(row), "created_at": row["created_at"].isoformat()} for row in rows]
            except SQLAlchemyError as error:
                self._db_failed(error)
        return []


    def list_threads(self, owner_id: str, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        if self._use_db():
            try:
                from app.database import engine

                with engine.connect() as conn:
                    rows = conn.execute(text("""
                        SELECT 
                            t.id, 
                            t.title, 
                            t.report_id,
                            t.created_at, 
                            t.updated_at,
                            COUNT(m.id) AS message_count,
                            (
                                SELECT content 
                                FROM chat_messages 
                                WHERE thread_id = t.id 
                                ORDER BY id DESC 
                                LIMIT 1
                            ) AS last_message
                        FROM chat_threads t
                        LEFT JOIN chat_messages m ON m.thread_id = t.id
                        WHERE t.owner_id = :o
                        GROUP BY t.id
                        ORDER BY t.updated_at DESC
                        LIMIT :limit
                    """), {"o": owner_id, "limit": limit}).mappings().all()
                return [{
                    "id": str(row["id"]),
                    "title": row["title"],
                    "report_id": row["report_id"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    "message_count": int(row["message_count"] or 0),
                    "last_message": row["last_message"][:100] if row["last_message"] else None,
                } for row in rows]
            except SQLAlchemyError as error:
                self._db_failed(error)
        with self._lock:
            results = []
            for tid, tdata in self._threads.items():
                if tdata.get("owner_id") == owner_id:
                    msgs = self._messages.get(tid, [])
                    results.append({
                        "id": tid,
                        "title": tdata.get("title", "Cuộc trò chuyện mới"),
                        "report_id": tdata.get("report_id"),
                        "created_at": None,
                        "updated_at": None,
                        "message_count": len(msgs),
                        "last_message": msgs[-1]["content"][:100] if msgs else None,
                    })
            return results[:limit]

    def get_thread(self, thread_id: str, owner_id: str) -> dict[str, Any] | None:
        if self._use_db():
            try:
                uuid.UUID(thread_id)
                from app.database import engine

                with engine.connect() as conn:
                    row = conn.execute(text("""
                        SELECT id, title, report_id, created_at, updated_at
                        FROM chat_threads
                        WHERE id = CAST(:i AS uuid) AND owner_id = :o
                    """), {"i": thread_id, "o": owner_id}).mappings().first()
                    if row:
                        return {
                            "id": str(row["id"]),
                            "title": row["title"],
                            "report_id": row["report_id"],
                            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                        }
            except (ValueError, SQLAlchemyError) as error:
                self._db_failed(error)
        with self._lock:
            t = self._threads.get(thread_id)
            if t and t.get("owner_id") == owner_id:
                return dict(t)
        return None

    def delete_thread(self, thread_id: str, owner_id: str) -> bool:
        with self._lock:
            self._threads.pop(thread_id, None)
            self._messages.pop(thread_id, None)
        if self._use_db():
            try:
                uuid.UUID(thread_id)
                from app.database import engine

                with engine.begin() as conn:
                    res = conn.execute(text(
                        "DELETE FROM chat_threads WHERE id = CAST(:t AS uuid) AND owner_id = :o"),
                        {"t": thread_id, "o": owner_id})
                    return bool(res.rowcount > 0)
            except (ValueError, SQLAlchemyError) as error:
                self._db_failed(error)
        return True

    def rename_thread(self, thread_id: str, owner_id: str, title: str) -> bool:
        clean_title = (title.strip() or "Cuộc trò chuyện mới")[:160]
        with self._lock:
            if thread_id in self._threads and self._threads[thread_id].get("owner_id") == owner_id:
                self._threads[thread_id]["title"] = clean_title
        if self._use_db():
            try:
                uuid.UUID(thread_id)
                from app.database import engine

                with engine.begin() as conn:
                    res = conn.execute(text(
                        "UPDATE chat_threads SET title = :t, updated_at = NOW() WHERE id = CAST(:i AS uuid) AND owner_id = :o"),
                        {"t": clean_title, "i": thread_id, "o": owner_id})
                    return bool(res.rowcount > 0)
            except (ValueError, SQLAlchemyError) as error:
                self._db_failed(error)
        return True

    def attach_report(self, thread_id: str, owner_id: str, report_id: str) -> bool:
        with self._lock:
            if thread_id in self._threads and self._threads[thread_id].get("owner_id") == owner_id:
                self._threads[thread_id]["report_id"] = report_id
        if self._use_db():
            try:
                uuid.UUID(thread_id)
                from app.database import engine

                with engine.begin() as conn:
                    res = conn.execute(text(
                        "UPDATE chat_threads SET report_id = :r, updated_at = NOW() WHERE id = CAST(:i AS uuid) AND owner_id = :o"),
                        {"r": report_id, "i": thread_id, "o": owner_id})
                    return bool(res.rowcount > 0)
            except (ValueError, SQLAlchemyError) as error:
                self._db_failed(error)
        return True

    def update_title_if_default(self, thread_id: str, owner_id: str, new_title: str) -> None:
        clean_title = (new_title.strip() or "Cuộc trò chuyện mới")[:160]
        with self._lock:
            t = self._threads.get(thread_id)
            if t and t.get("owner_id") == owner_id and t.get("title") in ("Cuộc trò chuyện mới", "Đoạn chat mới", "Phiên chat mới"):
                t["title"] = clean_title
        if self._use_db():
            try:
                uuid.UUID(thread_id)
                from app.database import engine

                with engine.begin() as conn:
                    conn.execute(text("""
                        UPDATE chat_threads 
                        SET title = :t, updated_at = NOW() 
                        WHERE id = CAST(:t_id AS uuid) 
                          AND owner_id = :o 
                          AND title IN ('Cuộc trò chuyện mới', 'Đoạn chat mới', 'Phiên chat mới')
                    """), {"t": clean_title, "t_id": thread_id, "o": owner_id})
            except Exception:
                pass


chat_store = ChatStore()
