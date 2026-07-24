import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { AppShell } from '../shell/AppShell';
import { CollectionPage } from '../pages/CollectionPage';
import { NewWorkPage } from '../pages/NewWorkPage';
import { TaskPage } from '../pages/TaskPage';
import { SettingsShell } from '../settings/SettingsShell';

export function ProductRouter() { return <BrowserRouter><AppShell><Routes><Route path="/" element={<NewWorkPage />} /><Route path="/task/:taskId" element={<TaskPage />} /><Route path="/library" element={<CollectionPage title="Library" body="Governed artifacts, evidence and exports." />} /><Route path="/approvals" element={<CollectionPage title="Approvals" body="Review approval work in the established governance surface." />} /><Route path="/settings" element={<SettingsShell />} /><Route path="*" element={<NewWorkPage />} /></Routes></AppShell></BrowserRouter>; }
