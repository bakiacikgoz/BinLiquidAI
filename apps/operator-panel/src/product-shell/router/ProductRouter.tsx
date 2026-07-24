import { HashRouter, Route, Routes } from 'react-router-dom';

import { AppShell } from '../shell/AppShell';
import { CollectionPage } from '../pages/CollectionPage';
import { NewWorkPage } from '../pages/NewWorkPage';
import { TaskPage } from '../pages/TaskPage';
import { SettingsShell } from '../settings/SettingsShell';

export function ProductRouter() { return <HashRouter><AppShell><Routes><Route path="/" element={<NewWorkPage />} /><Route path="/task/:taskId" element={<TaskPage />} /><Route path="/task/:taskId/workspace" element={<TaskPage />} /><Route path="/library" element={<CollectionPage title="Library" body="Governed artifacts, evidence and exports." />} /><Route path="/approvals" element={<CollectionPage title="Approvals" body="Review approval work in the established governance surface." />} /><Route path="/agents" element={<CollectionPage title="Agents" body="Registered operators and governed agent activity." />} /><Route path="/automations" element={<CollectionPage title="Automations" body="Automation status and evidence." />} /><Route path="/settings" element={<SettingsShell />} /><Route path="/settings/:section" element={<SettingsShell />} /><Route path="/system/*" element={<CollectionPage title="System" body="System operations remain on the governed legacy surface." />} /><Route path="*" element={<NewWorkPage />} /></Routes></AppShell></HashRouter>; }
