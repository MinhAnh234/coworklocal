"""Provider adapters and the central provider catalogue (EPIC R03)."""

from .provider_registry import (
    BUILTIN_DESCRIPTORS,
    ProviderRegistry,
    default_registry,
)

__all__ = [
    "BUILTIN_DESCRIPTORS",
    "ProviderRegistry",
    "default_registry",
]
