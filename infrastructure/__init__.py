"""Infrastructure layer - adapters to the outside world.

Concrete implementations of what the inner layers only describe: HTTP calls to
model gateways, the OS keyring, the filesystem, subprocesses, telemetry sinks.
May import ``domain/`` (to speak its types) and third-party libraries, but never
``presentation/``/``ui/``.
"""
