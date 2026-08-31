# Cowork Local

Cowork Local is the internal AI cowork desktop platform. It provides a local-first desktop runtime, multi-turn conversational agents, workspace isolation, task scheduling, MCP connectors, security guardrails, and model routing.

---

## 🏛️ 4-Tier Clean Architecture

The codebase strictly adheres to **Clean Architecture** with unidirectional inward dependencies:

```text
presentation/ (PySide6 UI, Shell, NavRail, Chat, Scheduling, Settings, Dashboard)
      │
      ▼
application/ (Pure Python Orchestration: Conversations, Scheduling, Workspaces, Monitoring, Routing)
      │
      ▼
domain/ (Pure Python: Entities, Immutable Execution Requests, Agent Events, Descriptors)
      ▲
      │
infrastructure/ (Adapters, LLM Providers, Atomic Persistence, Keyring SecretStore, MCP)
```

- **Domain & Application Layers**: 100% Pure Python (zero Qt/UI imports).
- **Single Responsibility**: Every production module is strictly `<= 400 LOC`.
- **Security & Durability**: API keys stored in OS Keyring; atomic JSON disk persistence.

---

## 🚀 Quick Start

### 1. Windows — two double-clicks

```
install.bat      once, to install the Python dependencies
run.bat          every time, to start the app
```

`install.bat` builds an isolated virtualenv under `%LOCALAPPDATA%\CoworkLocal`
(deliberately **outside** the repo — the quality gates walk the whole directory
tree, so a `.venv` in here would turn every vendored module into a Gate O
violation). Add `--dev` to also install the test dependencies, or `--system` to
skip the virtualenv and install into the Python already on `PATH`.

Both scripts also make the source importable under its package name. That step
is not optional: `python -m cowork_local` only resolves when the checkout
directory is literally named `cowork_local`, and the MS365 MCP server is
launched as a subprocess with `python -m cowork_local.mcp_servers.ms365_server`,
so a differently-named checkout breaks the app *and* its subprocesses. The
scripts create a junction instead of forcing anyone to rename their folder.

### 2. Any platform — run from source

From the **parent** of a checkout directory named `cowork_local`:

```bash
python -m cowork_local
```

### 3. Run Automated Tests
```bash
python -m pip install -r requirements.txt
pytest -q
```

There is one requirements file, not a runtime/test pair. A separate test file
would hold only `pytest`: 64 of the 108 test modules build real widgets, and 20
of them import PySide6 unguarded at module scope, so it would have to pull in
almost the whole runtime list anyway — two files for one near-identical list is
just a second place for the pins to drift.

---

## 🛡️ CASAN Quality Gate & Verification

Before submitting any Pull Request, run the unified CASAN Quality Gate:

```bash
# Run all 4 quality gates (Clean Arch, Secrets, LOC, and Pytest Suite)
python scripts/run_quality_gate.py

# Run static and architectural guards only (fast check)
python scripts/run_quality_gate.py --skip-tests
```

Individual guard scripts:
- **Clean Architecture Import Guard**: `python scripts/check_imports.py`
- **Secrets & Plaintext Audit**: `python scripts/audit_security.py`
- **Single Responsibility LOC Guard**: `python scripts/check_loc.py --max-lines 400`
- **Release E2E Smoke Test**: `pytest tests/e2e/test_smoke.py -v`

---

## 🤝 Contributing & Recipes

- **Quick Start Guide**: See [START_CONTRIBUTING.md](START_CONTRIBUTING.md).
- **Contributor Recipes**: See [docs/governance/contributor-recipes.md](docs/governance/contributor-recipes.md) for step-by-step recipes to:
  1. Add a new AI Model Provider.
  2. Add a new Built-in Tool / MCP Server.
  3. Add a new Screen / Tab / Widget.
- **Security Policy**: See [SECURITY.md](SECURITY.md).
