# Start Contributing

Welcome to the **Cowork Local** contributor guide!

---

## 🏛️ Architecture & Ground Rules

1. **4-Tier Clean Architecture**:
   - `domain/`: Business entities and immutable data structures (Pure Python).
   - `application/`: Application services and orchestration (Pure Python).
   - `infrastructure/`: External integrations, adapters, persistence, and secrets.
   - `presentation/`: Desktop UI widgets, PySide6 components, and Qt signals.
   - **Rule**: `domain/` and `application/` must NEVER import `PySide6` or any UI framework.

2. **File Size Limit (LOC)**:
   - Every file in `domain/`, `application/`, `infrastructure/`, and `presentation/` must be `<= 400 LOC`.

3. **In-Code Comments**:
   - All code logic, error handling, and design rationales must be documented with clear **English comments**.

---

## 🚀 Development Workflow

### 1. Create a Topic Branch
```bash
git switch -c feat/my-new-feature
```

### 2. Implement Using Contributor Recipes
Follow the standardized recipes in [`docs/governance/contributor-recipes.md`](docs/governance/contributor-recipes.md):
- **Recipe 1**: Adding a new AI Model Provider.
- **Recipe 2**: Adding a new Tool or MCP Server.
- **Recipe 3**: Adding a new UI Screen or Widget.

### 3. Run CASAN Quality Gate Locally
Before committing and pushing your branch, ensure all quality gates pass:

```bash
python scripts/run_quality_gate.py
```

---

## 🧪 Testing Pyramid

We maintain a strict multi-tier test pyramid:
- `tests/unit/`: Fast unit tests (no I/O, < 0.05s).
- `tests/contracts/`: Contract tests for Provider and Tool interfaces.
- `tests/integration/`: Component integration tests (Qt offscreen).
- `tests/e2e/`: End-to-End release smoke tests (`pytest tests/e2e/test_smoke.py`).
- `tests/fakes/`: Reusable in-memory test doubles (`FakeProvider`, `FakeToolRuntime`).

---

## 📋 Definition of Done (DoD)

A Pull Request is ready for merge only when:
- [x] All production files are `<= 400 LOC` (`python scripts/check_loc.py`).
- [x] Clean Architecture boundary check has 0 violations (`python scripts/check_imports.py`).
- [x] Secrets audit finds 0 plaintext credentials (`python scripts/audit_security.py`).
- [x] 100% of test suite passes without regressions (`pytest tests/`).
- [x] E2E release smoke tests pass (`pytest tests/e2e/test_smoke.py`).
