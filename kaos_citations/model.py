"""Discriminated-union ``Citation`` model.

Pydantic v2 discriminated union over concrete citation subclasses keyed
by a ``kind`` string literal. Adding a new family is a deliberate,
reviewable change: define a subclass with a distinct ``kind`` literal
and add it to the ``Citation`` union below.

Citation modifier fields (``signal``, ``pin_cite``, ``parenthetical``,
``weight``, ``back_ref``, ``parenthetical_kind``) live on
:class:`CitationBase` because almost every citation can carry them.

See ``docs/CITATION_TAXONOMY.md`` for the full per-family enumeration.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Modifier type aliases
# ---------------------------------------------------------------------------

SignalKind = Literal[
    "see",
    "see_also",
    "see_eg",
    "see_generally",
    "cf",
    "but_see",
    "but_cf",
    "contra",
    "accord",
    "compare_with",
    "eg",
]
"""Bluebook 21st-edition citation signals (Rule 1.2). The ``compare_with``
form is one logical signal even though Bluebook splits ``Compare ...
with ...`` across two tokens — the parser merges them."""

PinCiteKind = Literal[
    "page",
    "page_range",
    "paragraph",
    "section",
    "footnote",
    "line",
    "star",
]
"""How to interpret the ``pin_cite`` field. ``star`` is Westlaw / LEXIS
star pagination (``at *3``). ``footnote`` corresponds to ``n.5``;
``line`` to ``l. 12`` in transcript pagination."""

ParentheticalKind = Literal[
    "explanatory",
    "quoting",
    "citing",
    "weight",
    "judge",
    "history",
    "hereinafter",
]

WeightOfAuthority = Literal[
    "en_banc",
    "per_curiam",
    "plurality",
    "memorandum",
    "concurring",
    "dissenting",
    "concurring_in_part",
    "dissenting_in_part",
]

SubsequentHistoryRelation = Literal[
    "affirmed",
    "reversed",
    "vacated",
    "remanded",
    "cert_denied",
    "cert_granted",
    "overruled",
    "overruled_in_part",
    "abrogated",
    "modified",
    "reversing",
    "affirming",
]


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class CitationBase(BaseModel):
    """Fields every concrete citation subclass inherits.

    Acts as a mixin so concrete classes get consistent provenance,
    Bluebook-modifier fields, and validation without reimplementing
    them. All fields have defaults; concrete subclasses add the
    family-specific structured data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Provenance
    raw: str = Field(
        min_length=1,
        description="Exact substring from the source text that produced this citation.",
    )
    normalized: str = Field(
        min_length=1,
        description="Canonical string form — round-trips through the parser.",
    )
    span: tuple[int, int] = Field(
        description=(
            "Character offsets ``(start, end)`` of ``raw`` within the source text. "
            "Matches the ``Span.char_span`` convention used by "
            "``kaos_llm_core.signatures.grounding``."
        ),
    )
    source_uri: str | None = Field(
        default=None,
        description=(
            "Optional URI of the text this citation was extracted from. "
            "Typically ``doc_uri + block_ref`` when the source was a ``ContentDocument``."
        ),
    )
    cite_id: str = Field(
        default="",
        description=(
            "Stable per-extraction identifier (``c0001``, ``c0002``, ...) "
            "assigned in source-order by the dispatcher. ``back_ref`` and "
            "``subsequent_history`` reference other citations by this ID "
            "instead of by list index — so filtering / re-sorting the "
            "result list never breaks the cross-references. Empty string "
            "before the dispatcher's ID-assignment pass runs."
        ),
    )

    # Bluebook modifiers (Rule 1.2 signals, Rule 3 pin cites, Rule 1.5 parens, Rule 4 short forms)
    signal: SignalKind | None = Field(
        default=None,
        description="Bluebook 1.2 introductory signal preceding this cite.",
    )
    pin_cite: str | None = Field(
        default=None,
        description=(
            "Pinpoint cite — page, paragraph, section, footnote, or line. "
            "Stored as the raw token (e.g. ``491``, ``491-92``, ``¶ 12``, "
            "``§ 4.5``, ``n.5``, ``l. 12``, ``*3``)."
        ),
    )
    pin_cite_kind: PinCiteKind | None = Field(
        default=None,
        description="Type of pin cite (page / paragraph / section / footnote / line / star).",
    )
    parenthetical: str | None = Field(
        default=None,
        description=(
            "Explanatory parenthetical text (Bluebook Rule 1.5) — e.g. "
            "``holding that …``, ``per curiam``, ``Sotomayor, J., dissenting``. "
            "Outer parens stripped; inner content preserved."
        ),
    )
    parenthetical_kind: ParentheticalKind | None = Field(
        default=None,
        description=(
            "Classification of the parenthetical: explanatory (default), "
            "quoting (`(quoting Sweatt, ...)`), citing (`(citing ...)`), "
            "weight (`(en banc)`), judge (`(Sotomayor, J., dissenting)`), "
            "history (`(amended 1991)`), hereinafter."
        ),
    )
    back_ref: str | None = Field(
        default=None,
        description=(
            "``cite_id`` of the antecedent citation this short-form references "
            "(stable across filtering / re-sorting; see ``cite_id``). ``None`` "
            "for full-form cites."
        ),
    )
    string_cite_group: int | None = Field(
        default=None,
        description=(
            "Group ID for citations appearing in a Bluebook 1.4 string cite "
            "(e.g. ``See A; B; C.``). All members share the same group ID and "
            "leading signal."
        ),
    )


# ---------------------------------------------------------------------------
# Existing kinds — preserve shape from 0.1.0a1
# ---------------------------------------------------------------------------


class CFRCitation(CitationBase):
    """Code of Federal Regulations.

    Examples: ``17 CFR 240.10b-5``, ``21 CFR § 312.2``,
    ``40 CFR Part 60.7(a)(1)``, ``17 C.F.R. 240.10b5-1(c)(1)(i)``.
    """

    kind: Literal["cfr"] = "cfr"
    title: int = Field(ge=1, le=50, description="CFR title number (1-50).")
    section: str = Field(
        min_length=1,
        description=(
            "Section identifier including any subsection/paragraph suffixes, "
            "e.g. ``240.10b-5`` or ``60.7(a)(1)``. Leading ``§`` / ``Part`` stripped."
        ),
    )


