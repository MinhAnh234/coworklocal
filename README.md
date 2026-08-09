# Cowork Local

Cowork Local is the internal AI cowork desktop platform owned by the Cowork Team. It provides the Cowork runtime, workspace and agent experiences, MCP/connectors, security controls, and model routing foundation.

The Cowork Team owns this product and its stable branch. The FSG AI Core Team contributes selected reusable capabilities through branches and Pull Requests; it is not the owner or final merger of this repository.

## Quick start

The imported application is a Python/PySide6 package. Run it from the directory that contains `cowork_local`:

```bash
python -m cowork_local
```

The source snapshot does not include a complete runtime dependency manifest. Use the Cowork Team's supported runtime environment until that packaging contract is documented. The reliable automated test surface currently checked by CI is:

```bash
python -m pip install -r cowork_local/requirements-test.txt
python -m pytest cowork_local/tests -q
```

When already inside this repository, run `python -m pytest tests -q`.

Configuration and runtime data live under `~/.cowork_local/`. Provider keys and local unlock codes must be supplied through environment variables or an approved secret manager; see `.env.example`.

## Contributing

Start with [START_CONTRIBUTING.md](START_CONTRIBUTING.md), then read [CONTRIBUTING.md](CONTRIBUTING.md). Core AI task execution remains in [fsg-ai-core-assets](http://34.143.229.138/gitea-admin/fsg-ai-core-assets); source changes are reviewed as Pull Requests in this repository.

Security concerns should follow [SECURITY.md](SECURITY.md). Ownership and completion rules are documented under `docs/governance/`.
