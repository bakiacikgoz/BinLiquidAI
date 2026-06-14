# Design Partner Support Escalation

For handoff incidents, share status and hashes, not raw data.

Include:

- handoff manifest path;
- release train status;
- first-run drill status;
- blocker and warning reason codes;
- artifact ids and hashes;
- claim boundary card;
- support bundle manifest status.

Do not include:

- raw prompts;
- raw responses;
- screenshots;
- API keys, tokens, passwords, private keys;
- direct personal contact/payment identifiers.

If the verifier reports `HANDOFF_SECRET_OR_RAW_MARKER_DETECTED`, delete the
generated pack, fix the source artifact, rerun the scanner, and rebuild.
