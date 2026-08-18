# Branding and Compatibility

ImperaOS is the current public project and product name. BinLiquid and AegisOS are
historical and runtime names retained where compatibility requires them.

- `imperaos` is the preferred public CLI.
- `binliquid` and `aegis` remain compatibility CLI aliases.
- The `binliquid.*` Python namespace remains supported.
- Legacy environment variables, configuration keys, storage paths, serialized values,
  and internal runtime identifiers remain unchanged until a dedicated migration exists.
- Historically accurate documents may retain their original names; new user-facing
  documentation should use ImperaOS.

A future namespace migration must define compatibility and deprecation periods and
include serialization, configuration, storage, packaging, and migration tests. It must
not be performed as a mechanical search-and-replace.
