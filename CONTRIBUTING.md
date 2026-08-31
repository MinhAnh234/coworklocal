# Contributing to Cowork Local

Cowork Local is owned by the Cowork Team. Contributions from the FSG AI Core Team are welcome for selected generic capabilities, but final review and merge remain with the Cowork Team.

## Workflow

```text
Core AI Issue -> Pick task -> Branch on cowork-local -> Implement -> Tests
-> Core AI pre-review -> Cowork Pull Request -> Cowork Team review -> Merge
-> Core AI Issue Done
```

Core AI execution source of truth is the [fsg-ai-core-assets issue/project system](http://34.143.229.138/gitea-admin/fsg-ai-core-assets). Do not duplicate its complete backlog here.

Board states for a Core AI contribution mean:

- `Review`: Core AI internal/pre-review.
- `Upstream Review`: the Cowork Pull Request is waiting for Cowork Team review.
- `Done`: the Cowork Team merged the Pull Request into the stable branch.

## Branches

Use a short, focused branch name:

```text
feat/<short-description>
fix/<short-description>
test/<short-description>
docs/<short-description>
perf/<short-description>
refactor/<short-description>
```

Core AI contributions use:

```text
core-ai/<task-id>-<short-name>
```

Examples: `core-ai/TL-065-co4e-if-switch`, `core-ai/TL-146-model-routing-tests`, and `core-ai/TL-148-superpowers-phase1`.

## Commits

Prefer the existing lightweight Conventional Commit prefixes: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `perf:`, and `chore:`. Scopes are optional, for example `test(routing): verify model fallback policy`.

## Development and validation

Run the application from the parent directory with `python -m cowork_local`. The current reliable test command is:

```bash
python -m pip install -r requirements.txt
python -m pytest tests -q
```

Also run any focused checks relevant to the area you changed. Never use live provider credentials in automated tests.

## Pull Requests

One logical change equals one Pull Request. Do not combine unrelated task IDs into a mega PR; split large work into vertical, reviewable slices.

Complete the Pull Request template, including scope, test evidence, compatibility, and security impact. A Core AI Pull Request must include the full Core repository URL, Core issue URL or number, and Core task ID. Use a full URL if cross-repository linking is unavailable.

Normal Cowork changes follow the Cowork Team reviewer policy. Core AI contributions require both Core AI pre-review and Cowork Team final review. Critical areas listed in [SECURITY.md](SECURITY.md) receive additional scrutiny and are never auto-merged solely because tests pass.

The detailed ownership, review, and completion rules are in `docs/governance/`.
