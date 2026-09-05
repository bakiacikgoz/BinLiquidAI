import { Check, ChevronRight, RotateCcw, Zap } from 'lucide-react';
import { useState, useRef, useId, type ReactNode, type CSSProperties } from 'react';
import { canonicalAssistantProviderId, type AssistantModelDiscoveryState } from '../../assistant/useAssistantModels';
import type { AssistantRuntimeSettings } from '../../settings';

const efforts = ['low', 'medium', 'high', 'very_high'] as const;

export function AssistantQuickModelSettings({ settings, discovery, locale, onChange, children }: {
  settings: AssistantRuntimeSettings;
  discovery?: AssistantModelDiscoveryState | null;
  locale: string;
  onChange: (settings: Partial<AssistantRuntimeSettings>) => void;
  children: ReactNode;
}) {
  const [modelsOpen, setModelsOpen] = useState(false);
  const modelTrigger = useRef<HTMLButtonElement>(null);
  const listId = useId();
  const tr = locale === 'tr';
  const effort = Math.max(0, efforts.indexOf(settings.reasoningEffort ?? 'medium'));
  const effortLabels = tr ? ['Sınırlı', 'Dengeli', 'Yüksek', 'Ultra'] : ['Limited', 'Balanced', 'High', 'Ultra'];
  const provider = canonicalAssistantProviderId(settings.assistantProvider);
  const currentModel = settings.assistantModel || settings.assistantHfModelId;
  const models = discovery?.models ?? [];
  const closeModels = () => { setModelsOpen(false); modelTrigger.current?.focus(); };
  const selectModel = (modelProvider: string, modelId: string) => { onChange({
    assistantProvider: modelProvider,
    assistantModel: canonicalAssistantProviderId(modelProvider) === 'local-transformers' ? '' : modelId,
    assistantHfModelId: canonicalAssistantProviderId(modelProvider) === 'local-transformers' ? modelId : '',
  }); closeModels(); };
  return <div className="quick-model-settings">
    {modelsOpen && <div id={listId} className="quick-model-list" role="radiogroup" aria-label={tr ? 'Model seçimi' : 'Model selection'} onKeyDown={(event) => {
      if (event.key === 'Escape') { event.stopPropagation(); closeModels(); return; }
      if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const options = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="radio"]:not(:disabled)'));
      const current = options.indexOf(event.target as HTMLButtonElement);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? options.length - 1 : (current + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length;
      options[next]?.focus();
      options[next]?.click();
    }}>
      <button type="button" className="quick-model-option" role="radio" aria-checked={!provider && !currentModel}
        onClick={() => { onChange({ assistantProvider: '', assistantModel: '', assistantHfModelId: '' }); closeModels(); }}>
        <span><strong>{tr ? 'Varsayılan' : 'Default'}</strong><small>{tr ? 'Profilin önerdiği model' : 'Recommended by your profile'}</small></span>
        {!provider && !currentModel ? <Check size={16} /> : null}
      </button>
      {models.map((model) => {
        const available = (model.installed || model.configured) && discovery?.providers.find((item) => canonicalAssistantProviderId(item.provider) === canonicalAssistantProviderId(model.provider))?.available !== false;
        const selected = provider === canonicalAssistantProviderId(model.provider) && currentModel === model.id;
        return <button type="button" role="radio" aria-checked={selected} disabled={!available} className="quick-model-option" key={`${model.provider}:${model.id}`}
          onClick={() => selectModel(model.provider, model.id)}>
          <span><strong>{model.displayName || model.id}</strong><small>{model.provider}{!available ? (tr ? ' · Kullanılamıyor' : ' · Unavailable') : ''}</small></span>
          {selected ? <Check size={16} /> : null}
        </button>;
      })}
    </div>}
    {modelsOpen && <div className="quick-model-discovery" role="status">
      <span>{discovery?.status === 'loading' ? (tr ? 'Modeller yükleniyor…' : 'Loading models…')
        : discovery?.status === 'error' ? (tr ? 'Modellere bağlanılamadı' : 'Could not connect to models')
        : models.length === 0 ? (tr ? 'Henüz model bulunamadı' : 'No models found yet') : (tr ? 'Kullanılabilir modeller' : 'Available models')}</span>
      {discovery ? <button type="button" className="icon-button" aria-label={tr ? 'Modelleri yenile' : 'Refresh models'} disabled={discovery.status === 'loading'} onClick={discovery.refresh}><RotateCcw size={14} /></button> : null}
    </div>}
    <div className={`quick-effort-card${effort === 3 ? ' is-ultra' : ''}`} style={{ '--effort-fill': `${effort / 3 * 100}%` } as CSSProperties}>
      <div className="quick-effort-header"><Zap size={15} />
        <button ref={modelTrigger} type="button" className="quick-effort-model-trigger" aria-label={tr ? 'Model listesini aç' : 'Choose model'} aria-expanded={modelsOpen} aria-controls={modelsOpen ? listId : undefined} onClick={() => setModelsOpen(!modelsOpen)}>
          <strong>{effortLabels[effort]}<ChevronRight size={13} /></strong>
          <span className="quick-effort-model">{currentModel || (tr ? 'Profil varsayılanı' : 'Profile default')}</span>
        </button>
        <button type="button" className="icon-button" aria-label={tr ? 'Düşünme düzeyini sıfırla' : 'Reset reasoning effort'} onClick={() => onChange({ reasoningEffort: 'medium' })}><RotateCcw size={14} /></button>
      </div>
      <input type="range" min="0" max="3" step="1" value={effort} aria-label={tr ? 'Düşünme düzeyi' : 'Reasoning effort'} aria-valuetext={effortLabels[effort]} onChange={(event) => onChange({ reasoningEffort: efforts[Number(event.target.value)] })} />
      <div className="quick-effort-scale" aria-hidden="true">{effortLabels.map((label) => <span key={label} title={label}>•</span>)}</div>
    </div>
    <details className="quick-model-advanced"><summary>{tr ? 'Gelişmiş ayarlar' : 'Advanced settings'}</summary><div>{children}</div></details>
  </div>;
}
