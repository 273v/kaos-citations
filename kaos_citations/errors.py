"""Error hierarchy for kaos-citations.

Follows the KAOS exception pattern: every package defines a base error
inheriting from :class:`kaos_core.errors.KaosCoreError` so cross-package
try/except blocks work uniformly.
"""

from __future__ import annotations

from kaos_core.exceptions import KaosCoreError


class KaosCitationsError(KaosCoreError):
    """Base class for all kaos-citations errors."""


class CitationParseError(KaosCitationsError):
    """Raised when a citation parser cannot interpret matched text."""


__all__ = [
    "CitationParseError",
    "KaosCitationsError",
]
