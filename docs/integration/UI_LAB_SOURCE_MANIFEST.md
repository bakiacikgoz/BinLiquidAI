# ImperaOS UI Lab source manifest

- Source path: `/Users/baki/Documents/ImperaOS-UI-Lab`
- Frozen source SHA: `165208e90dd37376d5f0a21df22b7a1e7756aab5`
- Target base SHA: `0a9c4ea5a6e26a3b32a9dd327ec1d7154ac39376`
- Source validation: 39 Node tests passed; `pnpm lint` and `pnpm build` passed on 2026-07-24.

## Imported design contract

The source supplies the visual product model: the three-column shell, task hierarchy,
composer, conversation, workspace, context rail, bottom dock, collections and settings.
Its React 19/Vite/Tauri 2 dependencies were reconciled with the Operator Panel's React
19/Vite/Tauri 2 stack. The target adds `react-router-dom` 7.18 and `zustand` 5.0.

## Explicitly not imported into production

`src/mocks/**` and `src/stores/demoStore.ts` are fixtures only. Product Shell loads no
module from the UI Lab checkout and no mock module. Runtime actions are delegated to the
existing Operator Panel bridge, assistant runtime and Artifact Workspace.

## Style decision

The source's tokens and surface grammar are recreated in the scoped
`.imperaos-product-shell-v2` namespace, preventing a global CSS collision with the legacy
panel while preserving its information density and dark/light palette.
