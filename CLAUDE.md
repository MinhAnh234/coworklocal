# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Cowork Local (user-facing brand "Cowork-Local BamBOO") is a local-first PySide6 desktop app: multi-turn AI agents, per-project workspaces with GraphRAG, scheduled agent tasks (Kanban), MCP connectors, a sandbox security layer, model routing, and a monitoring dashboard. User config lives in `~/.cowork_local`. The internal name `cowork_local` / `APP_NAME` must not be rebranded. Only `DISPLAY_NAME` is the brand.

## The package-name quirk (read first)

The repository root **is** the `cowork_local` package: `__init__.py` and `__main__.py` sit at the root, and code imports itself as `cowork_local.*` or through relative imports. This checkout's folder is not named `cowork_local`, so:

- **Running the app:** `python -m cowork_local` works only from the parent of a folder literally named `cowork_local`. On Windows, `install.bat` (once; add `--dev` for test deps, `--system` to skip the venv) builds a venv under `%LOCALAPPDATA%\CoworkLocal` and creates a junction `%LOCALAPPDATA%\CoworkLocal\launcher\<key>\cowork_local` pointing at this checkout. After that, use `run.bat`. The MS365 MCP server is spawned as `python -m cowork_local.mcp_servers.ms365_server`, so the junction is needed for subprocesses too.
- **Never create a `.venv` inside the repo.** The quality gates walk the whole tree.
- **Tests:** the root `conftest.py` and `tests/conftest.py` bind `sys.modules["cowork_local"]` to this checkout, so pytest works whatever the folder is named. Tests use both import styles: top-level (`from providers.base import ...`) and qualified (`from cowork_local.core... import ...`). Characterization tests that spawn `python -c "from cowork_local..."` subprocesses still need a real `cowork_local` directory on `PYTHONPATH`. CI checks out into `cowork_local/` for this reason.

## Commands

```bash
python -m pip install -r requirements.txt       # single requirements file (includes pytest)
python -m pytest tests -q                       # full suite (what CI runs)
python -m pytest tests/unit/test_schedule_calculator.py -q          # one file
python -m pytest tests/unit/test_schedule_calculator.py -k name -q  # one test
python -m pytest tests/e2e/test_smoke.py -v     # release smoke test

python scripts/run_quality_gate.py              # all CASAN gates + pytest
python scripts/run_quality_gate.py --skip-tests # static gates only
python scripts/check_imports.py                 # domain/ + application/ must not import PySide6/PyQt/ui/app
python scripts/audit_security.py                # no plaintext credentials (CI also runs --self-test)
python scripts/check_loc.py                     # <= 400 lines per production file
python scripts/check_orphan_modules.py          # every production module must be reachable by import
```

Widget tests run headless with `QT_QPA_PLATFORM=offscreen`. `tools/check_*.py` are standalone offscreen smoke checkers against a real `MainWindow` built on a copy of `~/.cowork_local` (for example `python tools/check_nav.py`). Some of them still import private names re-exported from `app.py`, so keep those re-exports. Set `COWORK_PERF_TRACE=1` to log timing spans from `performance.py`.

## Architecture

Target design is 4-tier Clean Architecture (`docs/architecture/ADR-001-layered-architecture.md`):

- `domain/`: pure stdlib entities, frozen request snapshots (`ConversationExecutionRequest`), `AgentEvent`, tool/provider descriptors, `ScheduleCalculator`.
- `application/`: pure-Python use-case services (conversations, model_routing, scheduling, workspaces, monitoring, workflows). **No Qt.** Must run headless.
- `infrastructure/`: adapters: config (`JsonConfigRepository` over `AtomicJsonFile`), OS-keyring `SecretStore`, providers, MCP (`McpToolSourceManager`), sandbox, filesystem, telemetry, and Qt bridges (`infrastructure/qt`).
- `presentation/`: PySide6 widgets by feature (`shell`, `chat`, `co4e`, `dashboard`, `scheduling`, `workspace`, `monitoring`, `graph`, `settings`, ...). Widgets call `application/` services. They don't touch persistence or run LLM calls on the GUI thread. Agent work runs in worker threads and reaches the UI as `AgentEvent`s through Qt signal bridges.

