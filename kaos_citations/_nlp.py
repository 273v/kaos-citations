"""kaos-nlp-core integration boundary.

All kaos-citations matching, tokenization, and segmentation goes
through this module. There is exactly ONE source of truth for the
Punkt sentence tokenizer, the prefix matcher, and the per-family
RegexMatchers — they are constructed lazily here, cached, and reused.

The user's stated requirement: "we have an extremely excellent
sentence model that you need to ensure you load properly". The
guarantee:

- ``get_sentence_tokenizer()`` always returns a ``PunktTokenizer``
  initialised with the **embedded legal Punkt parameters**
  (~27,000 abbreviations, trained on legal-domain text).
- We never instantiate ``PunktTokenizer()`` with no args from kaos-
  citations code — that produces an empty model.
- If the embedded model fails to load (bad wheel, dev build), the
  loader **raises** rather than silently falling back to an empty
  tokenizer that would produce broken sentence boundaries.
"""

from __future__ import annotations

from functools import lru_cache

from kaos_nlp_core.segmentation import (
    PunktTokenizer,
    get_default_punkt_tokenizer,
    load_default_punkt_parameters,
)

# Minimum number of abbreviations the legal model is expected to ship
# with. The embedded model has ~27,064. Anything dramatically smaller
# means we accidentally got the empty-default fallback and our
# sentence-boundary logic will misfire on legal abbreviations.
_MIN_LEGAL_ABBREVIATIONS = 5_000


class PunktModelMissingError(RuntimeError):
    """Raised when the bundled Punkt legal model fails to load.

    kaos-citations relies on the abbreviation-rich legal Punkt model
    to detect sentence boundaries around tokens like ``v.``, ``U.S.``,
    ``Cir.``, ``F.3d``, ``402A.`` etc. Without it the postprocess
    layer cannot bind Bluebook signals correctly.

    Resolution paths:

    1. Reinstall ``kaos-nlp-core`` from a published wheel
       (``uv add kaos-nlp-core>=0.1.0a1``). Wheels embed the model
       bytes directly in the compiled extension.
    2. For editable / dev installs, ensure
       ``kaos-nlp-core/python/kaos_nlp_core/models/default.npkt.gz``
       is present.
    3. Run ``kaos-citations doctor`` to verify the model is loaded.
    """


@lru_cache(maxsize=1)
def get_sentence_tokenizer() -> PunktTokenizer:
    """Return the singleton legal-domain Punkt tokenizer.

    Raises:
        PunktModelMissingError: If the embedded legal model is missing
            or the abbreviation set is suspiciously small (which would
            indicate kaos-nlp-core silently fell back to the empty
            default and our citation parser would produce wrong
            sentence boundaries).
    """
    params = load_default_punkt_parameters()
    if params is None:
        msg = (
            "kaos-nlp-core's bundled Punkt legal model failed to load. "
            "kaos-citations requires the legal-domain Punkt parameters "
            "(~27K abbreviations) for correct sentence segmentation around "
            "Bluebook abbreviations like ``v.``, ``U.S.``, ``Cir.``. "
            "Fix: reinstall kaos-nlp-core from a published wheel, or "
            "verify the dev model file at "
            "``kaos-nlp-core/python/kaos_nlp_core/models/default.npkt.gz``."
        )
        raise PunktModelMissingError(msg)

    abbrev_count = params.num_abbreviations
    if abbrev_count < _MIN_LEGAL_ABBREVIATIONS:
        msg = (
            f"kaos-nlp-core Punkt parameters loaded with only "
            f"{abbrev_count} abbreviations — expected "
            f">={_MIN_LEGAL_ABBREVIATIONS} from the bundled legal model. "
            "This is the empty-default fallback, not the legal model. "
            "Fix: reinstall kaos-nlp-core; verify "
            "``kaos_nlp_core.segmentation.load_default_punkt_parameters()`` "
            "returns the embedded params."
        )
        raise PunktModelMissingError(msg)

    return get_default_punkt_tokenizer()


def verify_punkt_model() -> dict[str, int]:
    """Run the Punkt-load verification eagerly and return diagnostics.

    Used by the ``kaos-citations doctor`` command and by the
    benchmark harness to confirm the legal model is on the path
    before any extraction runs.

    Returns a dict with the abbreviation / collocation / starter
    counts of the loaded model.
    """
    params = load_default_punkt_parameters()
    if params is None:
        raise PunktModelMissingError(
            "Punkt parameters did not load — the embedded model bytes are "
            "unavailable and no filesystem copy was found. See "
            "PunktModelMissingError docstring for resolution steps."
        )
    return {
        "abbreviations": params.num_abbreviations,
        "collocations": params.num_collocations,
        "starters": params.num_sent_starters,
    }


__all__ = [
    "PunktModelMissingError",
    "get_sentence_tokenizer",
    "verify_punkt_model",
]
