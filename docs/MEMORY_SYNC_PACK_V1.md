# Memory Sync Pack v1

Memory Sync Pack v1 is file based. It does not open a network listener and does not implement distributed sync.

Export writes a JSON document with a manifest and redacted memory records. The manifest includes record count, source environment and a hash over the record payload. Raw content export is blocked.

Import supports dry-run and apply. Apply is blocked unless `memory.sync.enabled=true`, cross-environment import is explicitly allowed and an approval id is provided when `import_apply_requires_approval=true`.

Conflict detection checks targeted memory state versions before apply. Conflicts are reported and skipped; silent overwrite is not allowed.
