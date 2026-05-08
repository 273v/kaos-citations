"""Post-processing passes that run over a list of already-extracted citations.

Three cross-cutting Bluebook contracts are applied here rather than in
each per-family parser:

1. **Signal binding** (Bluebook R1.2) — scan the source text for
   ``See``, ``See, e.g.,``, ``See also``, ``Cf.``, ``But see``,
   ``But cf.``, ``Contra``, ``Accord``, ``Compare``, ``See generally``,
   ``E.g.`` immediately preceding a citation token, and set
   ``citation.signal`` accordingly. The signal also propagates to the
   rest of a string-cite group.

2. **String-cite grouping** (R1.4) — citations separated by ``;``
   within the same sentence belong to one string-cite group.

3. **Subsequent-history binding** (R10.7) — when two ``CaseCitation``
   tokens are joined by ``aff'd``, ``rev'd``, ``cert. denied``,
   ``vacated``, ``overruled by``, etc., emit the relationship onto the
   parent's ``subsequent_history`` tuple.

All passes return a NEW list (frozen-model semantics) — they don't
mutate the input.

Implementation: NO ``import re``. Sentence boundaries come from the
Punkt singleton (with the bundled legal model) via
``kaos_citations._nlp.get_sentence_tokenizer``. Signal and history
detection use Rust-backed RegexMatchers from ``kaos_citations.matchers``.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache

from kaos_citations._nlp import get_sentence_tokenizer
from kaos_citations.matchers import (
    bluebook_signal_matcher,
    subsequent_history_matcher,
)
from kaos_citations.model import (
    CaseCitation,
    Citation,
    SignalKind,
    SubsequentHistoryRelation,
)

# ---------------------------------------------------------------------------
# Bluebook signal classification
# ---------------------------------------------------------------------------


def _classify_signal(matched_text: str) -> SignalKind | None:
    """Map the raw matched signal substring to the typed SignalKind
    literal. Order matters — check longer / more-specific signals
    first so ``See, e.g.,`` wins over ``See``."""
    s = matched_text.lower()
    # Strip whitespace/punctuation for stable comparison
    compact = s.replace(" ", "").replace(",", "").replace(".", "")
    if compact.startswith("seeeg") or compact == "seeeg":
        return "see_eg"
    if compact == "seealso":
        return "see_also"
    if compact == "seegenerally":
        return "see_generally"
    if compact.startswith("butseeeg"):
        return "but_see"
    if compact == "butsee":
        return "but_see"
    if compact == "butcf":
        return "but_cf"
    if compact == "compare":
        return "compare_with"
    if compact == "accord":
        return "accord"
    if compact == "contra":
        return "contra"
    if compact == "cf":
        return "cf"
    if compact == "eg":
        return "eg"
    if compact == "see":
        return "see"
    return None


# ---------------------------------------------------------------------------
# Sentence boundary lookup — Punkt-backed
# ---------------------------------------------------------------------------


@lru_cache(maxsize=64)
def _sentence_starts_for(text: str) -> tuple[int, ...]:
    """Return a sorted tuple of sentence-start character offsets for
    ``text``, computed by the Punkt tokenizer with the bundled legal
    model. Cached per text-id since postprocess runs the same passes
    over the same document multiple times.

    Punkt's ``tokenize_spans`` returns ``(start, end)`` per sentence;
    we want only the starts plus position 0 to make a sorted "where
    can a sentence begin?" index. Tuple-typed for hashing.
    """
    tokenizer = get_sentence_tokenizer()
    spans = tokenizer.tokenize_spans(text)
    starts: list[int] = [0]
    starts.extend(s[0] for s in spans)
    # Dedup + sort
    return tuple(sorted(set(starts)))


def _sentence_start_for_position(text: str, pos: int) -> int:
    """Return the offset of the start of the sentence containing
    ``pos`` — i.e. the largest sentence start ≤ pos."""
    starts = _sentence_starts_for(text)
    # Binary search would be faster but the corpus per call is small;
    # linear from the right is fine and simpler.
    candidate = 0
    for s in starts:
        if s <= pos:
            candidate = s
        else:
            break
    return candidate


def attach_signals(text: str, citations: Iterable[Citation]) -> list[Citation]:
    """Bind each citation's preceding Bluebook signal (R1.2).

    Algorithm:

    1. For each citation, find the start of its containing sentence
       (Punkt boundaries).
    2. Slice ``text[sentence_start : citation.span[0]]``.
    3. Strip leading whitespace + quotes/parens.
    4. If the stripped prefix opens with a Bluebook signal, classify
       it via ``_classify_signal`` and set ``citation.signal``.
    """
    out: list[Citation] = []
    matcher = bluebook_signal_matcher()
    for c in citations:
        if c.signal is not None:
            out.append(c)
            continue
        sent_start = _sentence_start_for_position(text, c.span[0])
        leading = text[sent_start : c.span[0]].lstrip(" \t\n\r\"'(")
        if not leading:
            out.append(c)
            continue
        # Match the signal at the start of the leading slice.
        hit = matcher.find_first(leading)
        if hit is None or hit.start != 0:
            out.append(c)
            continue
        signal = _classify_signal(hit.text)
        if signal is None:
            out.append(c)
            continue
        out.append(c.model_copy(update={"signal": signal}))
    return out


# ---------------------------------------------------------------------------
# String-cite groups (R1.4)
# ---------------------------------------------------------------------------


def _has_real_sentence_break(text: str, start: int, end: int) -> bool:
    """Return True if a Punkt sentence boundary lies strictly inside
    ``(start, end)``. Punkt is the source of truth — no hand-rolled
    abbreviation logic.
    """
    if end <= start:
        return False
    starts = _sentence_starts_for(text)
    # A sentence boundary inside (start, end) means some sentence
    # starts at a position s such that start < s < end.
    for s in starts:
        if s <= start:
            continue
        return not s >= end
    return False


def attach_string_cite_groups(text: str, citations: Iterable[Citation]) -> list[Citation]:
    """Group adjacent citations separated by ``;`` into string-cite
    groups (R1.4) and propagate the leading signal across the group.

    A run of citations forms one group when:

    - Their inter-citation gaps are short (<200 chars).
    - At least one ``;`` appears in each gap.
    - No Punkt sentence boundary lies inside the gap.
    """
    cite_list = list(citations)
    if not cite_list:
        return cite_list

    sorted_cites = sorted(cite_list, key=lambda c: c.span[0])
    sort_to_orig = {i: cite_list.index(c) for i, c in enumerate(sorted_cites)}

    groups: list[list[int]] = []
    current: list[int] = [0]

    for i in range(1, len(sorted_cites)):
        prev = sorted_cites[i - 1]
        curr = sorted_cites[i]
        gap_start = prev.span[1]
        gap_end = curr.span[0]
        gap = text[gap_start:gap_end]

        # Punkt is the source of truth for sentence boundaries — it
        # correctly treats ``v.`` and ``U.S.`` as abbreviations rather
        # than terminators. We rely on it exclusively here.
        in_group = (
            len(gap) < 200 and ";" in gap and not _has_real_sentence_break(text, gap_start, gap_end)
        )

        if in_group:
            current.append(i)
        else:
            if len(current) > 1:
                groups.append(current)
            current = [i]
    if len(current) > 1:
        groups.append(current)

    annotated = list(cite_list)
    for group_id, indices in enumerate(groups):
        leader_signal = sorted_cites[indices[0]].signal
        for idx in indices:
            orig_pos = sort_to_orig[idx]
            updates: dict[str, object] = {"string_cite_group": group_id}
            if leader_signal is not None and annotated[orig_pos].signal is None:
                updates["signal"] = leader_signal
            annotated[orig_pos] = annotated[orig_pos].model_copy(update=updates)

    return annotated


# ---------------------------------------------------------------------------
# Subsequent history (R10.7)
# ---------------------------------------------------------------------------


def _classify_history_relation(connector: str) -> SubsequentHistoryRelation | None:
    """Map the raw connector string to the typed
    :class:`SubsequentHistoryRelation` literal."""
    s = connector.lower().replace(" ", "").replace("'", "").replace(".", "")
    if "affd" in s and "inpart" in s:
        return "affirmed"
    if s.startswith("affd"):
        return "affirmed"
    if "revd" in s and "inpart" in s:
        return "reversed"
    if s.startswith("revd"):
        return "reversed"
    if s.startswith("vacated"):
        return "vacated"
    if s.startswith("remanded"):
        return "remanded"
    if "certdenied" in s:
        return "cert_denied"
    if "certgranted" in s:
        return "cert_granted"
    if "overruled" in s and "inpart" in s:
        return "overruled_in_part"
    if s.startswith("overruled"):
        return "overruled"
    if s.startswith("abrogated"):
        return "abrogated"
    if s.startswith("modified"):
        return "modified"
    if s.startswith("affg"):
        return "affirming"
    if s.startswith("revg"):
        return "reversing"
    return None


def assign_cite_ids(citations: list[Citation]) -> list[Citation]:
    """Stamp each citation with a stable per-extraction ``cite_id``.

    IDs are sequential ``c0001``, ``c0002``, ... in source order
    (``span[0]`` ascending). They are stored on the citation model
    itself, so filtering or re-sorting the result list never breaks
    cross-references that use them — ``back_ref`` and the second tuple
    element of ``subsequent_history`` both reference these IDs.

    Idempotent: re-running on a list whose citations already carry
    cite_ids returns the same IDs (preserved as long as they are
    non-empty).
    """
    if not citations:
        return citations

    sort_order = sorted(range(len(citations)), key=lambda i: citations[i].span[0])
    out: list[Citation] = list(citations)
    rank = 0
    for orig_idx in sort_order:
        rank += 1
        c = out[orig_idx]
        if c.cite_id:
            continue
        out[orig_idx] = c.model_copy(update={"cite_id": f"c{rank:04d}"})
    return out


def attach_subsequent_history(text: str, citations: list[Citation]) -> list[Citation]:
    """Detect Bluebook R10.7 subsequent-history relationships between
    consecutive :class:`CaseCitation` tokens and emit them on
    ``parent.subsequent_history`` as ``(relation, child_cite_id)`` pairs.

    Assumes :func:`assign_cite_ids` has already run — the parent's
    history tuple stores the child's ``cite_id``, not its list index,
    so filtering or re-sorting the result list never breaks the
    cross-reference.
    """
    if not citations:
        return citations

    indexed = list(enumerate(citations))
    indexed.sort(key=lambda pair: pair[1].span[0])
    matcher = subsequent_history_matcher()

    additions: dict[int, list[tuple[SubsequentHistoryRelation, str]]] = {}
    for i in range(len(indexed) - 1):
        parent_orig_idx, parent = indexed[i]
        _, child = indexed[i + 1]
        if not isinstance(parent, CaseCitation) or not isinstance(child, CaseCitation):
            continue
        gap = text[parent.span[1] : child.span[0]]
        if len(gap) > 80 or not gap.strip():
            continue
        hits = matcher.find_all(gap)
        if not hits:
            continue
        # Take the first connector — there's typically only one.
        connector = hits[0].text
        relation = _classify_history_relation(connector)
        if relation is None:
            continue
        if not child.cite_id:
            # cite_id assignment must have run before this pass; if the
            # child somehow lacks one, skip rather than emit a broken
            # back-reference.
            continue
        additions.setdefault(parent_orig_idx, []).append((relation, child.cite_id))

    if not additions:
        return citations

    out: list[Citation] = []
    for orig_idx, c in enumerate(citations):
        if orig_idx in additions and isinstance(c, CaseCitation):
            existing = list(c.subsequent_history)
            for rel, child_id in additions[orig_idx]:
                if (rel, child_id) not in existing:
                    existing.append((rel, child_id))
            out.append(c.model_copy(update={"subsequent_history": tuple(existing)}))
        else:
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Combined pass
# ---------------------------------------------------------------------------


def apply_postprocess(text: str, citations: list[Citation]) -> list[Citation]:
    """Run all post-processing passes in dependency order.

    Order: cite-id assignment → signals → string-cite groups (which
    also propagate signals) → subsequent history (uses cite_ids). Each
    pass returns a new list.
    """
    citations = assign_cite_ids(citations)
    citations = attach_signals(text, citations)
    citations = attach_string_cite_groups(text, citations)
    citations = attach_subsequent_history(text, citations)
    return citations


__all__ = [
    "apply_postprocess",
    "assign_cite_ids",
    "attach_signals",
    "attach_string_cite_groups",
    "attach_subsequent_history",
]
