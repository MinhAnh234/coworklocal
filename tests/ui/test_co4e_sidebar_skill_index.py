"""Co4E left column: the skill library must be read ONCE per sidebar reload.

Why this test exists
--------------------
``Co4ESidebarMixin._reload_sidebar`` used to call
``core.skills.skill_prefix_for(name)`` once per skill. Every one of those calls
re-reads the *whole* skill folder from disk (``list_skills()`` +
``builtin_skills()``), so the reload was O(N**2) in the number of skills.

That reload runs on every language switch (``Co4ETab._retranslate`` ->
``_reload_sidebar``). Measured end-to-end on a real library of 121 skills, the
per-name calls cost ~3.8 s of blocked GUI thread — the "app freezes for a few
seconds when I switch Vietnamese -> English" the user reported.

Two different things are guarded here, and they fail for different reasons:

* ``test_reload_sidebar_reads_the_skill_library_once`` — the performance
  contract. Red before the fix (the library was read 1 + N times), green after.
* the two equivalence tests — the *correctness* contract. A lookup table is
  easy to build subtly wrong, and a wrong one silently changes which skill text
  is pushed into an agent prompt. They pin the answer to ``skill_prefix_for``
  itself in exactly the cases where a naive ``{name: skill}`` dict diverges:
  a name shared by a user skill and a built-in (first match wins, user first),
  a skill whose instructions are blank (it does NOT end ``skill_prefix_for``'s
  scan, so a later namesake with real instructions must still win), and
  lookups by slug / different case / padding / unknown name / empty name.
  Those two are characterization tests: green before AND after by design.
"""
from __future__ import annotations

from dataclasses import replace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget

from cowork_local.core import co4e, skills as skills_mod
from cowork_local.presentation.co4e.co4e_sidebar import Co4ESidebarMixin


class _SidebarHarness(Co4ESidebarMixin):
    """Just enough state to run the real ``_reload_sidebar``.

    Building a whole ``Co4ETab`` would drag in config/HOME-dependent module
    constants (see ``tests/test_build_co4e_tab.py``); the mixin only touches
    the three list widgets, so the real production method runs unchanged here.
    """

    def __init__(self) -> None:
        """Create the three palette lists ``_reload_sidebar`` fills in."""
        self.wf_list = QListWidget()
        self.agent_list = QListWidget()
        self.skill_list = QListWidget()


@pytest.fixture
def harness(qapp, monkeypatch):
    """A sidebar harness with the workflow/agent sources stubbed out empty."""
    monkeypatch.setattr(co4e, "list_workflows", lambda: [])
    monkeypatch.setattr(co4e, "list_custom_agents", lambda: [])
    return _SidebarHarness()


def _install_skills(monkeypatch, user, builtin):
    """Replace the two disk-reading skill sources and count how often they run.

    Fresh copies are handed out on every call so a caller mutating a returned
    ``Skill`` cannot make a later call look different.
    """
    calls = {"list_skills": 0, "builtin_skills": 0}

    def _list_skills(directory=None):
        """Stand-in for ``skills.list_skills`` that records each read."""
        calls["list_skills"] += 1
        return [replace(s) for s in user]

    def _builtin_skills():
        """Stand-in for ``skills.builtin_skills`` that records each read."""
        calls["builtin_skills"] += 1
        return [replace(s) for s in builtin]

    monkeypatch.setattr(skills_mod, "list_skills", _list_skills)
    monkeypatch.setattr(skills_mod, "builtin_skills", _builtin_skills)
    return calls


def _skill_rows(sidebar):
    """Return ``(item text, payload instructions)`` for every skill palette row."""
    return [(sidebar.skill_list.item(i).text(),
             sidebar.skill_list.item(i).data(Qt.UserRole)["instructions"])
            for i in range(sidebar.skill_list.count())]