class CaseCitation(CitationBase):
    """US case-law citation (eyecite ``FullCaseCitation``)."""

    kind: Literal["case"] = "case"
    volume: int | None = Field(default=None, ge=1)
    reporter: str | None = Field(default=None)
    page: int | None = Field(default=None, ge=1)
    year: int | None = Field(default=None, ge=1600, le=2200)
    case_name: str | None = Field(default=None)
    court: str | None = Field(default=None)
    weight: WeightOfAuthority | None = Field(
        default=None,
        description="Weight-of-authority tag from the parenthetical (en banc, per curiam, etc.).",
    )
    judges: tuple[str, ...] = Field(
        default=(),
        description=(
            "Judge name(s) extracted from a ``(Sotomayor, J., dissenting)``-style parenthetical."
        ),
    )
    parallel_cites: tuple[str, ...] = Field(
        default=(),
        description="Raw text of parallel reporter citations (e.g. S. Ct., L. Ed. 2d).",
    )
    subsequent_history: tuple[tuple[SubsequentHistoryRelation, str], ...] = Field(
        default=(),
        description=(
            "Subsequent-history relationships: tuple of "
            "``(relation, child_cite_id)`` pairs. ``child_cite_id`` is the "
            "``cite_id`` of the related case (stable across filtering / "
            "re-sorting; see ``cite_id``)."
        ),
    )


class StatuteCitation(CitationBase):
    """US statute citation — federal (USC, I.R.C.) and state codes (eyecite ``FullLawCitation``)."""

    kind: Literal["statute"] = "statute"
    code: str | None = Field(default=None, description="e.g. ``U.S.C.``, ``Cal. Penal Code``.")
    title: str | None = Field(default=None)
    section: str | None = Field(default=None)
    year: int | None = Field(default=None, ge=1600, le=2200)
    publisher: str | None = Field(
        default=None,
        description=(
            "Publisher of an annotated edition (e.g. ``West``, ``LexisNexis``, ``McKinney``)."
        ),
    )
    popular_name: str | None = Field(
        default=None,
        description=(
            "Popular name of the act if cited (e.g. ``Sherman Act``, "
            "``Patient Protection and Affordable Care Act``)."
        ),
    )


class PublicLawCitation(CitationBase):
    """Public Law / Statutes at Large (Bluebook R12.4)."""

    kind: Literal["public_law"] = "public_law"
    popular_name: str | None = Field(default=None)
    congress: int | None = Field(default=None, ge=1, le=200)
    public_law_number: str | None = Field(
        default=None,
        description="``Pub. L. No. 111-148`` → ``111-148``.",
    )
    section: str | None = Field(default=None)
    stat_volume: int | None = Field(default=None, ge=1)
    stat_page: int | None = Field(default=None, ge=1)
    year: int | None = Field(default=None, ge=1789, le=2200)


class FederalRegisterCitation(CitationBase):
    """Federal Register notice (``88 Fed. Reg. 12,345 (Mar. 1, 2023)``)."""

    kind: Literal["fed_register"] = "fed_register"
    volume: int | None = Field(default=None, ge=1)
    page: int | None = Field(default=None, ge=1)
    exact_date: str | None = Field(
        default=None,
        description="ISO 8601 date when extractable from the citation context.",
    )
    rule_status: Literal["proposed", "final", "notice", "interim_final"] | None = Field(
        default=None
    )
    agency: str | None = Field(default=None)
    to_be_codified_at: str | None = Field(
        default=None,
        description="``(to be codified at 29 C.F.R. pt. 791)`` parenthetical.",
    )


class ConstitutionCitation(CitationBase):
    """U.S. or state Constitution (Bluebook R11)."""

    kind: Literal["const"] = "const"
    jurisdiction: str = Field(
        default="U.S.",
        description="``U.S.`` for federal; state postal abbrev. for state constitutions.",
    )
    article: str | None = Field(default=None, description="Roman numeral when present.")
    amendment: str | None = Field(default=None, description="Roman numeral when present.")
    section: str | None = Field(default=None)
    clause: str | None = Field(default=None)
    paragraph: str | None = Field(default=None)
    is_preamble: bool = False
    status: Literal["active", "repealed", "amended", "superseded"] | None = None
    status_year: int | None = Field(default=None, ge=1789, le=2200)


class DOICitation(CitationBase):
    kind: Literal["doi"] = "doi"
    doi: str | None = Field(default=None)


class ArXivCitation(CitationBase):
    kind: Literal["arxiv"] = "arxiv"
    arxiv_id: str | None = Field(default=None)


class PubMedCitation(CitationBase):
    kind: Literal["pmid"] = "pmid"
    pmid: int | None = Field(default=None, ge=1)


class UnknownCitation(CitationBase):
    """Catch-all for matches that didn't classify into a specific family."""

    kind: Literal["unknown"] = "unknown"


# ---------------------------------------------------------------------------
# Phase 1A — short forms + journal
# ---------------------------------------------------------------------------


class IdCitation(CitationBase):
    """``Id.`` / ``Id. at NN`` short-form (Bluebook R4.1).

    Always carries ``back_ref`` (resolved by the dispatcher to the index
    of the immediately preceding cite). ``pin_cite`` carries the
    "at NN" suffix when present.
    """

    kind: Literal["id"] = "id"


class SupraCitation(CitationBase):
    """``Smith, supra note 12, at 45`` short-form (Bluebook R4.2)."""

    kind: Literal["supra"] = "supra"
    antecedent_guess: str | None = Field(
        default=None,
        description="Heuristic case/author name extracted before ``supra``.",
    )
    note_number: int | None = Field(
        default=None,
        description="``supra note 12`` → 12.",
    )


class ShortCaseCitation(CitationBase):
    """``Brown, 347 U.S. at 495`` (Bluebook R10.9)."""

    kind: Literal["case_short"] = "case_short"
    volume: int | None = Field(default=None, ge=1)
    reporter: str | None = Field(default=None)
    page: int | None = Field(default=None, ge=1)
    case_name_short: str | None = Field(default=None)


class CaseReferenceCitation(CitationBase):
    """``Roe at 240`` — case reference by name only (Bluebook R10.9)."""

    kind: Literal["case_ref"] = "case_ref"
    case_name_short: str | None = Field(default=None)


class HereinafterCitation(CitationBase):
    """``(hereinafter "Restatement")`` declaration (Bluebook R4.2(b)).

    Defines a label that subsequent short-form cites resolve against.
    The ``back_ref`` index points at the antecedent full cite.
    """

    kind: Literal["hereinafter"] = "hereinafter"
    label: str = Field(min_length=1, description="The hereinafter label, without quotes.")


class JournalCitation(CitationBase):
    """Law-review / journal article (Bluebook R16; eyecite ``FullJournalCitation``)."""

    kind: Literal["journal"] = "journal"
    authors: tuple[str, ...] = Field(default=())
    title: str | None = Field(default=None)
    volume: int | None = Field(default=None, ge=1)
    journal: str | None = Field(
        default=None, description="Reporter abbreviation (e.g. ``Yale L.J.``)."
    )
    page: int | None = Field(default=None, ge=1)
    year: int | None = Field(default=None, ge=1600, le=2200)
    note_type: Literal["article", "note", "comment", "recent_case", "symposium"] | None = None


