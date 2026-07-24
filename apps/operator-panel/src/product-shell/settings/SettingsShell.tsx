import { useState } from 'react';

import { loadSettings, resolveThemeMode, saveSettings, type PanelSettings } from '../../settings';
import { useProductShellStore } from '../state/productShellStore';

export function SettingsShell() {
  const [settings, setSettings] = useState<PanelSettings>(() => loadSettings());
  const [status, setStatus] = useState('');
  const setTheme = useProductShellStore((state) => state.setTheme);
  const update = <Key extends keyof PanelSettings>(key: Key, value: PanelSettings[Key]) => {
    setSettings((current) => ({ ...current, [key]: value }));
    setStatus('');
  };
  const save = () => {
    saveSettings(settings);
    setTheme(resolveThemeMode(settings.theme));
    setStatus('Settings saved to the governed operator profile.');
  };
  return <section className="ps-collection"><p className="ps-eyebrow">SETTINGS</p><h1>Operator settings</h1><p>These controls update the existing ImperaOS operator profile; advanced system settings remain available in the legacy route.</p><form className="ps-settings" onSubmit={(event) => { event.preventDefault(); save(); }}><label>Operator identity<input aria-label="Operator identity" value={settings.operatorId} onChange={(event) => update('operatorId', event.target.value)} /></label><label>Assistant profile<input aria-label="Assistant profile" value={settings.profile} onChange={(event) => update('profile', event.target.value)} /></label><label>Language<select aria-label="Language" value={settings.locale} onChange={(event) => update('locale', event.target.value as PanelSettings['locale'])}><option value="auto">Automatic</option><option value="en">English</option><option value="tr">Türkçe</option></select></label><label>Theme<select aria-label="Theme" value={settings.theme} onChange={(event) => update('theme', event.target.value as PanelSettings['theme'])}><option value="system">System</option><option value="dark">Dark</option><option value="light">Light</option></select></label><button type="submit">Save settings</button></form>{status ? <p role="status">{status}</p> : null}<a href="#/system/settings">Open advanced legacy settings</a></section>;
}
