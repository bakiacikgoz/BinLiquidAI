# UI Lab component map

| UI Lab source | Product Shell destination | Product adapter |
| --- | --- | --- |
| `app/App.tsx` | `product-shell/ProductShellApp.tsx` | Browser router and legacy rollback |
| `shell/AppShell.tsx`, `Sidebar.tsx` | `shell/AppShell.tsx`, `shell/Sidebar.tsx` | Product task selection state |
| `pages/NewWorkPage.tsx`, `TaskPage.tsx` | `pages/*.tsx` | governed assistant session |
| `composer/Composer.tsx` | `composer/Composer.tsx` | existing assistant runtime hook |
| `conversation/ConversationView.tsx` | `conversation/ProductConversationView.tsx` | streamed assistant turns |
| `workspace/WorkSurface.tsx` | `workspace/WorkSurface.tsx` | Artifact Workspace handoff |
| `context-rail/ContextRail.tsx` | `context-rail/ContextRail.tsx` | selected task context |
| `bottom-dock/BottomDock.tsx` | `bottom-dock/BottomDock.tsx` | run state and audit activity |
| `settings/SettingsShell.tsx` | `settings/SettingsShell.tsx` | existing panel settings link |

All target modules are authored/adapted in this repository; they do not import from the
UI Lab checkout or its mock/demo modules.