def test_reload_sidebar_reads_the_skill_library_once(harness, monkeypatch):
    """One sidebar reload must hit the skill library exactly once, not once per skill."""
    user = [skills_mod.Skill(name=f"Skill {i}", instructions=f"Body {i}")
            for i in range(8)]
    calls = _install_skills(monkeypatch, user, [])

    harness._reload_sidebar()

    assert harness.skill_list.count() == 8, "every skill must still reach the palette"
    assert calls["list_skills"] == 1, (
        f"the skill library was read {calls['list_skills']}x for 8 skills — "
        "reading it once per skill is the O(N^2) freeze on language switch"
    )
    assert calls["builtin_skills"] == 1, (
        f"built-in skills were read {calls['builtin_skills']}x for 8 skills"
    )


def test_skill_payloads_match_skill_prefix_for(harness, monkeypatch):
    """The palette payload must be byte-identical to ``skill_prefix_for``'s answer.

    The fixture is deliberately hostile: a name shared by a user skill and a
    built-in, a blank-instructions skill followed by a namesake with real
    content, and names with padding/odd casing.
    """
    user = [
        skills_mod.Skill(name="Shared Name", instructions="USER VERSION"),
        skills_mod.Skill(name="Blank First", instructions="   "),
        skills_mod.Skill(name="Blank First", instructions="LATER, WITH CONTENT"),
        skills_mod.Skill(name="  Padded Name  ", instructions="PADDED BODY"),
        skills_mod.Skill(name="MiXeD CaSe", instructions="MIXED BODY"),
    ]
    builtin = [
        skills_mod.Skill(name="Shared Name", instructions="BUILTIN VERSION"),
        skills_mod.Skill(name="Builtin Only", instructions="BUILTIN BODY"),
    ]
    _install_skills(monkeypatch, user, builtin)

    harness._reload_sidebar()

    expected = [(s.name, skills_mod.skill_prefix_for(s.name)) for s in user + builtin]
    assert _skill_rows(harness) == expected

    rows = dict(_skill_rows(harness))
    # A user skill wins over a built-in of the same name: list_skills() comes
    # first and skill_prefix_for() returns the FIRST match, not the last.
    assert rows["Shared Name"] == "## Skill: Shared Name\nUSER VERSION"
    # A blank-instructions skill does not end the scan, so its later namesake
    # supplies the text. A last-write-wins dict would answer '' here.
    assert rows["Blank First"] == "## Skill: Blank First\nLATER, WITH CONTENT"
    assert rows["Builtin Only"] == "## Skill: Builtin Only\nBUILTIN BODY"


def test_lookup_matches_skill_prefix_for_on_odd_names(monkeypatch):
    """Slug / case / padding / unknown / empty lookups must answer like ``skill_prefix_for``."""
    # Imported inside the test on purpose: this symbol is what the fix
    # introduces, and a module-level import would turn the pre-fix run into a
    # collection error instead of a real assertion failure in the test above.
    from cowork_local.presentation.co4e.co4e_sidebar import _skill_prefix_lookup

    user = [
        skills_mod.Skill(name="Shared Name", instructions="USER VERSION"),
        skills_mod.Skill(name="Blank First", instructions=""),
        skills_mod.Skill(name="Blank First", instructions="LATER, WITH CONTENT"),
        skills_mod.Skill(name="Tiếng Việt / 日本語", instructions="UNICODE BODY"),
        skills_mod.Skill(name="", instructions="NAMELESS BODY"),
    ]
    builtin = [skills_mod.Skill(name="Shared Name", instructions="BUILTIN VERSION")]
    _install_skills(monkeypatch, user, builtin)

    lookup = _skill_prefix_lookup(skills_mod.list_skills() + skills_mod.builtin_skills())

    probes = [
        "Shared Name", "shared name", "SHARED NAME", "  Shared Name  ",
        "shared-name",                      # by slug
        "Blank First", "blank-first",
        "Tiếng Việt / 日本語", "tiếng-việt-日本語",
        "", "   ", "no-such-skill-anywhere", "skill",
    ]
    for probe in probes:
        assert lookup(probe) == skills_mod.skill_prefix_for(probe), probe
