"""Integration tests: several real layers wired together, still fully offline.

Where unit tests pin one class against fakes and contract tests pin an interface
across implementations, these exercise a real path end to end — e.g. the
application routing service on top of the real ``core/routing`` engine — so a
seam that only works against a mock is caught here.
"""