# ---------------------------------------------------------------------------
# Phase 1B — federal rules + IRS + executive + legislative + restatements
# ---------------------------------------------------------------------------


FederalRuleSet = Literal[
    "FRCP",
    "FRCRMP",
    "FRE",
    "FRAP",
    "FRBP",
    "SCT",  # Supreme Court Rules
]


class FederalRuleCitation(CitationBase):
    """Federal Rules of Civil/Criminal/Evidence/Appellate/Bankruptcy Procedure
    + Supreme Court Rules (Bluebook R12.9). Examples:

    - ``Fed. R. Civ. P. 56(c)(1)(A)``
    - ``Fed. R. Crim. P. 11(c)(1)(C)``
    - ``Fed. R. Evid. 702``
    - ``Fed. R. App. P. 4(a)(1)(A)``
    - ``Fed. R. Bankr. P. 9011``
    - ``Sup. Ct. R. 10``
    """

    kind: Literal["fed_rule"] = "fed_rule"
    rule_set: FederalRuleSet
    rule_number: str = Field(
        min_length=1,
        description="Numeric rule, possibly with letter suffix (e.g. ``56``, ``9011``).",
    )
    subdivisions: tuple[str, ...] = Field(
        default=(),
        description="Subdivision tail like ``(c)(1)(A)`` → ``('c', '1', 'A')``.",
    )
    is_advisory_committee_note: bool = Field(
        default=False,
        description="True for ``Fed. R. Civ. P. 26 advisory committee's note to 2015 amendment``.",
    )
    amendment_year: int | None = Field(default=None, ge=1900, le=2200)


LocalRuleSet = Literal[
    "circuit",
    "district",
    "state",
    "bankruptcy",
    "patent",
]


class LocalRuleCitation(CitationBase):
    """Circuit / district / state local rules (Bluebook R12.9). Examples:

    - ``2d Cir. R. 32.1.1``
    - ``S.D.N.Y. Civ. R. 56.1``
    - ``N.Y. C.P.L.R. 3212`` (state proc.)
    - ``Cal. Evid. Code § 352`` (state evid.)
    """

    kind: Literal["local_rule"] = "local_rule"
    rule_set: LocalRuleSet
    jurisdiction: str = Field(
        description=(
            "Court / circuit / district / state identifier "
            "(``2d Cir.``, ``S.D.N.Y.``, ``N.Y.``, ``Cal.``)."
        )
    )
    rule_number: str = Field(min_length=1)
    subdivisions: tuple[str, ...] = Field(default=())


class ProfessionalConductCitation(CitationBase):
    """Model + state Rules of Professional Conduct (Bluebook R12.9)."""

    kind: Literal["pro_conduct"] = "pro_conduct"
    jurisdiction: str = Field(
        default="Model", description="``Model`` for the ABA Model Rules; state postal otherwise."
    )
    rule_number: str = Field(min_length=1)
    year: int | None = Field(default=None, ge=1900, le=2200)


class USSGCitation(CitationBase):
    """U.S. Sentencing Guidelines (Bluebook R12.9)."""

    kind: Literal["ussg"] = "ussg"
    section: str = Field(min_length=1, description="``2D1.1(a)(1)``-style.")
    subdivisions: tuple[str, ...] = Field(default=())
    year: int | None = Field(default=None, ge=1987, le=2200)


TreasuryRegulationStatus = Literal["final", "proposed", "temporary"]


class TreasuryRegulationCitation(CitationBase):
    """Treasury Regulation (Bluebook R14.5.1)."""

    kind: Literal["treas_reg"] = "treas_reg"
    section: str = Field(min_length=1, description="``1.501(c)(3)-1``-style.")
    status: TreasuryRegulationStatus = "final"
    fed_reg_volume: int | None = Field(default=None, ge=1)
    fed_reg_page: int | None = Field(default=None, ge=1)
    exact_date: str | None = None
    amendment_year: int | None = Field(default=None, ge=1900, le=2200)


IRSGuidanceKind = Literal[
    "rev_rul",
    "rev_proc",
    "notice",
    "announcement",
    "plr",
    "tam",
    "gcm",
    "fsa",
    "cca",
    "td",
    "irb",
    "irm",
]


class IRSGuidanceCitation(CitationBase):
    """IRS guidance — Rev. Rul., Rev. Proc., Notice, PLR, TAM, GCM, FSA, CCA, T.D.,
    Internal Revenue Bulletin, Internal Revenue Manual (Bluebook R14.5.2)."""

    kind: Literal["irs_guidance"] = "irs_guidance"
    guidance_kind: IRSGuidanceKind
    year: int | None = Field(default=None, ge=1900, le=2200)
    number: str | None = Field(
        default=None,
        description=(
            "Document number — e.g. ``2019-11`` for Rev. Rul. 2019-11; "
            "``2023-12-345`` for PLR; ``39,914`` for GCM; ``9930`` for T.D.; "
            "``4.10.7.2`` for IRM section."
        ),
    )
    irb_year: int | None = Field(default=None, ge=1900, le=2200)
    irb_number: int | None = Field(default=None, ge=1)
    irb_page: int | None = Field(default=None, ge=1)
    exact_date: str | None = None


ExecutiveActionKind = Literal[
    "executive_order",
    "proclamation",
    "memorandum",
    "determination",
]


class ExecutiveActionCitation(CitationBase):
    """Executive Order / Proclamation / Presidential Memorandum / Determination (Bluebook R14.7)."""

    kind: Literal["exec_action"] = "exec_action"
    action_kind: ExecutiveActionKind
    number: str | None = Field(
        default=None, description="``14,028`` for E.O. 14028; ``10,345`` for Proc. 10345."
    )
    fed_reg_volume: int | None = Field(default=None, ge=1)
    fed_reg_page: int | None = Field(default=None, ge=1)
    exact_date: str | None = None
    title: str | None = Field(
        default=None, description="Subject of memorandum or proclamation when present."
    )


LegislativeDocKind = Literal[
    "house_bill",
    "senate_bill",
    "house_joint_resolution",
    "senate_joint_resolution",
    "house_concurrent_resolution",
    "senate_concurrent_resolution",
    "house_resolution",
    "senate_resolution",
    "house_report",
    "senate_report",
    "conference_report",
    "house_document",
    "senate_document",
    "committee_print",
    "committee_hearing",
    "cong_record_bound",
    "cong_record_daily",
    "cong_globe",
]


