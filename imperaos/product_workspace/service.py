from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .models import Preference, ProductLink, ProductMessage, ProductTask, Project
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

    def create_project(
        self, workspace_id: str, title: str, idempotency_key: str | None = None
    ) -> Project:
        now = _now()
        payload = {"title": title}
        project = Project(
            projectId=_id("project"),
            workspaceId=workspace_id,
            title=title,
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
                "INSERT INTO product_projects VALUES (?,?,?,?,?,?)",
                (
                    project.project_id,
                    project.workspace_id,
                    project.title,
                    project.status,
                    project.created_at_utc.isoformat(),
                    project.updated_at_utc.isoformat(),
                ),
            )
            self._remember_mutation(
                db, workspace_id, "project.create", payload, idempotency_key, project
            )
        return project

    def list_projects(self, workspace_id: str) -> list[Project]:
        with self.store.connect() as db:
            rows = db.execute(
                "SELECT * FROM product_projects WHERE workspace_id=? ORDER BY updated_at_utc DESC",
                (workspace_id,),
            ).fetchall()
        return [
            Project(
                projectId=r["project_id"],
                workspaceId=r["workspace_id"],
                title=r["title"],
                status=r["status"],
                createdAtUtc=r["created_at_utc"],
                updatedAtUtc=r["updated_at_utc"],
            )
            for r in rows
        ]

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
