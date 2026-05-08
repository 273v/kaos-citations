"""Verifies the kaos-nlp-core boundary in `_nlp.py`.

The Punkt legal model must load on import — no silent fallback to
the empty-default tokenizer (which would produce wrong sentence
boundaries on legal text and break signal binding).
"""

from __future__ import annotations

from kaos_citations._nlp import (
    PunktModelMissingError,
    get_sentence_tokenizer,
    verify_punkt_model,
)


def test_punkt_legal_model_loads_with_legal_abbreviations() -> None:
    """The bundled legal Punkt model has ~27K abbreviations. We assert
    the loaded model has at least 5K to catch the case where
    kaos-nlp-core silently falls back to an empty default."""
    diag = verify_punkt_model()
    assert diag["abbreviations"] >= 5_000, (
        f"loaded only {diag['abbreviations']} abbreviations — expected the "
        "legal model with ~27K. The empty-default fallback would silently "
        "produce wrong sentence boundaries on legal text."
    )


def test_get_sentence_tokenizer_returns_singleton() -> None:
    a = get_sentence_tokenizer()
    b = get_sentence_tokenizer()
    assert a is b, "get_sentence_tokenizer should be a cached singleton"


def test_punkt_handles_legal_abbreviations() -> None:
    """Smoke test: the legal model should NOT split sentences at
    common legal abbreviations like ``v.``, ``U.S.``, ``Cir.``."""
    tok = get_sentence_tokenizer()
    text = "Brown v. Board of Education, 347 U.S. 483 (1954) is the seminal case."
    sentences = tok.tokenize(text)
    assert len(sentences) == 1, (
        f"legal Punkt model split a single sentence at abbreviations: {sentences}"
    )


def test_punkt_splits_real_sentence_boundaries() -> None:
    """Conversely, real sentence boundaries between two distinct
    sentences should fire."""
    tok = get_sentence_tokenizer()
    text = "The motion is granted. The opposing party shall respond."
    sentences = tok.tokenize(text)
    assert len(sentences) == 2


def test_punkt_model_missing_error_class_attached() -> None:
    """Verify the typed exception is exported."""
    assert issubclass(PunktModelMissingError, RuntimeError)