class LegislativeCitation(CitationBase):
    """Federal legislative materials — bills, all resolution types, House/Senate/Conf reports,
    committee hearings, committee prints, Cong. Rec. (Bluebook R13)."""

    kind: Literal["legislative"] = "legislative"
    doc_kind: LegislativeDocKind
    congress: int | None = Field(default=None, ge=1, le=200)
    number: str | None = Field(default=None, description="Bill / resolution / report number.")
    section: str | None = None
    page: int | None = Field(default=None, ge=1)
    chamber_page_prefix: Literal["H", "S", "E", "D"] | None = Field(
        default=None,
        description="``Cong. Rec. H1234`` → ``H`` (House daily ed.).",
    )
    exact_date: str | None = None
    year: int | None = Field(default=None, ge=1789, le=2200)
    title: str | None = None
    speaker: str | None = None
    speaker_role: str | None = None
    committee: str | None = None
    witness: str | None = None
    witness_role: str | None = None


RestatementSeries = Literal["First", "Second", "Third", "Fourth"]


class RestatementCitation(CitationBase):
    """ALI Restatement (Bluebook R15.8)."""

    kind: Literal["restatement"] = "restatement"
    series: RestatementSeries
    subject: str = Field(min_length=1, description="``Torts``, ``Contracts``, ``Agency``, etc.")
    section: str = Field(min_length=1)
    comment_letter: str | None = None
    illustration_number: int | None = Field(default=None, ge=1)
    is_reporters_note: bool = False
    year: int | None = Field(default=None, ge=1900, le=2200)


UniformActShort = Literal[
    "U.C.C.",
    "U.P.C.",
    "U.T.C.",
    "U.A.A.",  # Uniform Arbitration Act
    "U.E.T.A.",  # Uniform Electronic Transactions Act
    "U.F.T.A.",  # Uniform Fraudulent Transfer Act
    "M.P.C.",  # Model Penal Code
    "M.B.C.A.",  # Model Business Corporation Act
    "ALI_PLS",  # ALI Principles of the Law of Software Contracts (or other Principles)
    "OTHER",
]


class UniformActCitation(CitationBase):
    """Uniform Act / Model Code / ALI Principles (Bluebook R15.8)."""

    kind: Literal["uniform_act"] = "uniform_act"
    act_short: UniformActShort
    act_full_name: str | None = None
    section: str = Field(min_length=1)
    comment_number: int | None = Field(default=None, ge=1)
    year: int | None = Field(default=None, ge=1900, le=2200)


class StateSessionLawCitation(CitationBase):
    """State session law (Bluebook R12.4, T1)."""

    kind: Literal["state_session_law"] = "state_session_law"
    state: str = Field(description="State postal abbreviation (``Fla.``, ``Cal.``).")
    year: int = Field(ge=1789, le=2200)
    chapter: str | None = None
    public_act_number: str | None = None


class TreatiseCitation(CitationBase):
    """Treatise / hornbook / multi-volume (Bluebook R15)."""

    kind: Literal["treatise"] = "treatise"
    authors: tuple[str, ...] = Field(default=())
    title: str = Field(min_length=1)
    volume: int | None = Field(default=None, ge=1)
    section: str | None = None
    edition: str | None = None
    year: int | None = Field(default=None, ge=1700, le=2200)
    publisher: str | None = None


# ---------------------------------------------------------------------------
# Phase 2 — agency adjudications, SEC, manuals, opinions, court documents
# ---------------------------------------------------------------------------


AdjudicatingAgency = Literal[
    "NLRB",
    "BIA",
    "FERC",
    "FCC",
    "FTC",
    "NTSB",
    "EPA_EAB",
    "PTAB",
    "TTAB",
    "SEC_ALJ",
    "OSHRC",
    "MSPB",
    "CFTC",
    "DOL",
    "OTHER",
]


class AgencyAdjudicationCitation(CitationBase):
    """Federal agency adjudication (Bluebook R14.3). One typed Citation
    for many agencies — distinguished by ``agency`` field."""

    kind: Literal["agency_adj"] = "agency_adj"
    agency: AdjudicatingAgency
    parties: str | None = Field(
        default=None,
        description="Case caption (``In re Acme Corp.`` or ``E.I. du Pont de Nemours & Co.``).",
    )
    volume: int | None = Field(default=None, ge=1)
    reporter: str | None = Field(
        default=None,
        description=(
            "Reporter abbreviation "
            "(``N.L.R.B.``, ``F.T.C.``, ``FCC Rcd``, ``FERC ¶``, ``I. & N. Dec.``)."
        ),
    )
    page: int | None = Field(default=None, ge=1)
    paragraph: int | None = Field(
        default=None, ge=1, description="``FERC ¶ 61,123`` paragraph number."
    )
    slip_number: str | None = Field(default=None, description="``370 N.L.R.B. No. 12`` → ``12``.")
    year: int | None = Field(default=None, ge=1900, le=2200)
    decision_authority: str | None = Field(
        default=None,
        description=(
            "``A.G.``, ``BIA``, ``OHO``, ``NAC`` etc. when distinct from the agency proper."
        ),
    )
    docket_number: str | None = None
    exact_date: str | None = None


SECAct = Literal["33", "34", "IC", "IA", "TIA"]
"""Securities Act of 1933, Securities Exchange Act of 1934, Investment
Company Act of 1940, Investment Advisers Act of 1940, Trust Indenture
Act of 1939."""


class SECReleaseCitation(CitationBase):
    """SEC rulemaking / interpretive release (Bluebook cf. R14)."""

    kind: Literal["sec_release"] = "sec_release"
    act: SECAct
    release_number: str = Field(min_length=1, description="``34-94168`` for Exchange Act 94168.")
    title: str | None = None
    fed_reg_volume: int | None = Field(default=None, ge=1)
    fed_reg_page: int | None = Field(default=None, ge=1)
    exact_date: str | None = None


SECStaffDocKind = Literal[
    "no_action",
    "sab",  # Staff Accounting Bulletin
    "slb",  # Staff Legal Bulletin
    "cdi",  # Compliance & Disclosure Interpretation
    "comment_letter",
    "concept_release",
    "interpretive_release",
]


class SECStaffGuidanceCitation(CitationBase):
    """SEC staff guidance — no-action letters, SABs, SLBs, C&DIs, comment letters."""

    kind: Literal["sec_staff"] = "sec_staff"
    doc_kind: SECStaffDocKind
    number: str | None = Field(
        default=None, description="``121`` for SAB 121, ``14L`` for SLB 14L."
    )
    requestor: str | None = Field(default=None, description="No-action letter requestor.")
    division: str | None = Field(
        default=None,
        description="``Corp. Fin.``, ``IM``, ``TM``, ``Trad. & Mkts.``.",
    )
    exact_date: str | None = None
    response_date: str | None = None
    wl_id: str | None = None
    accession_number: str | None = None
    question: str | None = Field(default=None, description="C&DI question number (``234.01``).")
    section_topic: str | None = None


