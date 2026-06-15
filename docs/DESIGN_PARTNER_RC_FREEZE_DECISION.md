# Design Partner RC Freeze Decision

The source of truth is the generated RC freeze manifest:

```text
artifacts/mainline-rc-freeze/manifest.json
```

The freeze can be considered ready only when:

- stack verification is `ready`,
- merge rehearsal is `pass`,
- required gate evidence is `pass`,
- artifact scan is `pass`,
- public desktop, live computer-use, and approval-free irreversible mutation remain blocked,
- raw persistence is false and evidence mode is hash-only.

Any false-ready, raw/secret marker, boundary opening, hash mismatch, or merge conflict blocks the freeze.
