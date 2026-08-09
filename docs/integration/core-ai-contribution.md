# FSG AI Core Contribution Integration

Core AI task execution source of truth:

[fsg-ai-core-assets Issues / Project](http://34.143.229.138/gitea-admin/fsg-ai-core-assets)

Cowork source changes:

`cowork-local` Pull Requests

Typical relationship:

```text
Core Issue #42 -> cowork-local PR #18 -> Cowork Review -> Merged
-> Core Issue #42 Done
```

The Core board lifecycle is:

```text
Backlog -> Ready -> In Progress -> Review -> Upstream Review -> Done
```

- `Review` means Core AI internal/pre-review.
- `Upstream Review` means the Cowork Pull Request is waiting for Cowork Team review.
- `Done` means the Cowork Team merged the Pull Request.

Every Core AI Pull Request should reference:

```text
Core Repo: http://34.143.229.138/gitea-admin/fsg-ai-core-assets
Core Issue: #<number> (prefer the full issue URL)
Core Task: T?-??
```

## Promotion model

```text
Core Asset -> Evaluated -> Candidate for Upstream -> Cowork PR
-> Cowork Review -> Upstream Merged
```

Not every Core asset needs promotion. Do not create a `core-ai-assets/` copy here. Golden datasets, CASAN, internal agent catalogs, knowledge/RAG collections, and Core evaluation assets remain Core-owned unless the Cowork runtime needs a specific artifact under an agreed integration contract.
