from __future__ import annotations

from datetime import UTC, datetime
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

    def create_project(self, workspace_id: str, title: str) -> Project:
        now = _now()
        project = Project(
            projectId=_id("project"),
            workspaceId=workspace_id,
            title=title,
            createdAtUtc=now,
            updatedAtUtc=now,
        )
        with self.store.connect() as db:
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
    ) -> ProductTask:
        now = _now()
        with self.store.connect() as db:
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

    def add_message(self, workspace_id: str, task_id: str, role: str, body: str) -> ProductMessage:
        now = _now()
        with self.store.connect() as db:
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
        self, workspace_id: str, task_id: str, target_type: str, target_id: str
    ) -> ProductLink:
        now = _now()
        with self.store.connect() as db:
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
        return link

    def set_preference(
        self, workspace_id: str, principal_id: str, preference_key: str, value_json: str
    ) -> Preference:
        preference = Preference(
            workspaceId=workspace_id,
            principalId=principal_id,
            preferenceKey=preference_key,
            valueJson=value_json,
            updatedAtUtc=_now(),
        )
        with self.store.connect() as db:
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