class AgencyManualCitation(CitationBase):
    """Agency examining/operating manual — MPEP, TMEP, IRM, POMS (Bluebook R14.3)."""

    kind: Literal["agency_manual"] = "agency_manual"
    manual_id: Literal["MPEP", "TMEP", "IRM", "POMS", "FOM", "OTHER"]
    section: str = Field(min_length=1)
    edition: str | None = None
    revision: str | None = None
    exact_date: str | None = None


OpinionAuthority = Literal["AG", "OLC", "OTHER"]


class LegalOpinionCitation(CitationBase):
    """Attorney General Opinion / OLC Opinion (Bluebook R14.4)."""

    kind: Literal["legal_opinion"] = "legal_opinion"
    authority: OpinionAuthority
    volume: int | None = Field(default=None, ge=1)
    page: int | None = Field(default=None, ge=1)
    year: int | None = Field(default=None, ge=1789, le=2200)
    subject: str | None = None


CourtDocKind = Literal[
    "complaint",
    "answer",
    "motion",
    "opposition",
    "reply",
    "memorandum",
    "brief",
    "trial_transcript",
    "hearing_transcript",
    "deposition",
    "declaration",
    "affidavit",
    "exhibit",
    "stipulation",
    "judgment",
    "order",
    "ecf_filing",
]


class CourtDocumentCitation(CitationBase):
    """Court / litigation document (Bluebook B17 / R7)."""

    kind: Literal["court_doc"] = "court_doc"
    doc_kind: CourtDocKind
    parties: str | None = None
    docket_number: str | None = None
    court: str | None = None
    party_label: str | None = Field(default=None, description="``Pl.`` / ``Def.`` filing party.")
    paragraph: int | None = Field(default=None, ge=1)
    page_lines: str | None = Field(
        default=None,
        description="Transcript / deposition pin (``142:5-10``).",
    )
    exhibit_number: str | None = None
    ecf_number: int | None = Field(default=None, ge=1)
    declarant: str | None = None
    deponent: str | None = None
    exact_date: str | None = None


class TreatyCitation(CitationBase):
    """Bilateral / multilateral treaty (Bluebook R21.4)."""

    kind: Literal["treaty"] = "treaty"
    title: str | None = None
    parties: tuple[str, ...] = Field(default=())
    signed_date: str | None = None
    article: str | None = None
    ust_volume: int | None = Field(default=None, ge=1)
    ust_page: int | None = Field(default=None, ge=1)
    tias_number: str | None = None
    unts_volume: int | None = Field(default=None, ge=1)
    unts_page: int | None = Field(default=None, ge=1)


# ---------------------------------------------------------------------------
# Phase 2 — electronic / unpublished
# ---------------------------------------------------------------------------


class InternetCitation(CitationBase):
    """Generic internet citation (Bluebook R18) — URL + last-visited."""

    kind: Literal["internet"] = "internet"
    title: str | None = None
    source_org: str | None = None
    url: str
    last_visited: str | None = Field(default=None, description="ISO 8601 date.")


ElectronicMedium = Literal[
    "blog",
    "social_x",
    "social_facebook",
    "social_linkedin",
    "social_other",
    "video_youtube",
    "video_other",
    "podcast",
    "newsletter",
]


class ElectronicMediaCitation(CitationBase):
    """Blog / social media / video / podcast (Bluebook R18.2)."""

    kind: Literal["electronic_media"] = "electronic_media"
    medium: ElectronicMedium
    author_or_handle: str | None = None
    title: str | None = None
    platform: str | None = None
    url: str
    exact_datetime: str | None = Field(default=None, description="ISO 8601 datetime when present.")
    post_id: str | None = None
    video_id: str | None = None


class ArchiveCitation(CitationBase):
    """Archived web page (Wayback / Perma) (Bluebook R18.3)."""

    kind: Literal["archive"] = "archive"
    archive_url: str
    archive_id: str | None = None
    original_url: str | None = None
    archive_date: str | None = None
    title: str | None = None


class NewspaperCitation(CitationBase):
    """Newspaper article (print) (Bluebook R16.6)."""

    kind: Literal["newspaper"] = "newspaper"
    author: str | None = None
    title: str | None = None
    paper: str = Field(min_length=1)
    exact_date: str | None = None
    page: str | None = Field(default=None, description="``A1`` / ``B12`` / ``C5``.")
    url: str | None = None


class WorkingPaperCitation(CitationBase):
    """Working paper from a research series (Bluebook R17.2)."""

    kind: Literal["working_paper"] = "working_paper"
    authors: tuple[str, ...] = Field(default=())
    title: str | None = None
    series_org: str | None = Field(default=None, description="``Nat'l Bureau of Econ. Rsch.`` etc.")
    paper_number: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    url: str | None = None


class UnpublishedManuscriptCitation(CitationBase):
    """Unpublished manuscript (Bluebook R17)."""

    kind: Literal["unpublished"] = "unpublished"
    authors: tuple[str, ...] = Field(default=())
    title: str | None = None
    exact_date: str | None = None
    status: str | None = Field(
        default=None,
        description="``unpublished manuscript``, ``forthcoming``, ``draft``.",
    )


class LooseleafCitation(CitationBase):
    """Looseleaf service — CCH / BNA / RIA topical reporter (Bluebook R19)."""

    kind: Literal["looseleaf"] = "looseleaf"
    publisher: Literal["CCH", "BNA", "RIA", "BLOOMBERG", "OTHER"]
    reporter: str = Field(min_length=1, description="``Fed. Sec. L. Rep.``, ``OSHA Cases``, etc.")
    volume: int | None = Field(default=None, ge=1)
    binder: str | None = Field(default=None, description="``[2022 Transfer Binder]``.")
    paragraph: str | None = Field(default=None, description="``¶ 99,123``.")
    page: int | None = Field(default=None, ge=1)
    parties: str | None = None
    court: str | None = None
    exact_date: str | None = None


class BarEthicsOpinionCitation(CitationBase):
    """State bar ethics opinion (Bluebook R14.4)."""

    kind: Literal["bar_ethics"] = "bar_ethics"
    state: str
    bar_org: str | None = None
    opinion_number: str = Field(min_length=1)
    year: int | None = Field(default=None, ge=1900, le=2200)


# ---------------------------------------------------------------------------
# Phase 3 — financial citations
# ---------------------------------------------------------------------------


SECFilingForm = Literal[
    "10-K",
    "10-Q",
    "8-K",
    "10-K/A",
    "10-Q/A",
    "8-K/A",
    "S-1",
    "S-3",
    "S-4",
    "S-8",
    "S-11",
    "F-1",
    "F-3",
    "F-4",
    "20-F",
    "40-F",
    "13D",
    "13G",
    "13F-HR",
    "13F-NT",
    "14A",
    "14C",
    "ADV",
    "D",
    "144",
    "3",
    "4",
    "5",
    "N-1A",
    "N-2",
    "N-CSR",
    "N-PORT",
    "N-Q",
    "OTHER",
]


