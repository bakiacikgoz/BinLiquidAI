import { useEffect, useRef, useState } from 'react';
import { Bug, Hammer, Radar, RefreshCw } from 'lucide-react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { useAssistantModels } from '../../assistant/useAssistantModels';
import type { AssistantComposerControls } from '../../assistant/assistantTypes';
import { AssistantComposer } from '../../components/assistant/AssistantComposer';
import {
  getAssistantRuntimeSettings,
  loadSettings,
  resolveLocale,
  saveSettings,
  type AssistantRuntimeSettings,
  type PanelSettings,
} from '../../settings';
import { useProductShellStore } from '../state/productShellStore';
import { productWorkspaceClient, type ProductWorkspaceProject } from '../adapters/productWorkspaceClient';
import { ComposerProjectPicker } from '../shell/ComposerProjectPicker';
import { ProjectConnectionNotice } from '../shell/ProjectConnectionNotice';

const suggestions = [
  {
    title: 'Kodlamayı keşfet ve anla',
    icon: Radar,
    tone: 'blue' as const,
    prompt: 'Bu kod tabanını keşfet ve mimarisini açıkla.',
  },
  {
    title: 'Yeni bir özellik, uygulama veya araç oluştur',
    icon: Hammer,
    tone: 'purple' as const,
    prompt: 'Yeni bir özellik, uygulama veya araç oluştur.',
  },
  {
    title: 'Kodu gözden geçir ve değişiklik öner',
    icon: RefreshCw,
    tone: 'green' as const,
    prompt: 'Kodu gözden geçir ve iyileştirme önerileri sun.',
  },
  {
    title: 'Sorunları ve hataları düzelt',
    icon: Bug,
    tone: 'orange' as const,
    prompt: 'Sorunları ve hataları bul ve düzelt.',
  },
];

export function NewWorkPage() {
  const location = useLocation();
  return <NewWorkContent key={location.key} />;
}

