"""AST-based Static Analysis Guard for Clean Architecture Enforcement.

Scans designated Python packages (such as `domain/` and `application/`) to ensure
they remain 100% Pure Python and do not import presentation/GUI frameworks (PySide6, PyQt)
or concrete application shells.
"""
from __future__ import annotations

import argparse
import ast
import io
import sys
from pathlib import Path
from typing import List, NamedTuple, Set

# Ensure UTF-8 output on standard console streams across diverse Windows locales (CP932, etc.)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass


class ImportViolation(NamedTuple):
    file_path: Path
    line_number: int
    imported_module: str
    rule_description: str


# Disallowed top-level package names in pure business/domain layers
FORBIDDEN_MODULE_PREFIXES: Set[str] = {
    "PySide6",
    "PySide2",
    "PyQt6",
    "PyQt5",
    "ui",
    "app",
}

# Default directories that must strictly adhere to Clean Architecture
DEFAULT_SCAN_DIRS: List[str] = [
    "domain",
    "application",
]


class ArchitectureImportVisitor(ast.NodeVisitor):
    """AST visitor that checks all Import and ImportFrom statements against forbidden prefixes."""

    def __init__(self, file_path: Path, forbidden: Set[str]) -> None:
        self.file_path = file_path
        self.forbidden = forbidden
        self.violations: List[ImportViolation] = []

    def visit_Import(self, node: ast.Import) -> None:
        # Check direct `import x, y` statements
        for alias in node.names:
            root_module = alias.name.split(".")[0]
            if root_module in self.forbidden:
                self.violations.append(
                    ImportViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        imported_module=alias.name,
                        rule_description=f"Direct import of GUI/shell module '{alias.name}' is prohibited.",
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # Check `from x import y` statements
        if node.module:
            root_module = node.module.split(".")[0]
            if root_module in self.forbidden:
                self.violations.append(
                    ImportViolation(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        imported_module=node.module,
                        rule_description=f"Import from GUI/shell module '{node.module}' is prohibited.",
                    )
                )
        self.generic_visit(node)


def scan_file(file_path: Path, forbidden: Set[str]) -> List[ImportViolation]:
    """Parse a single Python file into AST and return all detected architecture import violations."""
    try:
        source_code = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source_code, filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        print(f"[Syntax/Read Warning] Could not parse {file_path}: {exc}", file=sys.stderr)
        return []

    visitor = ArchitectureImportVisitor(file_path, forbidden)
    visitor.visit(tree)
    return visitor.violations


def scan_directory(dir_path: Path, forbidden: Set[str]) -> List[ImportViolation]:
    """Recursively scan all Python files in a directory."""
    violations: List[ImportViolation] = []
    if not dir_path.exists():
        return violations

    for py_file in dir_path.rglob("*.py"):
        if py_file.is_file() and "__pycache__" not in py_file.parts:
            violations.extend(scan_file(py_file, forbidden))

    return violations


def main() -> int:
    """CLI entry point for CI/pre-commit quality gate checks."""
    parser = argparse.ArgumentParser(
        description="Clean Architecture Import Guard: Verifies zero GUI/Qt dependencies in domain/app layers."
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        default=DEFAULT_SCAN_DIRS,
        help="Paths or directories to scan (defaults to 'domain' and 'application')",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root workspace directory",
    )
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    all_violations: List[ImportViolation] = []

    print(f"[Clean Arch Guard] Scanning root: {root_dir}")

    for target in args.paths:
        target_path = (root_dir / target).resolve()
        if not target_path.exists():
            # If the layer directory does not exist yet (during early migration), skip cleanly
            print(f"[Clean Arch Guard] Directory '{target}' does not exist yet (skipped).")
            continue

        if target_path.is_file():
            all_violations.extend(scan_file(target_path, FORBIDDEN_MODULE_PREFIXES))
        else:
            all_violations.extend(scan_directory(target_path, FORBIDDEN_MODULE_PREFIXES))

    if all_violations:
        print("\n[FAIL] CLEAN ARCHITECTURE VIOLATIONS DETECTED:")
        print("=" * 70)
        for v in all_violations:
            rel_path = v.file_path.relative_to(root_dir) if v.file_path.is_relative_to(root_dir) else v.file_path
            print(f"  • {rel_path}:{v.line_number} -> Forbidden import: '{v.imported_module}'")
            print(f"    Reason: {v.rule_description}")
        print("=" * 70)
        print(f"Total Violations: {len(all_violations)}")
        return 1

    print("\n[PASS] CLEAN ARCHITECTURE CHECK: 0 forbidden imports detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