class SECFilingCitation(CitationBase):
    """SEC filing reference — 10-K / 10-Q / 8-K / S-1 / 13D / proxy / etc."""

    kind: Literal["sec_filing"] = "sec_filing"
    form: SECFilingForm
    filer: str | None = None
    filing_date: str | None = None
    period_of_report: str | None = None
    accession_number: str | None = None
    item_number: str | None = Field(
        default=None, description="``Item 1.01`` for an 8-K material agreement."
    )
    item_title: str | None = None
    cik: str | None = None


# FINRA + exchange rules
class FINRARuleCitation(CitationBase):
    kind: Literal["finra_rule"] = "finra_rule"
    rule_number: str = Field(min_length=1)
    subdivisions: tuple[str, ...] = Field(default=())


class FINRARegulatoryNoticeCitation(CitationBase):
    kind: Literal["finra_notice"] = "finra_notice"
    notice_number: str = Field(min_length=1, description="``23-12``.")
    exact_date: str | None = None


class FINRADisciplinaryCitation(CitationBase):
    kind: Literal["finra_disciplinary"] = "finra_disciplinary"
    proceeding_number: str = Field(min_length=1)
    decision_authority: Literal["OHO", "NAC", "OTHER"] | None = None
    parties: str | None = None
    exact_date: str | None = None


SecuritiesExchange = Literal["NYSE", "Nasdaq", "Cboe", "MSRB", "OCC", "OTHER"]


class ExchangeRuleCitation(CitationBase):
    """Self-regulatory organisation rule — NYSE / Nasdaq / Cboe / MSRB / OCC."""

    kind: Literal["exchange_rule"] = "exchange_rule"
    exchange: SecuritiesExchange
    rule_number: str = Field(min_length=1)
    subdivisions: tuple[str, ...] = Field(default=())
    exchange_subgroup: str | None = Field(
        default=None,
        description=(
            "Cboe sub-exchange (``BZX``/``EDGA``/``Options``) "
            "or NYSE board (``Arca``/``American``)."
        ),
    )


# Federal Reserve
class FedReserveRegulationCitation(CitationBase):
    """Federal Reserve Board regulation (Reg A through Reg KK)."""

    kind: Literal["fed_reserve_reg"] = "fed_reserve_reg"
    reg_letter: str = Field(min_length=1, description="``Z`` for Reg Z, ``DD`` for Reg DD.")
    cfr_title: int | None = Field(default=None, ge=1, le=50)
    cfr_part: str | None = None
    cfr_section: str | None = None


FedReserveLetterKind = Literal["SR", "CA", "OP", "INTERPRETIVE"]


class FedReserveLetterCitation(CitationBase):
    kind: Literal["fed_reserve_letter"] = "fed_reserve_letter"
    letter_kind: FedReserveLetterKind
    number: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    exact_date: str | None = None
    subject: str | None = None


# FDIC
FDICDocKind = Literal["FIL", "STATEMENT_OF_POLICY", "FAQ", "OTHER"]


class FDICDocumentCitation(CitationBase):
    kind: Literal["fdic_doc"] = "fdic_doc"
    doc_kind: FDICDocKind
    number: str | None = Field(default=None, description="``FIL-12-2023`` → ``12-2023``.")
    year: int | None = Field(default=None, ge=1900, le=2200)
    fed_reg_volume: int | None = Field(default=None, ge=1)
    fed_reg_page: int | None = Field(default=None, ge=1)
    exact_date: str | None = None
    title: str | None = None


# OCC
OCCDocKind = Literal["BULLETIN", "INTERPRETIVE_LETTER", "CONDITIONAL_APPROVAL", "OTHER"]


class OCCDocumentCitation(CitationBase):
    kind: Literal["occ_doc"] = "occ_doc"
    doc_kind: OCCDocKind
    number: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    exact_date: str | None = None


# CFPB
CFPBDocKind = Literal["BULLETIN", "COMPLIANCE_BULLETIN", "CIRCULAR", "ADVISORY_OPINION", "OTHER"]


class CFPBDocumentCitation(CitationBase):
    kind: Literal["cfpb_doc"] = "cfpb_doc"
    doc_kind: CFPBDocKind
    number: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    exact_date: str | None = None
    fed_reg_volume: int | None = Field(default=None, ge=1)
    fed_reg_page: int | None = Field(default=None, ge=1)


class NCUALetterCitation(CitationBase):
    kind: Literal["ncua_letter"] = "ncua_letter"
    number: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    exact_date: str | None = None


class BaselFrameworkCitation(CitationBase):
    """Basel Committee on Banking Supervision document."""

    kind: Literal["basel"] = "basel"
    document_id: str | None = Field(default=None, description="``d544``-style.")
    title: str | None = None
    exact_date: str | None = None


# CFTC
CFTCDocKind = Literal["INTERP_LETTER", "NO_ACTION", "ADVISORY", "ORDER", "RULE", "OTHER"]


class CFTCDocumentCitation(CitationBase):
    kind: Literal["cftc_doc"] = "cftc_doc"
    doc_kind: CFTCDocKind
    number: str | None = None
    division: str | None = Field(default=None, description="``DSIO``, ``DCR``, ``DMO``.")
    year: int | None = Field(default=None, ge=1900, le=2200)
    exact_date: str | None = None
    docket_number: str | None = None
    parties: str | None = None


# NAIC
NAICDocKind = Literal["MODEL_ACT", "BULLETIN", "OTHER"]


class NAICCitation(CitationBase):
    kind: Literal["naic"] = "naic"
    doc_kind: NAICDocKind
    title: str | None = None
    number: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    exact_date: str | None = None


# International finance
IntlFinancialBody = Literal["IOSCO", "FATF", "BCBS", "FSB", "OECD"]


class InternationalFinancialCitation(CitationBase):
    kind: Literal["intl_finance"] = "intl_finance"
    body: IntlFinancialBody
    document_id: str | None = None
    title: str | None = None
    recommendation_number: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    exact_date: str | None = None


# ---------------------------------------------------------------------------
# Phase 4 — accounting citations
# ---------------------------------------------------------------------------


class ASCCitation(CitationBase):
    """FASB Accounting Standards Codification (US GAAP)."""

    kind: Literal["asc"] = "asc"
    topic: int = Field(
        ge=100, le=999, description="ASC topic (e.g. 805 for Business Combinations)."
    )
    subtopic: int | None = Field(default=None, ge=0, le=999)
    section: int | None = Field(default=None, ge=0, le=999)
    paragraph: str | None = Field(
        default=None, description="String — can include letters (``25-1A``)."
    )


class ASUCitation(CitationBase):
    """FASB Accounting Standards Update."""

    kind: Literal["asu"] = "asu"
    year: int = Field(ge=2009, le=2200, description="ASU year (first ASU was 2009).")
    sequence: int = Field(ge=1, description="Sequence number within the year.")
    title: str | None = None
    exact_date: str | None = None