function NewWorkContent() {
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  const upsertProjects = useProductShellStore((state) => state.upsertProjects);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState('');
  const [projectLoadError, setProjectLoadError] = useState('');
  const [projectLoadAttempt, setProjectLoadAttempt] = useState(0);
  const [projects, setProjects] = useState<ProductWorkspaceProject[]>([]);
  const [projectId, setProjectId] = useState('');
  const [projectSelectionError, setProjectSelectionError] = useState('');
  const [projectsReady, setProjectsReady] = useState(false);
  const [seedPrompt, setSeedPrompt] = useState('');
  const [settings, setSettings] = useState<PanelSettings>(() => loadSettings());
  const pendingTask = useRef<{
    projectSelection: string;
    message: string;
    task: Awaited<ReturnType<typeof productWorkspaceClient.createTask>>;
  } | null>(null);
  const modelDiscovery = useAssistantModels({
    settings,
    profile: settings.profile,
    provider: 'all',
  });
  useEffect(() => {
    let active = true;
    setProjectsReady(false);
    setProjectLoadError('');
    setProjectSelectionError('');
    const loadProjects = async () => {
      const projects: ProductWorkspaceProject[] = [];
      const visitedCursors = new Set<string>();
      let cursor: string | undefined;
      do {
        const page = await productWorkspaceClient.listProjects({ cursor, status: 'active', limit: 100 });
        if (!active) return [];
        projects.push(...page.projects);
        cursor = page.nextCursor ?? undefined;
        if (cursor && visitedCursors.has(cursor)) throw new Error('Proje listesi tamamlanamadı. Sayfayı yenileyip tekrar deneyin.');
        if (cursor) visitedCursors.add(cursor);
      } while (cursor);
      return projects;
    };
    void loadProjects().then((projects) => {
      if (!active) return;
      const activeProjects = projects.filter((project) => project.status !== 'archived');
      setProjectsReady(true);
      setProjects(activeProjects);
      upsertProjects(activeProjects.map((project) => ({
        projectId: project.projectId,
        rootRef: project.rootRef,
        rootDisplayName: project.rootDisplayName,
      })));
      const requestedProjectId = searchParams.get('project');
      if (requestedProjectId && !activeProjects.some((project) => project.projectId === requestedProjectId)) {
        setProjectId(requestedProjectId);
        setProjectSelectionError('Seçilen proje bulunamadı veya arşivlendi. Devam etmek için listeden bir proje seçin.');
      } else if (requestedProjectId) {
        setProjectId(requestedProjectId);
        setProjectSelectionError('');
      } else {
        setProjectId((current) => current);
      }
    }).catch((cause) => {
      if (active) setProjectLoadError(cause instanceof Error ? cause.message : 'PROJECT_LIST_UNAVAILABLE');
    });
    return () => { active = false; };
  }, [projectLoadAttempt, searchParams, upsertProjects]);
  const updateRuntimeSettings = (next: Partial<AssistantRuntimeSettings>) => {
    setSettings((current) => {
      const updated = { ...current, ...next };
      saveSettings(updated);
      return updated;
    });
  };
  const start = async (
    message: string,
    runtimeSettings: AssistantRuntimeSettings,
    controls: AssistantComposerControls,
  ) => {
    if (!projectsReady || projectSelectionError) return false;
    if (!projectId) { setError('Başlamak için bir proje seçin.'); return false; }
    try {
      setError('');
      let task = pendingTask.current?.projectSelection === projectId && pendingTask.current.message === message
        ? pendingTask.current.task : undefined;
      if (!task) {
        const selectedProjectId = projectId;
        const assistantSessionId = `product-session-${crypto.randomUUID()}`;
        task = await productWorkspaceClient.createTask(selectedProjectId, message, assistantSessionId, {
          reasoningEffort: runtimeSettings.reasoningEffort ?? 'medium',
          speedProfile: runtimeSettings.speedProfile ?? 'standard',
          approvalProfile: runtimeSettings.approvalProfile ?? 'risk_based',
        });
        pendingTask.current = { projectSelection: projectId, message, task };
      }
      await productWorkspaceClient.addMessage(task.taskId, 'user', message);
      pendingTask.current = null;
      upsertTasks([{ id: task.taskId, projectId: task.projectId, title: task.title, createdAt: task.createdAtUtc, updatedAt: task.updatedAtUtc, status: task.status, priority: task.priority, pinned: task.pinned, manualOrder: task.manualOrder, archivedAt: task.archivedAtUtc, assistantSessionId: task.assistantSessionId ?? undefined, reasoningEffort: task.reasoningEffort, speedProfile: task.speedProfile, approvalProfile: task.approvalProfile }]);
      useProductShellStore.getState().setContextRailOpen(true);
      navigate(`/task/${task.taskId}`, { state: { initialMessage: message, runtimeSettings, controls } });
      return true;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Görev oluşturulamadı. Mesajınızı koruyarak tekrar deneyin.');
      return false;
    }
  };
  return (
    <main className="new-work-page codex-home">
      <div className="welcome-stage">
        <div className="welcome-hero">
          <div className="welcome-glyph" aria-hidden>
            <svg width="60" height="54" viewBox="0 0 40 36" fill="none">
              <path
                d="M13.5 28c-4.7 0-8.5-3.4-8.5-7.6 0-3.2 2-5.9 5-7.1C10.5 8.5 14.4 5.5 19.2 5.5c4.2 0 7.8 2.3 9.5 5.6 1 .2 1.9.5 2.7 1 3.2 1.7 5.1 4.7 5.1 8.1 0 5-4.3 9-9.6 9H13.5z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinejoin="round"
              />
              <path d="M15 18.5h4.5M15 22h7.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M15 15.5l2 2-2 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h1>{projects.find((project) => project.projectId === projectId)?.title ? `${projects.find((project) => project.projectId === projectId)?.title} projesinde ne oluşturalım?` : 'Ne oluşturalım?'}</h1>
          <div className="suggestion-grid codex-suggestions">
            {suggestions.map(({ title, icon: SuggestionIcon, tone, prompt }) => (
              <button
                key={title}
                type="button"
                className={`suggestion-card tone-${tone}`}
                onClick={() => setSeedPrompt(prompt)}
              >
                <span className={`suggestion-icon tone-${tone}`}>
                  <SuggestionIcon size={18} strokeWidth={1.75} />
                </span>
                <span className="suggestion-title">{title}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="welcome-composer">
          {projectLoadError ? <ProjectConnectionNotice detail={projectLoadError} onRetry={() => setProjectLoadAttempt((attempt) => attempt + 1)} /> : null}
          {error || projectSelectionError ? <p className="product-home-error" role="alert">{error || projectSelectionError}</p> : null}
          <AssistantComposer
            label="Governed assistant"
            placeholder="İstediğin şeyi yap"
            sendLabel="Başlat"
            disabled={!projectsReady || Boolean(projectSelectionError)}
            initialValue={seedPrompt}
            runtimeSettings={getAssistantRuntimeSettings(settings)}
            modelDiscovery={modelDiscovery}
            locale={resolveLocale(settings.locale)}
            variant="product"
            showRuntimeContext={false}
            projectControl={<ComposerProjectPicker projects={projects} projectId={projectId} ready={projectsReady}
              onSelect={(id) => { setProjectId(id); setProjectSelectionError(''); setError(''); }}
              onCreate={async () => {
                try {
                  const project = await productWorkspaceClient.registerProjectFromFolder();
                  if (!project) return;
                  setProjects((current) => [...current.filter((item) => item.projectId !== project.projectId), project]);
                  setProjectId(project.projectId); setProjectSelectionError(''); setError('');
                  window.dispatchEvent(new Event('imperaos-projects-changed'));
                } catch (cause) { setError(cause instanceof Error ? cause.message : 'Proje eklenemedi. Yeniden deneyin.'); }
              }} />}
            onRuntimeSettingsChange={updateRuntimeSettings}
            onSend={start}
          />
        </div>
      </div>
    </main>
  );
}
