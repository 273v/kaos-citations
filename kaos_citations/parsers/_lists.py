"""Section lists after a code citation: ``7 U.S.C. 61, 87e, 228``.

The CFR's Authority lines and the U.S. Code's notes write one title and
many sections. Each item after the first is a citation of its own, in the
same title and code, with its own span. An item that is the title of the
next citation (``42 U.S.C. 1983, 28 U.S.C. 1331``) ends the list: its
number is read by the next match, not here.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from kaos_citations.matchers import regex

# Longest a list is read, in characters after the citation, so a stray comma
# far down a paragraph never joins it.
_WINDOW = 400


@lru_cache(maxsize=4)
def _item_matcher(section_pattern: str):  # type: ignore[no-untyped-def]
    return regex(r"\s*,\s*(?:and\s+|or\s+)?(?P<item>" + section_pattern + r")")


def list_items(
    text: str,
    end: int,
    section_pattern: str,
    starts_next: Callable[[str], bool],
) -> list[tuple[int, int, str]]:
    """``(start, end, item)`` for each list item after position ``end``.

    ``starts_next(rest)`` says whether the text after an item begins a
    new citation's code (``U.S.C.``, ``CFR``): the item is then that
    citation's title, and the list stops before it.
    """
    window = text[end : end + _WINDOW]
    out: list[tuple[int, int, str]] = []
    expected = 0
    for m in _item_matcher(section_pattern).find_all(window):
        if m.start != expected:
            break
        item = m.groups[1] if len(m.groups) > 1 else ""
        if not item:
            break
        if starts_next(window[m.end :].lstrip()):
            break
        out.append((end + m.end - len(item), end + m.end, item))
        expected = m.end
    return out
