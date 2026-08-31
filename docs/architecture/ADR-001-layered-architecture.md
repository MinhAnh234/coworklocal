# ADR-001: 4-Tier Clean Architecture for Desktop Local Application

* **Status**: ACCEPTED / ENFORCED
* **Date**: 2026-08-21
* **Deciders**: Team Duy (Tech Lead & AI Runtime), Team Nam (Governance & Automation), Team Hoa (Workspace & Scheduling)
* **Target Project**: Cowork Local (Cowork-Local BamBOO)

---

## 1. Context and Problem Statement

Cowork Local is a desktop application written in Python using PySide6 (Qt) and designed for local-first execution.
Historically, the codebase suffered from architectural coupling across layers:
1. **God-Widget Problem**: Monolithic UI widgets (e.g., `ui/chat_panel.py` >1,800 LOC, `ui/co4e_tab.py` >1,400 LOC) mixed UI rendering, network I/O, business rules, filesystem operations, and background worker lifecycle.
2. **Untestable Business Logic**: Core algorithms (model routing, conversation turn management, schedule calculation) were tightly coupled to `PySide6` widgets or `QTimer`, making unit testing in headless CI environments impossible without a graphical display server.
3. **Circular Dependencies & Global State Leaks**: Uncontrolled module imports (`model_pricing.py` ↔ `usage_tracker.py`, `agent_security.py` ↔ `agent_security_alert.py`) and mutable global state (`state.py::AppContext.active_project_id`) caused race conditions in background task runs.

---

## 2. Decision: 4-Tier Clean Architecture

We enforce a strict **4-Tier Clean Architecture** based on the Dependency Inversion Principle:

```text
┌─────────────────────────────────────────────────────────────┐
│                      PRESENTATION                           │
│  (PySide6 Widgets, Dialogs, Qt Signals/Slots, View Models)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ depends on
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      APPLICATION                            │
│  (Use Case Services, Turn Orchestrators, Route Dispatchers) │
│             *** STRICTLY PURE PYTHON (0 Qt) ***             │
└──────────────────────────────┬──────────────────────────────┘
                               │ depends on
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   DOMAIN & RUNTIME CORE                     │
│  (Entities, Value Objects, Domain Events, Tool Descriptors)  │
│             *** STRICTLY PURE PYTHON (0 Qt) ***             │
└──────────────────────────────▲──────────────────────────────┘
                               │ implemented by
┌──────────────────────────────┴──────────────────────────────┐
│                     INFRASTRUCTURE                          │
│  (LLM Providers, Keyring Secrets, Atomic Persistence, MCP)  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Layer Definitions and Responsibilities

### Tier 1: Presentation Layer (`presentation/`)
* **Responsibilities**: UI component layout, user event capture, progress display, visual animations, confirmation dialog triggers.
* **Allowed Imports**: `PySide6.*`, `application.*`, `domain.*`.
* **Forbidden**: Direct database queries, raw LLM API calls, disk writes outside UI cache, executing tool commands directly.
* **Constraints**: Every widget file must strictly be **under 400 lines of code (LOC)**.

### Tier 2: Application Layer (`application/`)
* **Responsibilities**: Orchestrate single use cases (e.g. `ConversationApplicationService`, `RoutingApplicationService`, `TaskApplicationService`). Convert UI requests into domain requests, coordinate domain services with infrastructure adapters.
* **Allowed Imports**: `domain.*`, `infrastructure.*` interfaces/contracts, standard Python libraries.
* **Forbidden**: `PySide6`, `PyQt5`, `PyQt6`, `ui.*`, `app.*`.
* **Nature**: **100% Pure Python**. Must be executable and testable in headless CI environments without a display driver.

### Tier 3: Domain Layer (`domain/`)
* **Responsibilities**: Core domain models, frozen DTO snapshots (`ConversationExecutionRequest`), typed event streams (`AgentEvent`), descriptors (`ToolDescriptor`, `ProviderDescriptor`), deterministic calculation algorithms (`ScheduleCalculator`).
* **Allowed Imports**: Standard Python library only (`dataclasses`, `typing`, `enum`, `datetime`, `pathlib`, `abc`).
* **Forbidden**: `PySide6`, `PyQt*`, `requests`, `sqlalchemy`, filesystem mutations, OS network calls.
* **Nature**: Completely isolated and zero-dependency core.

### Tier 4: Infrastructure Layer (`infrastructure/`)
* **Responsibilities**: Adapters for external systems (OpenAI/Anthropic/Ollama/FPT providers, OS Keyring via `SecretStore`, `AtomicJsonFile` persistence, MCP child processes, filesystem tools).
* **Allowed Imports**: Third-party SDKs, OS libraries, `domain.*`.
* **Forbidden**: `presentation.*`, `PySide6.QtWidgets`.

---

## 4. Architectural Rules and Non-Negotiable Invariants

1. **Zero Qt in Business Logic**:
   - `domain/` and `application/` must never import `PySide6` or `PyQt*`.
   - Verified via AST parser script `scripts/check_imports.py`.
2. **Immutable Request Snapshots**:
   - Turns are initiated using immutable frozen dataclasses (`ConversationExecutionRequest`) to decouple runtime state from mutable UI state.
3. **Thread Safety and Signal Decoupling**:
   - AI generation and tool calls run asynchronously in worker threads.
   - UI updates occur strictly on the Qt main thread by consuming `AgentEvent` streams through Qt Signal bridges.
4. **Single Responsibility and Modularity**:
   - Production files must stay within **400 LOC**.
5. **English In-Code Comments**:
   - Every modified or created line/block must include concise English comments explaining design decisions and processing logic.

---

## 5. Consequences and Compliance

* **Positive**:
  - Full testability: Unit tests run in milliseconds without GUI or network mocks.
  - Zero circular dependencies: Clear top-down data flow.
  - Resilience: UI crashes do not corrupt background tasks or files.
* **Verification**:
  - Automated CI gate: `python scripts/check_imports.py` and `python scripts/check_loc.py`.
