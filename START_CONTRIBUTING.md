# Start Contributing

## What is this repository?

Cowork Local is the Cowork Team's product/platform repository: desktop runtime, UI/UX, workspaces, agents, MCP/connectors, security, and reusable platform foundations.

The Cowork Team owns architecture, product behavior, releases, the stable branch, final review, and merge. The FSG AI Core Team is a contributor for selected generic capabilities such as MCP integration, agent capabilities, orchestration/model-routing tests, evaluation/security integration, and reusable platform improvements.

## Where are Core AI tasks?

Use [fsg-ai-core-assets Issues/Project](http://34.143.229.138/gitea-admin/fsg-ai-core-assets) as the Core AI task source of truth. Pick and assign a contribution task there, then move it to `In Progress`.

Do not copy the Core AI backlog, golden datasets, CASAN assets, agent catalog, or evaluation repository into Cowork Local. Only source/artifacts required by an agreed Cowork runtime contract belong here.

## Make the change

Create a focused branch:

```bash
git switch -c core-ai/TL-xxx-short-name
```

For Cowork-native work use `feat/`, `fix/`, `test/`, `docs/`, `perf/`, or `refactor/`. Keep one logical change in one Pull Request.

Run the application from the parent directory with `python -m cowork_local`. Run the current automated test suite from this repository with:

```bash
python -m pip install -r requirements-test.txt
python -m pytest tests -q
```

Use environment variables for credentials; never commit `.env`, `~/.cowork_local/`, logs, customer data, or generated runtime files.

## Review and completion

Before opening a Pull Request, obtain Core AI pre-review and move the Core task to `Review`. Open the Pull Request in Cowork Local with the Core repository URL, issue, task ID, scope, validation evidence, and security impact. Then move the Core task to `Upstream Review`.

The Cowork Team may request changes or approve and merge. A Core AI task is `Done` only after the Cowork Pull Request is merged—not when implementation or Core AI review finishes. Record the Pull Request and merge reference in the Core issue.

See [CONTRIBUTING.md](CONTRIBUTING.md) for conventions and `docs/governance/` for ownership, review, and Definition of Done.
