# Security Policy

Do not open a public issue containing credentials, customer data, exploit details, or production logs. Report sensitive findings privately to the Cowork Team repository maintainers through the organization's approved security channel.

Before requesting review:

- remove secrets, tokens, private keys, customer documents, PII, and local runtime data;
- use environment variables or the approved secret manager for credentials;
- document permission, credential, network, TLS, isolation, and data-handling impact;
- add focused tests for security boundaries when practical;
- rotate any credential that may have been exposed.

Changes involving permissions, credentials, MCP write/exec, sandboxing, network access, TLS, customer/project isolation, security rules, model routing/fallback, or data deletion require additional Cowork Team scrutiny. Passing CI is not sufficient approval for a critical change.

If a secret is found in Git history, stop distribution and notify the Cowork Team. Do not rewrite shared history or force-push without an explicit, coordinated remediation plan.