The refactor is **incomplete**. Legacy top-level packages are still live and imported by the app:
- `ui/`: older tabs such as `cowork_tab`, `workspace_tab`, `monitoring_tab`, `settings_dialog`, `chat_panel`, and `co4e_*`.
- `core/`: agents, the Co4E flow runner, task scheduler, skills, tools, audit/usage tracking, routing.
- `providers/`: `base`, `anthropic`, `openai_compat`, `factory`.
- `security/`: validators, command risk classifier.
- Root modules: `config.py`, `state.py`.

`docs/architecture/dormant-code.md` lists deprecated pieces, such as `state.py::active_project_id` and the monolithic `core/tools.py`. New layers must not import dormant code.

Wiring:
- `__main__.py` → `app.run()`.
- `presentation/shell/bootstrap.py` is the **Composition Root**. It builds `AppContext` (`state.py`) around `JsonConfigRepository` plus `KeyringAdapter`, falling back to the config file when no keyring exists.
- `run()` then seeds the built-in skills (`skill_library/*.skill`) and the Co4E flows, applies the theme, and opens `presentation/shell/main_window.MainWindow`.
- Pages are registered in `presentation/shell/page_registry.py`.

Other cross-cutting pieces:
- `i18n/`: `tr(key, **kw)` with en/ja/vi (default `vi`). Long-lived widgets must use `bind_text(...)` or `on_language_changed(...)` so a language switch re-applies their text. Transient dialogs just call `tr()` at construction.
- `theme/`: palettes and QSS. Use theme tokens, not hard-coded colors.
- `mcp_servers/`: bundled MCP servers (MS365, project_context).
- `agent/`: a markdown instruction library for UI/UX bug-fix agents, not runtime code.

Step-by-step recipes for adding a provider, a tool or MCP server, or a screen are in `docs/governance/contributor-recipes.md`.

## Rules enforced by gates and review

- **400-line limit** for every production file. This covers `domain`, `application`, `infrastructure`, `presentation`, `ui`, `core`, `providers`, `security`, `mcp_servers`, `i18n`, `theme`, and root `.py` files. Legacy oversized files have per-file caps in `scripts/check_loc.py` that may only go down. Split files; never raise a cap.
- **No orphan modules.** `check_orphan_modules.py` has an `ALLOWLIST` that may only shrink. Wire up or delete a module instead of allowlisting it.
- **Secrets** belong in the OS keyring, never in `config.json` or the code. `.env.example` is not auto-loaded. Tests never use live provider credentials (use `tests/fakes/`: `FakeProvider`, `FakeToolExecutor`, `FakeToolPolicyGateway`, `FakeConfigRepository`/`FakeSecretStore`, `FakeClock`, ...).
- **Test layout:** `tests/unit` (fast, no I/O), `tests/contracts`, `tests/integration` (Qt offscreen), `tests/characterization` (pinned legacy behavior during refactors), `tests/e2e`, `tests/ui`, plus flat `tests/test_*.py`.
- **Startup housekeeping** (seeding, pruning) is wrapped in `try/except` and must never block app launch.
- **Comments:** the ADR asks for English comments. Existing code mixes English and Vietnamese docstrings and comments, so match the surrounding file.

## Git workflow

- Branches: `feat/`, `fix/`, `test/`, `docs/`, `perf/`, `refactor/<short-desc>`. Core AI work uses `core-ai/<task-id>-<name>`.
- Commits use Conventional Commit prefixes (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `perf:`, `chore:`).
- One logical change per PR, using `.gitea/PULL_REQUEST_TEMPLATE.md`. The remote is a Gitea instance, and CI (`.gitea/workflows/ci.yaml`, Python 3.11) runs on PRs to `main`.
- Critical areas listed in `SECURITY.md` get extra review.
