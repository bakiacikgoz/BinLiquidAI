import { ArrowLeft, CircleUserRound, Search } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { canonicalAssistantProviderId, useAssistantModels } from '../../assistant/useAssistantModels';
import { loadSettings, resolveLocale, resolveThemeMode, saveSettings, type PanelSettings } from '../../settings';
import { useProductShellStore } from '../state/productShellStore';
import { productText } from '../ui/productCopy';

const groups = [
  ['Account', 'General', 'Appearance', 'Assistant'],
  ['System', 'AI providers', 'Security', 'Shortcuts'],
] as const;
const keywords: Record<string, string[]> = {
  General: ['Operator identity', 'Language', 'Workspace'],
  Appearance: ['Theme', 'Dark', 'Light'],
  Assistant: ['Assistant profile', 'Model', 'Default approval profile'],
  'AI providers': ['Model', 'Configure providers', 'Refresh models'],
  Security: ['Advanced system settings'],
  Shortcuts: ['Global search', 'Terminal search', 'Close search'],
};

export function SettingsShell() {
  const [settings, setSettings] = useState<PanelSettings>(() => loadSettings());
  const [status, setStatus] = useState('');
  const [query, setQuery] = useState('');
  const [activeSection, setActiveSection] = useState('General');
  const setTheme = useProductShellStore((state) => state.setTheme);
  const locale = resolveLocale(settings.locale);
  const t = productText(locale);
  const discovery = useAssistantModels({ settings, profile: settings.profile, provider: 'all' });
  const modelAvailable = (model: typeof discovery.models[number]) => (model.installed || model.configured)
    && discovery.providers.find((item) => canonicalAssistantProviderId(item.provider) === canonicalAssistantProviderId(model.provider))?.available !== false;
  const selectedModel = discovery.models.find((model) => canonicalAssistantProviderId(model.provider) === canonicalAssistantProviderId(settings.assistantProvider)
    && model.id === (settings.assistantModel || settings.assistantHfModelId));
  const selectedKey = selectedModel ? JSON.stringify([selectedModel.provider, selectedModel.id]) : '';
  const hasCustomSelection = Boolean(settings.assistantProvider || settings.assistantModel || settings.assistantHfModelId);
  const normalized = query.trim().toLocaleLowerCase(locale);
  const matches = (section: string) => [section, ...(keywords[section] ?? [])]
    .some((value) => `${value} ${t(value)}`.toLocaleLowerCase(locale).includes(normalized));
  const visibleGroups = groups.map(([group, ...items]) => ({ group, items: items.filter(matches) }));
  const update = (next: Partial<PanelSettings>) => { setSettings((current) => ({ ...current, ...next })); setStatus(''); };
  const row = (title: string, description: string, children: ReactNode) => <SettingsRow title={t(title)} description={t(description)}>{children}</SettingsRow>;
  const models = <SettingsBlock title={t('AI providers')}>
    {row('Model', 'Choose a discovered model.', <select aria-label={t('Model')} value={selectedKey || (hasCustomSelection ? '__unavailable' : '')}
      disabled={discovery.status === 'loading'} onChange={(event) => {
        const model = discovery.models.find((item) => JSON.stringify([item.provider, item.id]) === event.target.value);
        if (!model) { update({ assistantProvider: '', assistantModel: '', assistantHfModelId: '' }); return; }
        if (!modelAvailable(model)) return;
        const hf = canonicalAssistantProviderId(model.provider) === 'local-transformers';
        update({ assistantProvider: model.provider, assistantModel: hf ? '' : model.id, assistantHfModelId: hf ? model.id : '' });
      }}>
      <option value="">{t('Profile default')}</option>
      {!selectedModel && hasCustomSelection && <option value="__unavailable" disabled>{settings.assistantModel || settings.assistantHfModelId || settings.assistantProvider} · {t('Unavailable')}</option>}
      {discovery.models.map((model) => <option key={JSON.stringify([model.provider, model.id])} value={JSON.stringify([model.provider, model.id])} disabled={!modelAvailable(model)}>
        {model.displayName || model.id} · {model.provider}{!modelAvailable(model) ? ` · ${t('Unavailable')}` : ''}
      </option>)}
    </select>)}
    <div className="model-setup">
      <p role="status">{discovery.status === 'loading' ? t('Loading models…') : discovery.status === 'error' ? t('Models could not be loaded.')
        : !discovery.models.some(modelAvailable) ? t('No available models found.') : null}</p>
      {(discovery.status === 'error' || !discovery.models.some(modelAvailable)) && <p>{t('Configure a provider or start your local model service, then refresh.')}</p>}
      <div className="settings-actions"><button type="button" disabled={discovery.status === 'loading'} onClick={discovery.refresh}>{t('Refresh models')}</button><a href="#/system/settings">{t('Configure providers')}</a></div>
      {discovery.error && <details><summary>{t('Technical details')}</summary><p>{discovery.error.message}</p></details>}
    </div>
  </SettingsBlock>;
  return <div className="settings-shell">
    <aside className="settings-sidebar">
      <a className="back-to-app" href="#/"><ArrowLeft size={16} />{t('Back to app')}</a>
      <label className="settings-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('Search settings')} aria-label={t('Search settings')} /><kbd>{t('Filter')}</kbd></label>
      <div className="settings-links">{visibleGroups.map(({ group, items }) => items.length ? <section key={group}><span>{t(group)}</span>{items.map((item) => item === 'Security'
        ? <a key={item} href="#/system/settings">{t(item)}</a>
        : <button key={item} type="button" className={activeSection === item ? 'is-active' : ''} onClick={() => setActiveSection(item)}>{t(item)}</button>)}</section> : null)}
        {!visibleGroups.some(({ items }) => items.length) && <p role="status">{t('No settings found.')}</p>}
      </div>
      <div className="settings-account"><span className="avatar">{settings.operatorId.trim().slice(0, 2).toUpperCase() || 'IO'}</span><div><strong>{settings.operatorId}</strong><small>{t('Workspace')}</small></div></div>
    </aside>
    <main className="settings-content"><form className="settings-page" onSubmit={(event) => { event.preventDefault(); saveSettings(settings); setTheme(resolveThemeMode(settings.theme)); setStatus('Settings saved.'); }}>
      <header><span className="settings-page-icon"><CircleUserRound size={20} /></span><div><h1>{t(activeSection === 'General' ? 'Operator settings' : activeSection)}</h1><p>{t('Manage your workspace preferences.')}</p></div></header>
      {activeSection === 'General' && <>
        <SettingsBlock title={t('Operator profile')}>{row('Operator identity', 'Identity used for approval decisions.', <input aria-label={t('Operator identity')} value={settings.operatorId} onChange={(event) => update({ operatorId: event.target.value })} />)}</SettingsBlock>
        <SettingsBlock title={t('Workspace')}>{row('Language', 'Preferred interface language.', <select aria-label={t('Language')} value={settings.locale} onChange={(event) => update({ locale: event.target.value as PanelSettings['locale'] })}><option value="auto">{t('Automatic')}</option><option value="en">English</option><option value="tr">Türkçe</option></select>)}</SettingsBlock>
        <SettingsBlock title={t('Advanced')}>{row('Advanced system settings', 'Manage connection and security settings in the system panel.', <a href="#/system/settings">{t('Open system settings')}</a>)}</SettingsBlock>
      </>}
      {activeSection === 'Appearance' && <SettingsBlock title={t('Appearance')}>{row('Theme', 'Choose an interface theme.', <select aria-label={t('Theme')} value={settings.theme} onChange={(event) => update({ theme: event.target.value as PanelSettings['theme'] })}><option value="system">{t('System')}</option><option value="dark">{t('Dark')}</option><option value="light">{t('Light')}</option></select>)}</SettingsBlock>}
      {activeSection === 'Assistant' && <SettingsBlock title={t('Assistant')}>
        {row('Assistant profile', 'Default runtime profile for new tasks.', <input aria-label={t('Assistant profile')} value={settings.profile} onChange={(event) => update({ profile: event.target.value })} />)}
        {row('Default approval profile', 'Approval behavior within the current policy.', <select aria-label={t('Default approval profile')} value={settings.approvalProfile} onChange={(event) => update({ approvalProfile: event.target.value as PanelSettings['approvalProfile'] })}><option value="always_ask">{t('Always ask')}</option><option value="risk_based">{t('Risk-based approval')}</option><option value="policy_automatic">{t('Automatic within policy')}</option></select>)}
      </SettingsBlock>}
      {['Assistant', 'AI providers'].includes(activeSection) && models}
      {activeSection === 'Shortcuts' && <SettingsBlock title={t('Shortcuts')}>
        {row('Global search', 'Search projects, tasks, outputs and approvals.', <kbd>⌘/Ctrl K</kbd>)}
        {row('Terminal search', 'Search the focused terminal.', <kbd>Ctrl Shift F</kbd>)}
        {row('Close search', 'Dismiss the open search panel.', <kbd>Esc</kbd>)}
      </SettingsBlock>}
      <div className="settings-actions"><button type="submit">{t('Save settings')}</button>{status && <p role="status">{t(status)}</p>}</div>
    </form></main>
  </div>;
}

function SettingsBlock({ title, children }: { title: string; children: ReactNode }) {
  return <section className="settings-block"><h2>{title}</h2><div>{children}</div></section>;
}
function SettingsRow({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <div className="settings-row"><div><strong>{title}</strong><p>{description}</p></div>{children}</div>;
}
