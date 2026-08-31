"""Characterization tests: pin the CURRENT behaviour of legacy code (R01-T04).

These are not specifications of what the code *should* do - they are a snapshot
of what it *does* today, written before the refactor so that any behavioural
drift introduced while moving logic into ``application/`` shows up as a failing
test rather than as a bug report from a user.

Rule for this folder: when a test here fails during the refactor, do not "fix"
the test first. Decide deliberately whether the behaviour change is intended,
and only then update the snapshot in the same commit as the change.
"""
