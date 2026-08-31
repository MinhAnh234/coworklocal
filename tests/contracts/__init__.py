"""Contract tests: one shared specification every interchangeable adapter must satisfy.

Unlike unit tests (which pin ONE implementation's behaviour), a contract test is
parametrised over every implementation of an interface, so adding a new provider
means adding a row — not writing a new test file — and a provider that quietly
breaks the canonical shape fails here rather than in production.
"""