LegacyFASBStatementKind = Literal[
    "FAS",  # FASB Statement of Financial Accounting Standards
    "FIN",  # FASB Interpretation
    "CON",  # FASB Concepts Statement
    "FSP",  # FASB Staff Position
    "EITF",  # Emerging Issues Task Force
    "TB",  # FASB Technical Bulletin
    "APB",  # APB Opinion (pre-FASB)
    "ARB",  # Accounting Research Bulletin (pre-FASB)
]


class LegacyFASBCitation(CitationBase):
    """Pre-codification FASB / APB / ARB citation."""

    kind: Literal["legacy_fasb"] = "legacy_fasb"
    statement_kind: LegacyFASBStatementKind
    number: str = Field(
        min_length=1, description="``142`` for FAS 142; ``02-13`` for EITF Issue 02-13."
    )
    title: str | None = None
    exact_date: str | None = None


PCAOBDocKind = Literal["AS", "PRACTICE_ALERT", "RELEASE", "RULE", "STAFF_QA", "OTHER"]


class PCAOBCitation(CitationBase):
    kind: Literal["pcaob"] = "pcaob"
    doc_kind: PCAOBDocKind
    number: str | None = Field(
        default=None, description="``2401`` for AS 2401; ``2023-001`` for releases."
    )
    title: str | None = None
    exact_date: str | None = None


AICPADocKind = Literal[
    "SAS",
    "SSAE",
    "SSARS",
    "SOP",
    "AAG",  # Audit & Accounting Guide
    "CODE",  # Code of Professional Conduct
    "PRACTICE_ALERT",
    "TQA",
    "ISSUES_PAPER",
    "OTHER",
]


class AICPACitation(CitationBase):
    kind: Literal["aicpa"] = "aicpa"
    doc_kind: AICPADocKind
    number: str | None = None
    section: str | None = None
    title: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)
    exact_date: str | None = None


SECRegulationKind = Literal["S-X", "S-K", "G", "AB", "M", "FD", "BTR", "S-T", "OTHER"]


class SECRegulationCitation(CitationBase):
    """SEC regulation by name — Reg S-X, S-K, G, etc. (cross-references CFR title 17)."""

    kind: Literal["sec_reg"] = "sec_reg"
    regulation: SECRegulationKind
    cfr_title: int | None = Field(default=None, ge=1, le=50)
    cfr_section: str | None = None
    item: str | None = Field(default=None, description="``Item 303`` for Reg S-K MD&A.")
    title: str | None = None


IFRSStandardKind = Literal["IFRS", "IAS", "IFRIC", "SIC", "PS", "CF"]
"""IFRS Standard, International Accounting Standard (legacy IFRS), IFRS
Interpretations Committee Interpretation, Standing Interpretations
Committee (legacy), Practice Statement, Conceptual Framework."""


class IFRSCitation(CitationBase):
    kind: Literal["ifrs"] = "ifrs"
    standard_kind: IFRSStandardKind
    number: str = Field(
        min_length=1, description="``15`` for IFRS 15; ``36`` for IAS 36; ``23`` for IFRIC 23."
    )
    paragraph: str | None = Field(default=None, description="``31`` (IFRS 15.31).")
    title: str | None = None
    exact_date: str | None = None


IAASBStandardKind = Literal["ISA", "ISAE", "ISRE", "ISRS", "ISQM", "ISQC"]


class IAASBCitation(CitationBase):
    """IAASB international standards — ISA / ISAE / ISRE / ISRS / ISQM."""

    kind: Literal["iaasb"] = "iaasb"
    standard_kind: IAASBStandardKind
    number: str = Field(min_length=1, description="``315`` for ISA 315.")
    revision: str | None = Field(default=None, description="``Revised 2019``.")
    title: str | None = None
    exact_date: str | None = None


class IESBACodeCitation(CitationBase):
    """IESBA Code of Ethics for Professional Accountants."""

    kind: Literal["iesba"] = "iesba"
    section: str = Field(min_length=1)
    year: int | None = Field(default=None, ge=1900, le=2200)


GASBDocKind = Literal[
    "STATEMENT",
    "INTERPRETATION",
    "IMPLEMENTATION_GUIDE",
    "CONCEPTS_STATEMENT",
    "TECHNICAL_BULLETIN",
]


class GASBCitation(CitationBase):
    kind: Literal["gasb"] = "gasb"
    doc_kind: GASBDocKind
    number: str = Field(min_length=1)
    paragraph: str | None = None
    title: str | None = None
    exact_date: str | None = None


FASABDocKind = Literal["SFFAS", "CONCEPTS_STATEMENT", "INTERPRETATION", "TECHNICAL_BULLETIN"]


class FASABCitation(CitationBase):
    kind: Literal["fasab"] = "fasab"
    doc_kind: FASABDocKind
    number: str = Field(min_length=1)
    title: str | None = None
    exact_date: str | None = None


GovtAuditDocKind = Literal[
    "OMB_CIRCULAR",
    "GAO_YELLOWBOOK",
    "OMB_MEMORANDUM",
    "GAO_REPORT",
]


class GovernmentAuditCitation(CitationBase):
    """OMB Circular / GAO Yellow Book / GAO Report / OMB Memorandum."""

    kind: Literal["govt_audit"] = "govt_audit"
    doc_kind: GovtAuditDocKind
    document_id: str | None = Field(
        default=None, description="``A-133`` / ``A-87`` for OMB; report number for GAO."
    )
    title: str | None = None
    revision_year: int | None = Field(default=None, ge=1900, le=2200)


class NAICAccountingCitation(CitationBase):
    """NAIC Statutory Accounting Principles (SAP / SSAP)."""

    kind: Literal["naic_acct"] = "naic_acct"
    ssap_number: str = Field(min_length=1, description="``5R``-style.")
    title: str | None = None
    revision: str | None = None
    year: int | None = Field(default=None, ge=1900, le=2200)


SustainabilityFramework = Literal[
    "GRI",
    "SASB",
    "TCFD",
    "ISSB",  # International Sustainability Standards Board (IFRS S1, S2, ...)
    "ESRS",  # European Sustainability Reporting Standards
    "CDP",
    "OTHER",
]


class SustainabilityCitation(CitationBase):
    """Sustainability / ESG reporting framework citation."""

    kind: Literal["sustainability"] = "sustainability"
    framework: SustainabilityFramework
    standard_id: str | None = Field(
        default=None,
        description=(
            "``305`` for GRI 305; ``S1``/``S2`` for ISSB IFRS Sustainability; "
            "``FB-FR-110a.1`` for SASB."
        ),
    )
    title: str | None = None
    sector: str | None = None
    industry: str | None = None
    version_year: int | None = Field(default=None, ge=2000, le=2200)
    exact_date: str | None = None


