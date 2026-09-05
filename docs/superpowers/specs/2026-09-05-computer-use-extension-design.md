# Computer-use extension isolation

Approved direction: remove computer use from the main product UI and promise, retain its code as an optional module, and pause active development until a concrete user workflow requires desktop interaction.

The core distribution must import, install, start and run its release checks without desktop drivers or the optional module. Preserve existing governance denial of unqualified device actions and historical audit data. Core capability contracts may retain disabled compatibility fields; they must not probe desktop providers or claim execution support.

Move the Python implementation into `extensions/computer-use`, distributed as `imperaos-computer-use` with its own CLI. The extension depends on core, never the reverse. Existing configuration schemas can remain for compatibility, with computer use disabled in every normal profile. Dedicated extension tests and qualification checks are opt-in and must not become a core release prerequisite.

Remove computer-use controls, cards and background requests from the panel. Preserve ordinary agent tasks, approvals, run history and terminal functionality. Preserve the user's existing change in `apps/operator-panel/src-tauri/src/terminal.rs`.

Verification: core import with extension unavailable; core CLI help and capability contract; extension install and help; targeted governance/config/release tests; panel TypeScript build and affected tests. No live desktop actions are required.
