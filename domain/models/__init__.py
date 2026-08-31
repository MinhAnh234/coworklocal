"""Domain models package: provider descriptors, model pricing, and routing metadata."""

from .provider_descriptor import (
    AuthKind,
    ProviderDescriptor,
    WireProtocol,
)

__all__ = [
    "AuthKind",
    "ProviderDescriptor",
    "WireProtocol",
]
