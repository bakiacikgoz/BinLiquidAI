from __future__ import annotations

import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import uuid4

from .models import Preference, ProductLink, ProductMessage, ProductTask, Project, ProjectPage
from .store import ProductWorkspaceStore


def _now() -> datetime:
    return datetime.now(UTC)


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


class ProductWorkspaceService:
    def __init__(self, store: ProductWorkspaceStore) -> None:
        self.store = store

    @staticmethod
    def _payload_json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _replay_mutation(
        self,
        db: Any,
        workspace_id: str,
        method: str,
        payload: dict[str, Any],
        idempotency_key: str | None,
    ) -> dict[str, Any] | None:
        if idempotency_key is None:
            return None
        payload_json = self._payload_json(payload)
        row = db.execute(
            """SELECT method, payload_json, response_json FROM product_mutation_dedup
            WHERE workspace_id=? AND idempotency_key=?""",
            (workspace_id, idempotency_key),
        ).fetchone()
        if row is None:
            return None
        if row["method"] != method or row["payload_json"] != payload_json:
            raise ValueError("idempotency key was reused with a different product mutation")
        return json.loads(row["response_json"])

    @staticmethod
    def _remember_mutation(
        db: Any,
        workspace_id: str,
        method: str,
        payload: dict[str, Any],
        idempotency_key: str | None,
        response: Project | ProductTask | ProductMessage | ProductLink | Preference,
    ) -> None:
        if idempotency_key is None:
            return
        db.execute(
            """INSERT INTO product_mutation_dedup
            (workspace_id,idempotency_key,method,payload_json,response_json,created_at_utc)
            VALUES (?,?,?,?,?,?)""",
            (
                workspace_id,
                idempotency_key,
                method,
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
                response.model_dump_json(by_alias=True),
                _now().isoformat(),
            ),
        )

    @staticmethod
    def _project_from_row(row: Any) -> Project:
        return Project(
            projectId=row["project_id"],
            workspaceId=row["workspace_id"],
            title=row["title"],
            rootRef=row["root_ref"],
            rootDisplayName=row["root_display_name"],
            status=row["status"],
            pinned=bool(row["pinned"]),
            manualOrder=row["manual_order"],
            createdAtUtc=row["created_at_utc"],
            updatedAtUtc=row["updated_at_utc"],
            archivedAtUtc=row["archived_at_utc"],
        )

    @staticmethod
    def _encode_cursor(offset: int) -> str:
        return urlsafe_b64encode(str(offset).encode("ascii")).decode("ascii")

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            decoded = urlsafe_b64decode(cursor.encode("ascii")).decode("ascii")
            offset = int(decoded)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("project cursor is invalid") from exc
        if offset < 0:
            raise ValueError("project cursor is invalid")
        return offset

    def create_project(
        self, workspace_id: str, title: str, idempotency_key: str | None = None
    ) -> Project:
        now = _now()
        payload = {"title": title}
        project = Project(
            projectId=_id("project"),
            workspaceId=workspace_id,
            title=title,
            rootRef=_id("root"),
            rootDisplayName=title,
            createdAtUtc=now,
            updatedAtUtc=now,
        )
        with self.store.connect() as db:
            replay = self._replay_mutation(
                db, workspace_id, "project.create", payload, idempotency_key
            )
            if replay is not None:
                return Project.model_validate(replay)
            db.execute(
                """INSERT INTO product_projects
                (project_id,workspace_id,title,root_ref,root_display_name,status,pinned,manual_order,
                created_at_utc,updated_at_utc,archived_at_utc,archive_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    project.project_id,
                    project.workspace_id,
                    project.title,
                    project.root_ref,
                    project.root_display_name,
                    project.status,
                    int(project.pinned),
                    project.manual_order,
                    project.created_at_utc.isoformat(),
                    project.updated_at_utc.isoformat(),
                    None,
                    None,
                ),
            )
            self._remember_mutation(
                db, workspace_id, "project.create", payload, idempotency_key, project
            )
        return project

    def register_project(
        self,
        workspace_id: str,
        folder_ticket: str,
        title: str,
        idempotency_key: str | None = None,
    ) -> Project:
        if not folder_ticket or len(folder_ticket) > 512 or "\x00" in folder_ticket:
            raise ValueError("folder ticket is invalid")
        now = _now()
        payload = {
            "folderTicketHash": sha256(folder_ticket.encode("utf-8")).hexdigest(),
            "title": title,
        }
        project = Project(
            projectId=_id("project"),
            workspaceId=workspace_id,
            title=title,
            rootRef=_id("root"),
            rootDisplayName=title,
            createdAtUtc=now,
            updatedAtUtc=now,
        )
        with self.store.connect() as db:
            replay = self._replay_mutation(
                db, workspace_id, "project.register", payload, idempotency_key
            )
            if replay is not None:
                return Project.model_validate(replay)
            db.execute(
                """INSERT INTO product_projects
                (project_id,workspace_id,title,root_ref,root_display_name,status,pinned,manual_order,
                created_at_utc,updated_at_utc,archived_at_utc,archive_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    project.project_id,
                    project.workspace_id,
                    project.title,
                    project.root_ref,
                    project.root_display_name,
                    project.status,
                    int(project.pinned),
                    project.manual_order,
                    project.created_at_utc.isoformat(),
                    project.updated_at_utc.isoformat(),
                    None,
                    None,
                ),
            )
            self._remember_mutation(
                db, workspace_id, "project.register", payload, idempotency_key, project
            )
        return project

    def list_projects(self, workspace_id: str) -> list[Project]:
        return self.list_project_page(workspace_id, limit=500).projects

    def list_project_page(
        self,
        workspace_id: str,
        *,
        cursor: str | None = None,
        limit: int = 50,
        status: str | None = None,
        sort: str = "updated_desc",
    ) -> ProjectPage:
        if not 1 <= limit <= 500:
            raise ValueError("project limit is outside the allowed range")
        if status not in (None, "active", "archived"):
            raise ValueError("project status is invalid")
        order_by = {
            "updated_desc": "pinned DESC, updated_at_utc DESC, project_id DESC",
            "manual": "pinned DESC, manual_order ASC, updated_at_utc DESC, project_id DESC",
            "priority": "pinned DESC, manual_order ASC, updated_at_utc DESC, project_id DESC",
        }.get(sort)
        if order_by is None:
            raise ValueError("project sort is invalid")
        offset = self._decode_cursor(cursor)
        clauses = ["workspace_id=?"]
        params: list[Any] = [workspace_id]
        if status is not None:
            clauses.append("status=?")
            params.append(status)
        with self.store.connect() as db:
            rows = db.execute(
                f"""SELECT * FROM product_projects WHERE {' AND '.join(clauses)}
                ORDER BY {order_by} LIMIT ? OFFSET ?""",
                (*params, limit + 1, offset),
            ).fetchall()
        has_next = len(rows) > limit
        return ProjectPage(
            projects=[self._project_from_row(row) for row in rows[:limit]],
            nextCursor=self._encode_cursor(offset + limit) if has_next else None,
        )

    def _require_project(self, db: Any, workspace_id: str, project_id: str) -> Project:
        row = db.execute(
            "SELECT * FROM product_projects WHERE workspace_id=? AND project_id=?",
            (workspace_id, project_id),
        ).fetchone()
        if row is None:
            raise PermissionError("project is unavailable in this workspace")
        return self._project_from_row(row)

    def update_project(
        self,
        workspace_id: str,
        project_id: str,
        *,
        pinned: bool | None = None,
        manual_order: int | None = None,
        title: str | None = None,
        idempotency_key: str | None = None,
    ) -> Project:
        if pinned is None and manual_order is None and title is None:
            raise ValueError("project update has no changes")
        payload = {
            "projectId": project_id,
            "pinned": pinned,
            "manualOrder": manual_order,
            "title": title,
        }
        with self.store.connect() as db:
            replay = self._replay_mutation(
                db, workspace_id, "project.update", payload, idempotency_key
            )
            if replay is not None:
                return Project.model_validate(replay)
            current = self._require_project(db, workspace_id, project_id)
            updated = Project(
                projectId=current.project_id,
                workspaceId=current.workspace_id,
                title=title if title is not None else current.title,
                rootRef=current.root_ref,
                rootDisplayName=current.root_display_name,
                status=current.status,
                pinned=current.pinned if pinned is None else pinned,
                manualOrder=current.manual_order if manual_order is None else manual_order,
                createdAtUtc=current.created_at_utc,
                updatedAtUtc=_now(),
                archivedAtUtc=current.archived_at_utc,
            )
            db.execute(
                """UPDATE product_projects
                SET title=?, pinned=?, manual_order=?, updated_at_utc=?
                WHERE workspace_id=? AND project_id=?""",
                (
                    updated.title,
                    int(updated.pinned),
                    updated.manual_order,
                    updated.updated_at_utc.isoformat(),
                    workspace_id,
                    project_id,
                ),
            )
            self._remember_mutation(
                db, workspace_id, "project.update", payload, idempotency_key, updated
            )
        return updated

    def archive_project(
        self,
        workspace_id: str,
        project_id: str,
        reason: str,
        idempotency_key: str | None = None,
    ) -> Project:
        if not reason.strip() or len(reason) > 500:
            raise ValueError("archive reason is invalid")
        payload = {"projectId": project_id, "reason": reason}
        with self.store.connect() as db:
            replay = self._replay_mutation(
                db, workspace_id, "project.archive", payload, idempotency_key
            )
            if replay is not None:
                return Project.model_validate(replay)
            current = self._require_project(db, workspace_id, project_id)
            now = _now()
            archived = Project(
                projectId=current.project_id,
                workspaceId=current.workspace_id,
                title=current.title,
                rootRef=current.root_ref,
                rootDisplayName=current.root_display_name,
                status="archived",
                pinned=current.pinned,
                manualOrder=current.manual_order,
                createdAtUtc=current.created_at_utc,
                updatedAtUtc=now,
                archivedAtUtc=now,
            )
            db.execute(
                """UPDATE product_projects
                SET status='archived', archived_at_utc=?, archive_reason=?, updated_at_utc=?
                WHERE workspace_id=? AND project_id=?""",
                (now.isoformat(), reason, now.isoformat(), workspace_id, project_id),
            )
            self._remember_mutation(
                db, workspace_id, "project.archive", payload, idempotency_key, archived
            )
        return archived

    def create_task(
        self,
        workspace_id: str,
        project_id: str,
        title: str,
        assistant_session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> ProductTask:
        now = _now()
        payload = {
            "projectId": project_id,
            "title": title,
            "assistantSessionId": assistant_session_id,
        }
        with self.store.connect() as db:
            replay = self._replay_mutation(
                db, workspace_id, "task.create", payload, idempotency_key
            )
            if replay is not None:
                return ProductTask.model_validate(replay)
            if (
                db.execute(
                    "SELECT 1 FROM product_projects WHERE project_id=? AND workspace_id=?",
                    (project_id, workspace_id),
                ).fetchone()
                is None
            ):
                raise PermissionError("project is unavailable in this workspace")
            task = ProductTask(
                taskId=_id("task"),
                workspaceId=workspace_id,
                projectId=project_id,
                title=title,
                assistantSessionId=assistant_session_id,
                createdAtUtc=now,
                updatedAtUtc=now,
            )
            db.execute(
                "INSERT INTO product_tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    task.task_id,
                    task.workspace_id,
                    task.project_id,
                    task.title,
                    task.status,
                    task.assistant_session_id,
                    None,
                    None,
                    task.created_at_utc.isoformat(),
                    task.updated_at_utc.isoformat(),
                ),
            )
            self._remember_mutation(
                db, workspace_id, "task.create", payload, idempotency_key, task
            )
        return task

    def list_tasks(self, workspace_id: str, project_id: str) -> list[ProductTask]:
        with self.store.connect() as db:
            rows = db.execute(
                "SELECT * FROM product_tasks WHERE workspace_id=? AND project_id=? "
                "ORDER BY updated_at_utc DESC",
                (workspace_id, project_id),
            ).fetchall()
        return [
            ProductTask(
                taskId=r["task_id"],
                workspaceId=r["workspace_id"],
                projectId=r["project_id"],
                title=r["title"],
                status=r["status"],
                assistantSessionId=r["assistant_session_id"],
                assistantTurnId=r["assistant_turn_id"],
                teamJobId=r["team_job_id"],
                createdAtUtc=r["created_at_utc"],
                updatedAtUtc=r["updated_at_utc"],
            )
            for r in rows
        ]

    def add_message(
        self,
        workspace_id: str,
        task_id: str,
        role: str,
        body: str,
        idempotency_key: str | None = None,
    ) -> ProductMessage:
        now = _now()
        payload = {"taskId": task_id, "role": role, "body": body}
        with self.store.connect() as db:
            replay = self._replay_mutation(
                db, workspace_id, "task.message.add", payload, idempotency_key
            )
            if replay is not None:
                return ProductMessage.model_validate(replay)
            if (
                db.execute(
                    "SELECT 1 FROM product_tasks WHERE task_id=? AND workspace_id=?",
                    (task_id, workspace_id),
                ).fetchone()
                is None
            ):
                raise PermissionError("task is unavailable in this workspace")
            message = ProductMessage(
                messageId=_id("message"),
                workspaceId=workspace_id,
                taskId=task_id,
                role=role,
                body=body,
                createdAtUtc=now,
            )
            db.execute(
                "INSERT INTO product_messages VALUES (?,?,?,?,?,?)",
                (
                    message.message_id,
                    message.workspace_id,
                    message.task_id,
                    message.role,
                    message.body,
                    message.created_at_utc.isoformat(),
                ),
            )
            self._remember_mutation(
                db, workspace_id, "task.message.add", payload, idempotency_key, message
            )
        return message

    def list_messages(self, workspace_id: str, task_id: str) -> list[ProductMessage]:
        with self.store.connect() as db:
            rows = db.execute(
                """SELECT * FROM product_messages WHERE workspace_id=? AND task_id=?
                ORDER BY created_at_utc ASC""",
                (workspace_id, task_id),
            ).fetchall()
        return [
            ProductMessage(
                messageId=row["message_id"],
                workspaceId=row["workspace_id"],
                taskId=row["task_id"],
                role=row["role"],
                body=row["body"],
                createdAtUtc=row["created_at_utc"],
            )
            for row in rows
        ]

    def add_link(
        self,
        workspace_id: str,
        task_id: str,
        target_type: str,
        target_id: str,
        idempotency_key: str | None = None,
    ) -> ProductLink:
        now = _now()
        payload = {"taskId": task_id, "targetType": target_type, "targetId": target_id}
        with self.store.connect() as db:
            replay = self._replay_mutation(
                db, workspace_id, "task.link.add", payload, idempotency_key
            )
            if replay is not None:
                return ProductLink.model_validate(replay)
            if (
                db.execute(
                    "SELECT 1 FROM product_tasks WHERE task_id=? AND workspace_id=?",
                    (task_id, workspace_id),
                ).fetchone()
                is None
            ):
                raise PermissionError("task is unavailable in this workspace")
            link = ProductLink(
                linkId=_id("link"),
                workspaceId=workspace_id,
                taskId=task_id,
                targetType=target_type,
                targetId=target_id,
                createdAtUtc=now,
            )
            db.execute(
                "INSERT OR IGNORE INTO product_links VALUES (?,?,?,?,?,?)",
                (
                    link.link_id,
                    link.workspace_id,
                    link.task_id,
                    link.target_type,
                    link.target_id,
                    link.created_at_utc.isoformat(),
                ),
            )
            existing = db.execute(
                """SELECT * FROM product_links WHERE workspace_id=? AND task_id=?
                AND target_type=? AND target_id=?""",
                (workspace_id, task_id, target_type, target_id),
            ).fetchone()
            if existing is not None:
                link = ProductLink(
                    linkId=existing["link_id"], workspaceId=existing["workspace_id"],
                    taskId=existing["task_id"], targetType=existing["target_type"],
                    targetId=existing["target_id"], createdAtUtc=existing["created_at_utc"],
                )
            self._remember_mutation(
                db, workspace_id, "task.link.add", payload, idempotency_key, link
            )
        return link

    def set_preference(
        self,
        workspace_id: str,
        principal_id: str,
        preference_key: str,
        value_json: str,
        idempotency_key: str | None = None,
    ) -> Preference:
        payload = {
            "principalId": principal_id,
            "preferenceKey": preference_key,
            "valueJson": value_json,
        }
        preference = Preference(
            workspaceId=workspace_id,
            principalId=principal_id,
            preferenceKey=preference_key,
            valueJson=value_json,
            updatedAtUtc=_now(),
        )
        with self.store.connect() as db:
            replay = self._replay_mutation(
                db, workspace_id, "preferences.set", payload, idempotency_key
            )
            if replay is not None:
                return Preference.model_validate(replay)
            db.execute(
                """INSERT INTO product_preferences VALUES (?,?,?,?,?)
                ON CONFLICT(workspace_id,principal_id,preference_key) DO UPDATE SET
                value_json=excluded.value_json, updated_at_utc=excluded.updated_at_utc""",
                (
                    preference.workspace_id,
                    preference.principal_id,
                    preference.preference_key,
                    preference.value_json,
                    preference.updated_at_utc.isoformat(),
                ),
            )
            self._remember_mutation(
                db, workspace_id, "preferences.set", payload, idempotency_key, preference
            )
        return preference

    def get_preference(
        self, workspace_id: str, principal_id: str, preference_key: str
    ) -> Preference | None:
        with self.store.connect() as db:
            row = db.execute(
                """SELECT * FROM product_preferences WHERE workspace_id=?
                AND principal_id=? AND preference_key=?""",
                (workspace_id, principal_id, preference_key),
            ).fetchone()
        return (
            None
            if row is None
            else Preference(
                workspaceId=row["workspace_id"],
                principalId=row["principal_id"],
                preferenceKey=row["preference_key"],
                valueJson=row["value_json"],
                updatedAtUtc=row["updated_at_utc"],
            )
        )