class FFIECCallReportCitation(CitationBase):
    """FFIEC Call Report (banking regulatory)."""

    kind: Literal["ffiec_call"] = "ffiec_call"
    form_number: str = Field(min_length=1, description="``031`` / ``041`` / ``051``.")
    schedule: str | None = None
    item: str | None = None
    period: str | None = None


# ---------------------------------------------------------------------------
# The discriminated union
# ---------------------------------------------------------------------------


Citation = Annotated[
    # Existing
    CFRCitation
    | CaseCitation
    | StatuteCitation
    | PublicLawCitation
    | FederalRegisterCitation
    | ConstitutionCitation
    | DOICitation
    | ArXivCitation
    | PubMedCitation
    | UnknownCitation
    # Phase 1A — short forms + journal
    | IdCitation
    | SupraCitation
    | ShortCaseCitation
    | CaseReferenceCitation
    | HereinafterCitation
    | JournalCitation
    # Phase 1B — federal rules / IRS / executive / legislative / restatements
    | FederalRuleCitation
    | LocalRuleCitation
    | ProfessionalConductCitation
    | USSGCitation
    | TreasuryRegulationCitation
    | IRSGuidanceCitation
    | ExecutiveActionCitation
    | LegislativeCitation
    | RestatementCitation
    | UniformActCitation
    | StateSessionLawCitation
    | TreatiseCitation
    # Phase 2 — agency / SEC / manuals / opinions / electronic
    | AgencyAdjudicationCitation
    | SECReleaseCitation
    | SECStaffGuidanceCitation
    | AgencyManualCitation
    | LegalOpinionCitation
    | CourtDocumentCitation
    | TreatyCitation
    | InternetCitation
    | ElectronicMediaCitation
    | ArchiveCitation
    | NewspaperCitation
    | WorkingPaperCitation
    | UnpublishedManuscriptCitation
    | LooseleafCitation
    | BarEthicsOpinionCitation
    # Phase 3 — financial
    | SECFilingCitation
    | FINRARuleCitation
    | FINRARegulatoryNoticeCitation
    | FINRADisciplinaryCitation
    | ExchangeRuleCitation
    | FedReserveRegulationCitation
    | FedReserveLetterCitation
    | FDICDocumentCitation
    | OCCDocumentCitation
    | CFPBDocumentCitation
    | NCUALetterCitation
    | BaselFrameworkCitation
    | CFTCDocumentCitation
    | NAICCitation
    | InternationalFinancialCitation
    # Phase 4 — accounting
    | ASCCitation
    | ASUCitation
    | LegacyFASBCitation
    | PCAOBCitation
    | AICPACitation
    | SECRegulationCitation
    | IFRSCitation
    | IAASBCitation
    | IESBACodeCitation
    | GASBCitation
    | FASABCitation
    | GovernmentAuditCitation
    | NAICAccountingCitation
    | SustainabilityCitation
    | FFIECCallReportCitation,
    Field(discriminator="kind"),
]


__all__ = [
    # Phase 4
    "AICPACitation",
    "AICPADocKind",
    "ASCCitation",
    "ASUCitation",
    # Phase 2
    "AdjudicatingAgency",
    "AgencyAdjudicationCitation",
    "AgencyManualCitation",
    # Existing
    "ArXivCitation",
    "ArchiveCitation",
    "BarEthicsOpinionCitation",
    # Phase 3
    "BaselFrameworkCitation",
    "CFPBDocKind",
    "CFPBDocumentCitation",
    "CFRCitation",
    "CFTCDocKind",
    "CFTCDocumentCitation",
    "CaseCitation",
    # Phase 1A
    "CaseReferenceCitation",
    "Citation",
    "CitationBase",
    "ConstitutionCitation",
    "CourtDocKind",
    "CourtDocumentCitation",
    "DOICitation",
    "ElectronicMediaCitation",
    "ElectronicMediaCitation",
    "ElectronicMedium",
    "ExchangeRuleCitation",
    # Phase 1B
    "ExecutiveActionCitation",
    "ExecutiveActionKind",
    "FASABCitation",
    "FASABDocKind",
    "FDICDocKind",
    "FDICDocumentCitation",
    "FFIECCallReportCitation",
    "FINRADisciplinaryCitation",
    "FINRARegulatoryNoticeCitation",
    "FINRARuleCitation",
    "FedReserveLetterCitation",
    "FedReserveLetterKind",
    "FedReserveRegulationCitation",
    "FederalRegisterCitation",
    "FederalRuleCitation",
    "FederalRuleSet",
    "GASBCitation",
    "GASBDocKind",
    "GovernmentAuditCitation",
    "GovtAuditDocKind",
    "HereinafterCitation",
    "IAASBCitation",
    "IAASBStandardKind",
    "IESBACodeCitation",
    "IFRSCitation",
    "IFRSStandardKind",
    "IRSGuidanceCitation",
    "IRSGuidanceKind",
    "IdCitation",
    "InternationalFinancialCitation",
    "InternetCitation",
    "IntlFinancialBody",
    "JournalCitation",
    "LegacyFASBCitation",
    "LegacyFASBStatementKind",
    "LegalOpinionCitation",
    "LegislativeCitation",
    "LegislativeDocKind",
    "LocalRuleCitation",
    "LocalRuleSet",
    "LooseleafCitation",
    "NAICAccountingCitation",
    "NAICCitation",
    "NAICDocKind",
    "NCUALetterCitation",
    "NewspaperCitation",
    "OCCDocKind",
    "OCCDocumentCitation",
    "OpinionAuthority",
    "PCAOBCitation",
    "PCAOBDocKind",
    # Modifier types
    "ParentheticalKind",
    "PinCiteKind",
    "ProfessionalConductCitation",
    "PubMedCitation",
    "PublicLawCitation",
    "RestatementCitation",
    "RestatementSeries",
    "SECAct",
    "SECFilingCitation",
    "SECFilingForm",
    "SECRegulationCitation",
    "SECRegulationKind",
    "SECReleaseCitation",
    "SECStaffDocKind",
    "SECStaffGuidanceCitation",
    "SecuritiesExchange",
    "ShortCaseCitation",
    "SignalKind",
    "StateSessionLawCitation",
    "StatuteCitation",
    "SubsequentHistoryRelation",
    "SupraCitation",
    "SustainabilityCitation",
    "SustainabilityFramework",
    "TreasuryRegulationCitation",
    "TreasuryRegulationStatus",
    "TreatiseCitation",
    "TreatyCitation",
    "USSGCitation",
    "UniformActCitation",
    "UniformActShort",
    "UnknownCitation",
    "UnpublishedManuscriptCitation",
    "WeightOfAuthority",
    "WorkingPaperCitation",
]
