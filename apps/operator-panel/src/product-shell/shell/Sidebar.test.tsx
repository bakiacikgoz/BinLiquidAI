import { screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const workspace = vi.hoisted(() => ({
  listProjects: vi.fn(), listTasks: vi.fn(), updateProject: vi.fn(), updateTask: vi.fn(),
  archiveProject: vi.fn(), archiveTask: vi.fn(), registerProjectFromFolder: vi.fn(),
}));

vi.mock('../adapters/productWorkspaceClient', () => ({ productWorkspaceClient: workspace }));
vi.mock('./GlobalSearch', () => ({ GlobalSearch: () => <div /> }));

import { renderOperatorPanel } from '../../test/render';
import { useProductShellStore } from '../state/productShellStore';
import { Sidebar } from './Sidebar';

const project = {
  projectId: 'project-release', workspaceId: 'workspace-1', title: 'Release workspace',
  rootRef: 'root-release', rootDisplayName: 'Release workspace', status: 'active' as const,
  pinned: false, manualOrder: 2, createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z', archivedAtUtc: null,
};
const task = {
  taskId: 'task-release', workspaceId: 'workspace-1', projectId: 'project-release',
  title: 'Prepare release', status: 'active' as const, priority: 1, pinned: false, manualOrder: 3,
  reasoningEffort: 'high' as const, speedProfile: 'standard' as const, approvalProfile: 'risk_based' as const,
  assistantSessionId: 'session-release', assistantTurnId: null, teamJobId: null,
  createdAtUtc: '2026-07-24T12:00:00Z', updatedAtUtc: '2026-07-24T12:00:00Z', archivedAtUtc: null,
};
const archivedTask = {
  ...task,
  status: 'archived' as const,
  updatedAtUtc: '2026-08-07T07:00:00Z',
  archivedAtUtc: '2026-08-07T07:00:00Z',
};

function LocationProbe() {
  const location = useLocation();
  return <p>Current route: {location.pathname}{location.search}</p>;
}

describe('Sidebar project lifecycle', () => {
  it('collapses recent conversations without opening the options menu', async () => {
    const { user, container } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);
    await screen.findAllByText(task.title);
    const toggle = screen.getByRole('button', { name: 'Yakın zamanlılar' });
    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(container.querySelector('.recent-list')).toBeNull();
    expect(screen.queryByRole('dialog', { name: 'Sohbet düzeni' })).not.toBeInTheDocument();
    await user.click(toggle);
    expect(container.querySelector('.recent-list a')).toHaveTextContent(task.title);
  });

  it('applies layout choices and creates a usable custom section', async () => {
    const { user, container } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);
    await screen.findAllByText(task.title);
    await user.click(screen.getByRole('button', { name: 'Görevleri düzenle' }));
    await user.click(screen.getByRole('button', { name: 'Kenar çubuğunu düzenle' }));
    await user.click(screen.getByRole('menuitemradio', { name: 'Tek listede' }));
    expect(screen.queryByRole('button', { name: project.title })).not.toBeInTheDocument();
    expect(container.querySelector('.recent-list a')).toHaveTextContent(task.title);
    await user.click(screen.getByRole('button', { name: 'Görevleri düzenle' }));
    await user.click(screen.getByRole('button', { name: 'Yeni bölüm' }));
    await user.type(screen.getByLabelText('Bölüm adı'), 'Çalışmalarım');
    await user.click(screen.getByRole('button', { name: 'Oluştur' }));
    await user.selectOptions(screen.getByLabelText('Çalışmalarım bölümüne sohbet ekle'), task.taskId);
    expect(container.querySelector('.sidebar-custom-section a')).toHaveTextContent(task.title);
    expect(container.querySelector('.recent-list a')).toBeNull();
    expect(localStorage.getItem('imperaos-sidebar-sections')).toContain(task.taskId);
  });
  it('loads tasks from projects beyond the first page', async () => {
    workspace.listProjects.mockImplementation(async ({ cursor }) => cursor
      ? { projects: [{ ...project, projectId: 'later', title: 'Later project' }], nextCursor: null }
      : { projects: [project], nextCursor: 'page-2' });
    workspace.listTasks.mockImplementation(async (projectId) => ({ tasks: projectId === 'later' ? [{ ...task, taskId: 'later-task', projectId, title: 'Later task' }] : [] }));
    const { container, user } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);
    await waitFor(() => expect(container.querySelector('.recent-list')).toHaveTextContent('Later task'));
    await user.click(screen.getByRole('button', { name: 'Görevleri düzenle' }));
    await user.click(screen.getByText('Filtrele ve yenile'));
    await user.type(screen.getByLabelText('Görevlerde ara'), 'unmatched');
    expect(container.querySelector('.recent-list a')).toBeNull();
    await user.clear(screen.getByLabelText('Görevlerde ara'));
    expect(container.querySelector('.recent-list a')).toHaveTextContent('Later task');
  });
  it('shows project information after hovering a conversation', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);
    const links = await screen.findAllByRole('link', { name: task.title });
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    await user.hover(links[0]);
    expect(await screen.findByRole('tooltip')).toHaveTextContent(project.title);
    expect(screen.getByRole('tooltip')).toHaveTextContent('1 sohbet');
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('renders an indented empty state for a project with no conversations', async () => {
    workspace.listTasks.mockResolvedValue({ tasks: [] });
    renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);
    expect(await screen.findAllByText('Sohbet yok')).toHaveLength(2);
    expect(document.querySelector('.project-empty')).toHaveTextContent('Sohbet yok');
    expect(document.querySelector('.recent-empty')).toHaveTextContent('Sohbet yok');
  });
  it('opens a newly registered project for its first conversation', async () => {
    workspace.registerProjectFromFolder.mockResolvedValue(project);
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={[`/task/${task.taskId}`]}><Sidebar /><LocationProbe /></MemoryRouter>);
    await user.click(screen.getByRole('button', { name: 'Yeni proje' }));
    await waitFor(() => expect(screen.getByText('Current route: /?project=project-release')).toBeInTheDocument());
    expect(workspace.registerProjectFromFolder).toHaveBeenCalledOnce();
  });

  it('expands or collapses a project without leaving the current conversation', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={[`/task/${task.taskId}`]}><Sidebar /><LocationProbe /></MemoryRouter>);
    await user.click(await screen.findByRole('button', { name: project.title }));
    expect(screen.getByText(`Current route: /task/${task.taskId}`)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: project.title })).toHaveAttribute('aria-expanded', 'false');
  });

  it('starts a new conversation in the chosen project without hiding existing tasks', async () => {
    useProductShellStore.setState({ selectedTaskId: task.taskId });
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={[`/task/${task.taskId}`]}><Sidebar /><LocationProbe /></MemoryRouter>);
    await user.click(await screen.findByRole('button', { name: 'Release workspace projesinde yeni sohbet' }));
    expect(screen.getByText('Current route: /?project=project-release')).toBeInTheDocument();
    expect(screen.getAllByText(task.title)).toHaveLength(2);
    expect(useProductShellStore.getState().selectedTaskId).toBeNull();
  });

  it('starts a new conversation from the Tasks section', async () => {
    useProductShellStore.setState({ selectedTaskId: task.taskId });
    const { user } = renderOperatorPanel(<MemoryRouter initialEntries={[`/task/${task.taskId}`]}><Sidebar /><LocationProbe /></MemoryRouter>);
    await user.click(screen.getByRole('button', { name: 'Yeni sohbet' }));
    expect(screen.getByText('Current route: /')).toBeInTheDocument();
    expect(useProductShellStore.getState().selectedTaskId).toBeNull();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useProductShellStore.setState(useProductShellStore.getInitialState(), true);
    workspace.listProjects.mockResolvedValue({ projects: [project], nextCursor: null });
    workspace.listTasks.mockResolvedValue({ tasks: [task] });
    workspace.updateProject.mockResolvedValue({ ...project, pinned: true });
    workspace.updateTask.mockResolvedValue({ ...task, manualOrder: 2 });
  });

  it('renders durable projects and persists a pin action through the workspace client', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);

    expect(screen.getByRole('complementary', { name: 'Product navigation' }))
      .toHaveClass('sidebar', 'codex-sidebar');
    expect(screen.getByRole('button', { name: /kenar çubuğunu/i })).toBeVisible();
    await user.click(await screen.findByRole('button', { name: 'Pin Release workspace' }));

    await waitFor(() => expect(workspace.updateProject).toHaveBeenCalledWith('project-release', { pinned: true }));
  });

  it('preserves governed project and task manual-order mutations', async () => {
    const { user } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);

    await user.click(await screen.findByRole('button', { name: 'Move Release workspace up' }));
    await user.click((await screen.findAllByRole('button', { name: 'Move Prepare release up' }))[0]);

    await waitFor(() => expect(workspace.updateProject).toHaveBeenCalledWith('project-release', { manualOrder: 1 }));
    expect(workspace.updateTask).toHaveBeenCalledWith('task-release', { manualOrder: 2 });
  });

  it('filters and refreshes the task collection', async () => {
    const { user, container } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);
    await screen.findAllByText(task.title);
    await user.click(screen.getByRole('button', { name: 'Görevleri düzenle' }));
    await user.click(screen.getByText('Filtrele ve yenile'));
    await user.selectOptions(screen.getByLabelText('Görev durumu'), 'completed');
    expect(container.querySelector('.recent-list a')).toBeNull();
    expect(screen.getByText('Bu filtreye uygun görev yok.')).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Görev durumu'), 'all');
    expect(container.querySelector('.recent-list a')).toHaveTextContent(task.title);
    await user.click(screen.getByRole('button', { name: 'Görevleri yenile' }));
    await waitFor(() => expect(workspace.listTasks.mock.calls.length).toBeGreaterThan(1));
  });

  it('preserves tasks from successful projects when another project fails', async () => {
    workspace.listProjects.mockResolvedValue({ projects: [project, { ...project, projectId: 'broken' }], nextCursor: null });
    workspace.listTasks.mockImplementation(async (id) => { if (id === 'broken') throw new Error('offline'); return { tasks: [task] }; });
    const { container } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);
    await waitFor(() => expect(container.querySelector('.recent-list a')).toHaveTextContent(task.title));
    expect(screen.getByRole('alert')).toHaveTextContent('Bazı projelerin görevleri yüklenemedi');
  });

  it('distinguishes the primary create route and keeps desktop-only data truth compact', async () => {
    workspace.listProjects.mockRejectedValueOnce(new Error(
      'Workspace data requires the ImperaOS desktop runtime. Open this screen in the desktop app.',
    ));

    const { container } = renderOperatorPanel(<MemoryRouter><Sidebar /></MemoryRouter>);

    expect(screen.getByRole('link', { name: /Yeni görev/i })).toHaveClass('sidebar-primary-action');
    expect(await screen.findByRole('alert')).toHaveClass('sidebar-runtime-notice');
    expect(container.querySelector('.sidebar-runtime-notice')).toHaveTextContent(/desktop runtime/i);
  });

  it('archives a selected task only after success, removes it from active navigation, and leaves its record retained', async () => {
    useProductShellStore.setState({ selectedTaskId: task.taskId });
    workspace.archiveTask.mockImplementation(async () => {
      workspace.listTasks.mockResolvedValue({ tasks: [archivedTask] });
      return archivedTask;
    });
    const { user } = renderOperatorPanel(
      <MemoryRouter initialEntries={[`/task/${task.taskId}/workspace`]}>
        <Sidebar />
        <LocationProbe />
      </MemoryRouter>,
    );

    await user.click((await screen.findAllByRole('button', { name: `Archive ${task.title}` }))[0]);

    await waitFor(() => expect(screen.getByText('Current route: /')).toBeInTheDocument());
    expect(screen.queryByText(task.title)).not.toBeInTheDocument();
    expect(useProductShellStore.getState().selectedTaskId).toBeNull();
    expect(useProductShellStore.getState().tasks).toEqual([
      expect.objectContaining({ id: task.taskId, status: 'archived' }),
    ]);
  });

  it('leaves the active row, task route, and selection unchanged when archive fails', async () => {
    useProductShellStore.setState({ selectedTaskId: task.taskId });
    workspace.archiveTask.mockRejectedValue(new Error('Archive denied'));
    const { user } = renderOperatorPanel(
      <MemoryRouter initialEntries={[`/task/${task.taskId}`]}>
        <Sidebar />
        <LocationProbe />
      </MemoryRouter>,
    );

    await user.click((await screen.findAllByRole('button', { name: `Archive ${task.title}` }))[0]);

    expect(await screen.findByRole('alert')).toHaveTextContent('Archive denied');
    expect(screen.getByText(`Current route: /task/${task.taskId}`)).toBeInTheDocument();
    expect(screen.getAllByText(task.title)).toHaveLength(2);
    expect(useProductShellStore.getState().selectedTaskId).toBe(task.taskId);
    expect(useProductShellStore.getState().tasks).toEqual([
      expect.objectContaining({ id: task.taskId, status: 'active' }),
    ]);
  });
});
