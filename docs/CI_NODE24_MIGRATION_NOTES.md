# CI Node 24 Migration Notes

GitHub Actions currently emits Node.js 20 deprecation warnings for several JavaScript actions. These warnings are tracked as release hygiene evidence, not as blockers while CI jobs pass.

## Policy

- Warning only and checks pass: non-blocking.
- Actual JavaScript action runtime failure: blocking.
- Unmaintained action with a security risk: blocking.
- Workflow changes should be made deliberately and verified in CI.

## Inventory

Generate the current action inventory:

```bash
make ci-node24-inventory
```

Artifacts:

- `artifacts/ci/node-action-inventory.json`
- `artifacts/ci/NODE_ACTION_INVENTORY.md`

The inventory marks known warning-producing actions such as `actions/checkout@v4`, `actions/setup-node@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`, and `pnpm/action-setup@v4` as `node20` review items. It does not assume a safe replacement without a workflow test.

## Migration Approach

1. Keep existing CI behavior passing.
2. Review official action releases for Node 24-compatible versions.
3. Update one workflow family at a time.
4. Run the affected workflow and confirm the deprecation warning is gone.
5. Keep the inventory artifact in beta operations packs until the warning is fully cleared.

`FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` can be tested on a canary workflow, but it should not be globally enabled until action compatibility is verified.
