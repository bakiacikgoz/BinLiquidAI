import { invoke } from '@tauri-apps/api/core';
import { z } from 'zod';

const envelope = z.discriminatedUnion('ok', [
  z.object({ ok: z.literal(true), data: z.unknown(), error: z.null() }).strict(),
  z.object({ ok: z.literal(false), data: z.null(), error: z.object({ code: z.string(), message: z.string(), retryable: z.boolean() }).passthrough() }).strict(),
]);
const project = z.object({ projectId: z.string(), workspaceId: z.string(), title: z.string(), status: z.string(), createdAtUtc: z.string(), updatedAtUtc: z.string() }).strict();
const task = z.object({ taskId: z.string(), workspaceId: z.string(), projectId: z.string(), title: z.string(), status: z.string(), assistantSessionId: z.string().nullable(), assistantTurnId: z.string().nullable(), teamJobId: z.string().nullable(), createdAtUtc: z.string(), updatedAtUtc: z.string() }).strict();

export class ProductWorkspaceClient {
  private async call<T>(command: string, params: Record<string, unknown>, schema: z.ZodType<T>, idempotencyKey: string | null = null): Promise<T> {
    const raw = await invoke<unknown>(command, { payload: { params, idempotencyKey, timeoutMs: 15_000 } });
    const parsed = envelope.parse(raw);
    if (!parsed.ok) throw new Error(parsed.error.message);
    return schema.parse(parsed.data);
  }

  listProjects() { return this.call('bridge_product_project_list', {}, z.object({ projects: z.array(project) }).strict()); }
  createProject(title: string) { return this.call('bridge_product_project_create', { title }, project, `project-${crypto.randomUUID()}`); }
  listTasks(projectId: string) { return this.call('bridge_product_task_list', { projectId }, z.object({ tasks: z.array(task) }).strict()); }
  createTask(projectId: string, title: string, assistantSessionId?: string) { return this.call('bridge_product_task_create', { projectId, title, assistantSessionId }, task, `task-${crypto.randomUUID()}`); }
}

export const productWorkspaceClient = new ProductWorkspaceClient();
