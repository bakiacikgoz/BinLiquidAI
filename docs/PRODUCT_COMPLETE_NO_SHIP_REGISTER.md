# Product-Complete No-Ship Register

The product-complete gate must block ready claims when any blocker below is open.

| Reason code | Boundary |
|---|---|
| `ASSISTANT_PREVIEW_IN_PRODUCT_MODE` | Assistant cannot return preview fixtures in product mode. |
| `ASSISTANT_MODEL_DISCOVERY_FAKE` | Model picker must use real discovery or setup diagnostics. |
| `OPERATOR_INERT_PRIMARY_ACTION` | Primary actions must work or be disabled with a reason. |
| `ENTERPRISE_WORKSPACE_SETUP_BYPASS` | Enterprise ready claims require identity/workspace readiness. |
| `AGENT_ENROLLMENT_RAW_TOKEN_LEAK` | Enrollment raw tokens are shown-once only and never persisted. |
| `EXTERNAL_AGENT_NOT_ENROLLED_ACCEPTED` | Unknown or unenrolled external agents cannot submit actions. |
| `MEMORY_CROSS_WORKSPACE_ALLOWED` | Workspace memory boundaries must deny cross-workspace access. |
| `COMPUTER_USE_UNQUALIFIED_CLAIM` | Live computer-use remains qualification-gated. |
| `PUBLIC_CLOUD_SAAS_OUT_OF_SCOPE` | Public multi-tenant SaaS is outside this product-complete scope. |
| `PUBLIC_INSTALLER_UNSIGNED_CLAIM` | Public signed installer claims require signing/notarization evidence. |

Accepted external boundaries can be documented, but they do not make an unsupported
claim shippable. The final closure gate emits `no_ship_register.json` for the
current head SHA.
