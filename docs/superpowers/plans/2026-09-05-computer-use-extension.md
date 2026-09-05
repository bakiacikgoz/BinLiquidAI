# Computer-use Extension Implementation Plan

**Goal:** Keep the main product independent of the paused desktop automation experiment.
**Architecture:** Optional Python distribution and CLI under extensions; core retains only disabled compatibility contracts. Panel stops exposing or polling computer-use operations.
**Tech Stack:** Python/Typer/Hatch, React/TypeScript/Tauri, pytest/Vitest.
**Spec:** ../specs/2026-09-05-computer-use-extension-design.md

## Global constraints
- Preserve existing local terminal.rs edits and historical audit compatibility.
- No live desktop execution, release publication or remote push.
- Work in the current feature checkout so the result is available in the user's project.

## Tasks
- [x] Core and extension: move implementation to extensions/computer-use/src/imperaos_computer_use; extract CLI commands and helpers; remove core imports and execution advertisement; default config disabled. Verify import isolation, CLI contracts and extension commands.
- [x] Panel: remove active computer-use UI and polling; retain archived source separately when appropriate. Verify affected component tests, TypeScript and build.
- [x] Release and documentation: isolate dedicated extension tests/gates, update primary README/product boundary and add paused-extension guide. Keep rejection of unsupported claims. Verify release checks and discovery do not need extension.
- [x] Integration: run targeted Python and frontend checks, inspect diff and report actual evidence and limitations.

## Decisions
- The user's explicit approval covers the previously proposed architecture; no repeated approval step.
- Existing config/contract fields remain as disabled compatibility data; desktop implementations must leave the core wheel.

## Verification result
- Core: 1,067 passed with short Windows --basetemp.
- Extension: 209 passed, 9 live/opt-in skips.
- Frontend: 37 affected tests and 3 Chromium E2E scenarios passed; TypeScript and production Vite build passed.
- Ruff and git diff --check passed. Both distributions built; core wheel excludes desktop implementation.
- Review findings resolved: removed desktop quick action and core readiness dependency; historical evidence cannot reopen desktop claim.
- Preserved all 49 original Python implementation files and prior local terminal.rs edit.
