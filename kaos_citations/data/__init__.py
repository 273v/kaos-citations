"""Vendored third-party JSON data — see ``LICENSE.vendored``.

Layout:

- ``reporters.json``, ``case_name_abbreviations.json``,
  ``state_abbreviations.json``, ``laws.json``, ``journals.json``,
  ``regexes.json`` — vendored from ``reporters_db`` (BSD-2)
- ``courts.json``, ``courts_states.json``, ``courts_variables.json``
  — vendored from ``courts_db`` (BSD-2)

kaos-citations consumes only the data, never the upstream Python
code. See ``kaos_citations.data._loaders`` for typed accessors.
"""
