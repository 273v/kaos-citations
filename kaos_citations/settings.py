"""Module settings for kaos-citations.

kaos-citations is a focused structured-extraction library — there are
no per-module tunables beyond what's intrinsic to the bundled vendored
data. ``KaosCitationsSettings`` is intentionally empty at this layer;
kept as a typed shell so callers can pass configuration via
``KaosContext._config`` if they need to add behavior in the future
without breaking the public API.
"""

from __future__ import annotations

from kaos_core.config.module_settings import ModuleSettings
from pydantic_settings import SettingsConfigDict


class KaosCitationsSettings(ModuleSettings):
    """Typed settings for kaos-citations.

    Empty at 0.1.0a1 — no runtime tunables. The class exists so
    downstream code can pass a typed settings object via
    ``KaosCitationsSettings.from_context(context)`` even when no
    fields are set, and so future configuration can be added without
    a public-API change.
    """

    model_config = SettingsConfigDict(
        env_prefix="KAOS_CITATIONS_",
        env_file=".env",
        extra="ignore",
    )


__all__ = ["KaosCitationsSettings"]
