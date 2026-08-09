# Review Policy

Normal Cowork changes follow the Cowork Team's reviewer policy.

Core AI contributions require two review stages:

1. Core AI internal/pre-review.
2. Cowork Team final review and merge decision.

Additional scrutiny is required for permissions, credentials, MCP write/exec, sandboxing, network access, TLS, customer/project isolation, security rules, model routing/fallback, and data deletion. These changes must not be auto-merged merely because automated checks pass.

Branch protection should prevent force-push and deletion of the stable branch, prefer Pull Requests, and require CI after an Actions runner is available. Core AI contributors must not be configured as Cowork final approvers by process convention.
