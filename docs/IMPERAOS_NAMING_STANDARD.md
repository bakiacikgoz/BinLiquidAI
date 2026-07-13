# ImperaOS Naming Standard

`branding/identity.json` is the source of truth for product identity. Product surfaces,
packaging, runtime resources, telemetry, and documentation must use the values from that
contract without introducing spelling or casing variants.

## Product text

- Write the product name as `ImperaOS`, with an uppercase `I`, uppercase `OS`, and no space.
- Write the operator application as `ImperaOS Operator Panel`.
- Do not derive display names by title-casing technical identifiers. Read them from the
  identity contract.

## Technical identifiers

- Use lowercase `imperaos` for the slug, Python distribution, Python package, and CLI command.
- Use uppercase `IMPERAOS` as the environment-variable prefix. Environment variables begin
  with `IMPERAOS_` followed by the setting name.
- Use `.imperaos` for the state root and `imperaos-runtime` for the runtime resource directory.
- Use `imperaos_` as the metric prefix.
- Use `com.imperaos.operatorpanel` as the operator bundle identifier.
- Use `imperaos.com` for the product domain and `bakiacikgoz/ImperaOS` for the repository.

When a new surface needs an identity value, extend the canonical contract and its schema first,
then update consumers. Do not create local aliases or independently maintained copies.
