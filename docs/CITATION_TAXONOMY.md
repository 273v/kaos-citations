# Citation taxonomy — kaos-citations

Comprehensive enumeration of legal, financial, and accounting citations
that should parse into structured `Citation` subclasses. One row per
distinct citation family. Each row carries:

- **Family** — short identifier
- **Bluebook rule** (where applicable) — rule number from Bluebook
  21st edition; `—` if the family lives outside the Bluebook
- **Canonical example** — real-world example
- **Structured fields** — what the typed citation should extract
- **Source / resolver** — where to find authoritative text for resolution

Common base fields on every citation (subset of `CitationBase`):
`raw`, `normalized`, `span`, `source_uri`, `kind`, `signal`,
`pin_cite`, `pin_cite_kind`, `parenthetical`, `parenthetical_kind`,
`weight`, `back_ref`, `string_cite_group`, `subsequent_history`.
Family-specific fields are added per row.

---

## 1. US Legal citations

### 1.1 Cases

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **SCOTUS — U.S. Reports** | R10 | `Brown v. Bd. of Educ., 347 U.S. 483, 495 (1954)` | volume, reporter (`U.S.`), page, pin_cite, year, court (`SCOTUS`), case_name | CourtListener / supremecourt.gov |
| **SCOTUS — S. Ct. parallel** | R10 | `347 U.S. 483, 74 S. Ct. 686 (1954)` | parallel_cites (S. Ct., L. Ed., L. Ed. 2d) | CourtListener |
| **SCOTUS — pre-1875 nominate reporters** | R10, T1 | `Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)` | nominative_reporter, nominative_volume | CourtListener |
| **Federal circuit (F./F.2d/F.3d/F.4th)** | R10 | `Doe v. Doe, 73 F.4th 102, 110 (2d Cir. 2023)` | volume, reporter, page, pin_cite, year, circuit, case_name | CourtListener |
| **Federal circuit unreported** | R10.8.1 | `Smith v. Jones, 525 F. App'x 314 (4th Cir. 2013)` | volume, reporter (`F. App'x`), page, year, circuit | CourtListener |
| **Federal district** | R10 | `Doe v. Roe, 88 F. Supp. 2d 116, 127 (S.D.N.Y. 1999)` | volume, reporter (`F. Supp.`/`F. Supp. 2d`/`F. Supp. 3d`), page, pin_cite, year, district | CourtListener |
| **Federal Rules Decisions** | R10 | `Smith v. Jones, 200 F.R.D. 555, 558 (E.D. Pa. 2001)` | volume, reporter (`F.R.D.`), page, year, district | CourtListener |
| **U.S. Court of Federal Claims** | R10 | `Doe v. United States, 50 Fed. Cl. 5 (2001)` | volume, reporter (`Fed. Cl.`/`Cl. Ct.`), page, year | CourtListener |
| **U.S. Tax Court (regular)** | R10 | `Smith v. Comm'r, 145 T.C. 12 (2015)` | volume, reporter (`T.C.`), page, year | ustaxcourt.gov |
| **U.S. Tax Court (memo)** | R10 | `Smith v. Comm'r, T.C.M. (RIA) 2020-12` / `T.C.M. (CCH) ¶ 2020-12` | year, memo_number, publisher (RIA/CCH) | ustaxcourt.gov |
| **U.S. Bankruptcy Court** | R10 | `In re Acme Corp., 123 B.R. 456 (Bankr. S.D.N.Y. 2000)` | volume, reporter (`B.R.`), page, year, district, debtor_name | PACER / CourtListener |
| **State high court — official reporter** | R10, T1 | `People v. Goetz, 68 N.Y.2d 96, 102 (1986)` | volume, official_reporter (`N.Y.2d`), page, pin_cite, year, court_state | per-state |
| **State high court — regional parallel** | R10, T1 | `497 N.E.2d 41, 44 (N.Y. 1986)` | regional_reporter (`N.E.2d`/`P.3d`/`A.3d`/`So. 3d`/`S.E.2d`/`S.W.3d`/`N.W.2d`), volume, page, court_jurisdiction | per-state |
| **State intermediate appellate** | R10, T1 | `Doe v. Roe, 245 Cal. Rptr. 3d 12 (Ct. App. 2019)` | reporter, volume, page, year, court, division/department | per-state |
| **State trial court** | R10, T1 | `Smith v. Jones, 50 Misc. 3d 100 (N.Y. Sup. Ct. 2015)` | reporter, volume, page, year, court, county | per-state |
| **Westlaw unreported** | R10.8.1 | `Doe v. Roe, No. 22-cv-1234, 2023 WL 1234567, at *3 (S.D.N.Y. Mar. 14, 2023)` | docket_number, year, wl_id, pin_cite (star_page), court, exact_date | Westlaw |
| **LEXIS unreported** | R10.8.1 | `Doe v. Roe, 2023 U.S. Dist. LEXIS 12345 (S.D.N.Y. Mar. 14, 2023)` | docket_number, year, lexis_id, court, exact_date | Lexis |
| **Slip opinion / docket-only** | R10.8.1 | `United States v. Doe, No. 23-1234, slip op. at 5 (D.D.C. June 1, 2024)` | docket_number, court, slip_op_pin, exact_date | PACER |
| **Subsequent history annotation** | R10.7 | `…, aff'd, 521 U.S. 1 (1997)` / `cert. denied, 600 U.S. 700 (2024)` / `vacated`, `rev'd in part`, `overruled by` | parent_citation, history_type (`affirmed`/`reversed`/`cert_denied`/`cert_granted`/`vacated`/`overruled`/`overruled_in_part`/`abrogated`), child_citation | CourtListener |
| **Prior history annotation** | R10.7 | `521 U.S. 1 (1997), rev'g 100 F.3d 1 (2d Cir. 1996)` | child_citation, history_type (`reversing`/`affirming`), parent_citation | CourtListener |
| **Weight-of-authority parenthetical** | R10.6.1 | `(en banc)` / `(per curiam)` / `(plurality)` / `(mem.)` | weight (`en_banc`/`per_curiam`/`plurality`/`memorandum`) | n/a |
| **Judge-specific parenthetical** | R10.6.1 | `(Sotomayor, J., dissenting)` / `(Roberts, C.J., concurring)` | judge, opinion_role (`majority`/`concurring`/`dissenting`/`plurality`/`per_curiam`), title (`J.`/`C.J.`) | n/a |
| **Foreign jurisdiction in U.S. brief** | R10.4 | `R. v. Oakes, [1986] 1 S.C.R. 103 (Can.)` | jurisdiction, citation_form_native | per-country (out of v0.2 scope) |

### 1.2 Constitutions

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **U.S. Constitution — article** | R11 | `U.S. Const. art. III, § 2, cl. 1` | article (Roman), section, clause, paragraph | constitution.congress.gov |
| **U.S. Constitution — amendment** | R11 | `U.S. Const. amend. XIV, § 1` | amendment (Roman), section, clause | constitution.congress.gov |
| **U.S. Constitution — preamble** | R11 | `U.S. Const. pmbl.` | (preamble flag) | constitution.congress.gov |
| **U.S. Constitution — repealed** | R11 | `U.S. Const. art. I, § 9, cl. 4 (amended 1913)` | provision, amendment_year, status (`repealed`/`amended`/`superseded`) | constitution.congress.gov |
| **State constitution** | R11 | `Cal. Const. art. I, § 7(a)` | state, article, section, subdivision | per-state |

### 1.3 Federal statutes + session laws

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **U.S. Code (current)** | R12 | `42 U.S.C. § 1983 (2018)` | title (int), section, year, edition (`U.S.C.`/`U.S.C.A.`/`U.S.C.S.`) | uscode.house.gov / govinfo |
| **U.S. Code with subsections** | R12 | `18 U.S.C. § 924(c)(1)(A)(ii)` | title, section, subsections (list of subdivision tokens) | uscode.house.gov |
| **U.S. Code — popular name** | R12 | `Sherman Act, 15 U.S.C. § 1` | popular_name, title, section | uscode.house.gov |
| **I.R.C. (Title 26 short form)** | R12.9.4 | `I.R.C. § 501(c)(3)` | section, subsections, year | uscode.house.gov |
| **U.S. Code Annotated (West)** | R12.5 | `42 U.S.C.A. § 1983 (West 2024)` | title, section, year, publisher (`West`) | Westlaw |
| **U.S. Code Service (Lexis)** | R12.5 | `42 U.S.C.S. § 1983 (LexisNexis 2024)` | title, section, year, publisher (`LexisNexis`) | Lexis |
| **Public Law** | R12.4 | `Patient Protection and Affordable Care Act, Pub. L. No. 111-148, 124 Stat. 119 (2010)` | popular_name, congress, public_law_number, stat_volume, stat_page, year | govinfo (Pub. L.) |
| **Public Law with pinpoint** | R12.4 | `Pub. L. No. 111-148, § 1101, 124 Stat. 119, 141 (2010)` | public_law_number, section, stat_volume, stat_page, pin_cite, year | govinfo |
| **Statutes at Large only** | R12.4 | `124 Stat. 119 (2010)` | volume, page, year | govinfo |
| **Repealed / amended notation** | R12.10 | `42 U.S.C. § 1981 (1976) (amended 1991)` | base_citation, status (`repealed`/`amended`/`superseded`), status_year | uscode.house.gov |
| **U.S. Code historical edition** | R12.3.2 | `42 U.S.C. § 1983 (1958)` | title, section, edition_year | govinfo (historical) |

### 1.4 State statutes + session laws

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **State code (compiled — by topic)** | R12, T1 | `N.Y. C.P.L.R. § 3211(a)(7) (McKinney 2023)` | state, code_name, section, subdivisions, publisher, year | per-state |
| **State code (numbered title)** | R12, T1 | `Cal. Penal Code § 187 (West 2024)` | state, code_name, section, publisher, year | per-state |
| **State session law** | R12.4, T1 | `2023 Fla. Laws ch. 2023-22` | year, state, chapter | per-state |
| **State popular-name acts** | R12 | `California Consumer Privacy Act, Cal. Civ. Code § 1798.100` | popular_name, state, code, section | per-state |

### 1.5 Federal rules + court rules

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **Federal Rules of Civil Procedure** | R12.9 | `Fed. R. Civ. P. 56(c)(1)(A)` | rule_number (str), subdivisions | law.cornell.edu (LII) / uscourts.gov |
| **Federal Rules of Criminal Procedure** | R12.9 | `Fed. R. Crim. P. 11(c)(1)(C)` | rule_number, subdivisions | LII / uscourts.gov |
| **Federal Rules of Evidence** | R12.9 | `Fed. R. Evid. 702` | rule_number, subdivisions | LII / uscourts.gov |
| **Federal Rules of Appellate Procedure** | R12.9 | `Fed. R. App. P. 4(a)(1)(A)` | rule_number, subdivisions | LII / uscourts.gov |
| **Federal Rules of Bankruptcy Procedure** | R12.9 | `Fed. R. Bankr. P. 9011` | rule_number, subdivisions | LII / uscourts.gov |
| **FRCP advisory committee notes** | R12.9 | `Fed. R. Civ. P. 26 advisory committee's note to 2015 amendment` | rule_number, amendment_year | LII |
| **Supreme Court Rules** | R12.9 | `Sup. Ct. R. 10` | rule_number | supremecourt.gov |
| **Circuit local rules** | R12.9 | `2d Cir. R. 32.1.1` | circuit, rule_number | per-circuit |
| **District local rules** | R12.9 | `S.D.N.Y. Civ. R. 56.1` | district, rule_set (`Civ.`/`Crim.`/`Bankr.`/`Pat.`), rule_number | per-district |
| **State Rules of Civil Procedure** | R12.9, T1 | `N.Y. C.P.L.R. 3212` | state, rule_number, subdivisions | per-state |
| **State Rules of Evidence** | R12.9, T1 | `Cal. Evid. Code § 352` | state, rule_number | per-state |
| **State Rules of Appellate Procedure** | R12.9, T1 | `Cal. Rules of Court 8.204` | state, rule_number | per-state |
| **Model Rules of Professional Conduct (ABA)** | R12.9 | `Model Rules of Pro. Conduct r. 1.7 (Am. Bar Ass'n 2023)` | rule_number, year | americanbar.org |
| **State Rules of Professional Conduct** | R12.9, T1 | `N.Y. Rules of Pro. Conduct r. 1.7` | state, rule_number | per-state bar |
| **U.S. Sentencing Guidelines** | R12.9 | `U.S.S.G. § 2D1.1(a)(1)` | section, subdivisions, year (default current) | ussc.gov |

### 1.6 Federal regulations

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **Code of Federal Regulations** | R14.2 | `17 C.F.R. § 240.10b-5(b)(1)(i) (2023)` | title (int), part, section, subdivisions, year | ecfr.gov |
| **C.F.R. — part-only** | R14.2 | `40 C.F.R. pt. 60 (2023)` | title, part, year, scope (`part`/`subpart`/`section`) | ecfr.gov |
| **Federal Register — proposed rule** | R14.2 | `Definition of Employer, 88 Fed. Reg. 12,345, 12,350 (Mar. 1, 2023) (proposed) (to be codified at 29 C.F.R. pt. 791)` | volume, page, pin_cite, exact_date, status (`proposed`), to_be_codified, agency | federalregister.gov |
| **Federal Register — final rule** | R14.2 | `Same as above, but with `(final)` instead of `(proposed)`` | …, status (`final`) | federalregister.gov |
| **Federal Register — notice** | R14.2 | `88 Fed. Reg. 45,678 (July 18, 2023)` | volume, page, exact_date | federalregister.gov |
| **Treasury Regulation — final** | R14.5.1 | `Treas. Reg. § 1.501(c)(3)-1 (as amended in 2023)` | section, status_amendment_year | ecfr.gov (26 C.F.R.) |
| **Treasury Regulation — proposed** | R14.5.1 | `Prop. Treas. Reg. § 1.401(k)-1, 88 Fed. Reg. 12,345 (Mar. 1, 2023)` | section, status (`proposed`), fed_reg_volume, fed_reg_page, exact_date | federalregister.gov |
| **Treasury Regulation — temporary** | R14.5.1 | `Temp. Treas. Reg. § 1.401(k)-1T` | section, status (`temporary`) | ecfr.gov |
| **State administrative code** | R14, T1 | `N.Y. Comp. Codes R. & Regs. tit. 12, § 142-2.2` | state, title, section | per-state |

### 1.7 Federal agency materials (executive)

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **Executive Order** | R14.7 | `Exec. Order No. 14,028, 86 Fed. Reg. 26,633 (May 12, 2021)` | order_number, fed_reg_volume, fed_reg_page, exact_date, president (lookup) | federalregister.gov |
| **Presidential Proclamation** | R14.7 | `Proclamation No. 10,345, 87 Fed. Reg. 1234 (Jan. 5, 2022)` | proclamation_number, fed_reg_volume, fed_reg_page, exact_date | federalregister.gov |
| **Presidential Memorandum** | R14.7 | `Memorandum on Delegation of Authority, 88 Fed. Reg. 9876 (Feb. 14, 2023)` | subject, fed_reg_volume, fed_reg_page, exact_date | federalregister.gov |
| **Presidential Determination** | R14.7 | `Presidential Determination No. 2023-04, 88 Fed. Reg. 1234 (Jan. 5, 2023)` | determination_number, fed_reg_volume, fed_reg_page, exact_date | federalregister.gov |
| **Treaty (bilateral, post-1950)** | R21.4 | `Treaty of Friendship, U.S.-Japan, Apr. 2, 1953, 4 U.S.T. 2063, T.I.A.S. No. 2863` | name, parties, signed_date, ust_volume, ust_page, tias_number | state.gov / Treaties in Force |
| **Treaty (multilateral)** | R21.4 | `Vienna Convention on the Law of Treaties art. 31, May 23, 1969, 1155 U.N.T.S. 331` | name, signed_date, unts_volume, unts_page, article | UN Treaty Collection |
| **Attorney General Opinion** | R14.4 | `42 Op. Att'y Gen. 5 (1981)` | volume, page, year | justice.gov |
| **OLC Opinion** | R14.4 | `Memorandum Opinion for the Att'y Gen., 38 Op. O.L.C. 1 (2014)` | volume, page, year, subject | justice.gov/olc |

### 1.8 IRS / Treasury guidance

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **Revenue Ruling** | R14.5.2 | `Rev. Rul. 2019-11, 2019-19 I.R.B. 1041` | year, number, irb_year, irb_number, irb_page | irs.gov |
| **Revenue Procedure** | R14.5.2 | `Rev. Proc. 2023-1, 2023-1 I.R.B. 1` | year, number, irb_year, irb_number, irb_page | irs.gov |
| **IRS Notice** | R14.5.2 | `I.R.S. Notice 2023-7, 2023-3 I.R.B. 390` | year, number, irb_year, irb_number, irb_page | irs.gov |
| **IRS Announcement** | R14.5.2 | `I.R.S. Announcement 2023-2, 2023-2 I.R.B. 388` | year, number, irb_year, irb_number, irb_page | irs.gov |
| **Private Letter Ruling (PLR)** | R14.5.2 | `I.R.S. Priv. Ltr. Rul. 2023-12-345 (Mar. 24, 2023)` | year, week, sequence (compound number `YYYY-WW-NNN`), exact_date | irs.gov |
| **Technical Advice Memorandum (TAM)** | R14.5.2 | `I.R.S. Tech. Adv. Mem. 2023-04-001 (Jan. 27, 2023)` | year, week, sequence, exact_date | irs.gov |
| **General Counsel Memorandum (GCM)** | R14.5.2 | `I.R.S. Gen. Couns. Mem. 39,914 (Aug. 5, 1992)` | gcm_number, exact_date | irs.gov |
| **Field Service Advice (FSA)** | R14.5.2 | `I.R.S. Field Serv. Adv. 2023-01-001 (Jan. 5, 2023)` | year, week, sequence, exact_date | irs.gov |
| **Chief Counsel Advice (CCA)** | R14.5.2 | `I.R.S. Chief Couns. Adv. 2023-01-001` | year, week, sequence | irs.gov |
| **Treasury Decision** | R14.5.1 | `T.D. 9930, 85 Fed. Reg. 80,402 (Dec. 11, 2020)` | td_number, fed_reg_volume, fed_reg_page, exact_date | federalregister.gov |
| **Internal Revenue Bulletin** | R14.5.2 | `2023-19 I.R.B. 1041` | irb_year, irb_number, page | irs.gov |
| **Internal Revenue Manual** | R14.3 | `Internal Revenue Manual § 4.10.7.2 (Sept. 1, 2023)` | section, exact_date | irs.gov |

### 1.9 Federal agency adjudications + manuals

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **NLRB Decision** | R14.3 | `E.I. du Pont de Nemours & Co., 311 NLRB 893 (1993)` / `In re Acme Corp., 370 N.L.R.B. No. 12 (Mar. 1, 2020)` | volume, page or slip_number, year, parties | nlrb.gov |
| **EPA Environmental Appeals Board** | R14.3 | `In re Acme Corp., 13 E.A.D. 100 (EAB 2006)` | volume, reporter (`E.A.D.`), page, year | epa.gov/eab |
| **FERC Decision** | R14.3 | `Acme Corp., 162 FERC ¶ 61,123 (2018)` | volume, paragraph, year, parties | ferc.gov |
| **FCC Decision** | R14.3 | `In re Acme Corp., 35 FCC Rcd 12,789 (2020)` | volume, reporter (`FCC Rcd`/`F.C.C.2d`), page, year | fcc.gov |
| **FTC Decision** | R14.3 | `In re Acme Corp., 162 F.T.C. 1 (2016)` | volume, reporter (`F.T.C.`), page, year | ftc.gov |
| **NTSB Decision** | R14.3 | `In re Acme Air, 6 N.T.S.B. 100 (1997)` | volume, page, year | ntsb.gov |
| **BIA Decision (immigration)** | R14.3 | `Matter of A-B-, 27 I. & N. Dec. 316 (A.G. 2018)` | volume, reporter (`I. & N. Dec.`), page, year, decision_authority (`A.G.`/`BIA`) | justice.gov/eoir |
| **PTAB Decision (patent)** | R14.3 | `Ex parte Smith, Appeal 2020-002,345 (PTAB 2021)` | appeal_number, year, application_number | uspto.gov |
| **TTAB Decision (trademark)** | R14.3 | `In re Acme Corp., Ser. No. 87/123,456 (TTAB 2020)` | serial_number, year | uspto.gov |
| **MPEP (patent examining manual)** | R14.3 | `U.S. Patent & Trademark Off., Manual of Patent Examining Procedure § 2106 (9th ed. Rev. 7, June 2022)` | section, edition, revision, exact_date | uspto.gov |
| **TMEP (trademark examining manual)** | R14.3 | `U.S. Patent & Trademark Off., Trademark Manual of Examining Procedure § 1202.02 (Nov. 2024)` | section, exact_date | uspto.gov |
| **SSA Field Operations Manual (POMS)** | R14.3 | `Soc. Sec. Admin., Program Operations Manual System (POMS) § DI 25025.001` | section | ssa.gov |

### 1.10 Federal legislative materials

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **Bill — House** | R13.2 | `H.R. 3590, 111th Cong. § 1101 (2009)` | bill_number, congress, section, year | congress.gov |
| **Bill — Senate** | R13.2 | `S. 1083, 107th Cong. § 2(b) (2001)` | bill_number, congress, section, year | congress.gov |
| **House Joint Resolution** | R13.2 | `H.R.J. Res. 114, 107th Cong. (2002)` | resolution_number, congress, year | congress.gov |
| **Senate Joint Resolution** | R13.2 | `S.J. Res. 23, 117th Cong. (2021)` | resolution_number, congress, year | congress.gov |
| **House Concurrent Resolution** | R13.2 | `H. Con. Res. 50, 117th Cong. (2021)` | resolution_number, congress, year | congress.gov |
| **Senate Concurrent Resolution** | R13.2 | `S. Con. Res. 12, 117th Cong. (2021)` | resolution_number, congress, year | congress.gov |
| **House Simple Resolution** | R13.2 | `H. Res. 100, 118th Cong. (2023)` | resolution_number, congress, year | congress.gov |
| **Senate Simple Resolution** | R13.2 | `S. Res. 50, 118th Cong. (2023)` | resolution_number, congress, year | congress.gov |
| **House Report** | R13.4 | `H.R. Rep. No. 111-443, pt. 1, at 12 (2010)` | congress, report_number, part, pin_cite, year | congress.gov / govinfo |
| **Senate Report** | R13.4 | `S. Rep. No. 117-50, at 5 (2021)` | congress, report_number, pin_cite, year | congress.gov / govinfo |
| **Conference Report** | R13.4 | `H.R. Rep. No. 111-517, at 4 (2010) (Conf. Rep.)` | congress, report_number, pin_cite, year, type (`conference`) | congress.gov |
| **Committee Hearing** | R13.5 | `Oversight of the FTC: Hearing Before the Subcomm. on Consumer Prot. of the S. Comm. on Com., Sci., & Transp., 117th Cong. 12 (2021) (statement of Lina Khan, Chair, FTC)` | hearing_title, committee, congress, pin_cite, year, witness, witness_role | congress.gov |
| **Committee Print** | R13.7 | `Staff of S. Comm. on the Judiciary, 117th Cong., Print on Antitrust 5 (Comm. Print 2022)` | committee, congress, title, pin_cite, year | congress.gov |
| **Congressional Record (bound)** | R13.6 | `165 Cong. Rec. 1234 (2019)` | volume, page, year | congress.gov |
| **Congressional Record (daily)** | R13.6 | `165 Cong. Rec. H1234 (daily ed. Mar. 14, 2019) (statement of Rep. Doe)` | volume, chamber_page (`H`/`S`/`E`/`D`), exact_date, speaker | congress.gov |
| **Congressional Globe / Annals (historical)** | R13.6 | `Cong. Globe, 39th Cong., 1st Sess. 2459 (1866)` | series_name, congress, session, page, year | govinfo (LLSALV) |
| **Public Papers of the Presidents** | R14.7 | `Pub. Papers 2008, vol. II, at 1234 (Sept. 1, 2008)` | year, volume, page, exact_date | govinfo |

### 1.11 Court documents (Bluebook B17 / R7)

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **Pleading — own case** | B17 | `Compl. ¶ 12; Pl.'s Mot. Summ. J. 5, ECF No. 47` | doc_type (`complaint`/`answer`/`motion`/`opposition`/`reply`), pin_cite, ecf_number | n/a (in-document) |
| **Pleading — cross-case** | R7 | `Compl. ¶ 12, Doe v. Roe, No. 22-cv-1234 (S.D.N.Y. Mar. 1, 2022), ECF No. 1` | doc_type, parties, docket_number, court, exact_date, ecf_number | PACER |
| **Trial transcript** | R7 | `Trial Tr. 142:5–10, May 1, 2023` | page_lines (`142:5-10`), exact_date | n/a |
| **Hearing transcript** | R7 | `Hr'g Tr. 50:5–10, June 1, 2023 (oral arg.)` | hearing_type, page_lines, exact_date | n/a |
| **Deposition transcript** | R7 | `Doe Dep. 45:12–46:3, Mar. 1, 2023` | deponent, page_lines, exact_date | n/a |
| **Affidavit / declaration** | R7 | `Smith Decl. ¶ 5, Mar. 1, 2023` | declarant, paragraph_pin, exact_date | n/a |
| **Trial exhibit** | R7 | `Pl.'s Trial Ex. 12, May 1, 2023` | party (`Pl.`/`Def.`), exhibit_number, exact_date | n/a |

### 1.12 Citation modifiers + short forms

| Family | Bluebook | Canonical example | Structured fields | Notes |
|---|---|---|---|---|
| **Bluebook signal** | R1.2 | `See`, `See, e.g.`, `See also`, `Cf.`, `But see`, `But cf.`, `Contra`, `Accord`, `Compare … with …`, `See generally`, `E.g.` | signal (Literal), embedded_in_compare (bool) | apply to following Citation |
| **Pin cite (page)** | R3.2 | `347 U.S. 483, 491` | pin_cite (str — page or page-range) | post-page suffix |
| **Pin cite (multi-page range)** | R3.2 | `347 U.S. 483, 491-92` | pin_cite (range str) | |
| **Pin cite (paragraph / section)** | R3.3 | `347 U.S. 483 ¶ 12` / `§ 4.5` | pin_cite_unit (`page`/`paragraph`/`section`/`note`/`line`) | |
| **Pin cite (footnote)** | R3.3 | `347 U.S. 483, 491 n.5` | pin_cite, pin_footnote (int) | |
| **Pin cite (multiple)** | R3.2 | `347 U.S. 483, 491, 495, 510` | pin_cite (list of pages) | |
| **Star pagination (Westlaw / LEXIS)** | R10.8.1 | `at *3` | star_page (int) | |
| **Explanatory parenthetical** | R1.5 | `(holding that property rights exist)` | parenthetical (str), parenthetical_kind (`holding`/`finding`/`reasoning`/`describing`/`other`) | |
| **Quoting parenthetical** | R1.5 | `(quoting Sweatt, 339 U.S. at 634)` | parenthetical_kind=`quoting`, inner_citations (list) | recursive parse |
| **Citing-within parenthetical** | R1.5 | `(citing Sweatt, 339 U.S. at 634)` | parenthetical_kind=`citing`, inner_citations (list) | recursive parse |
| **Weight-of-authority parenthetical** | R10.6.1 | `(en banc)` / `(per curiam)` / `(plurality)` / `(mem.)` | weight (Literal) | applies to CaseCitation |
| **Judge / opinion-type parenthetical** | R10.6.1 | `(Sotomayor, J., dissenting)` | judge, opinion_role | applies to CaseCitation |
| **Hereinafter declaration** | R4.2(b) | `(hereinafter "Restatement")` | hereinafter_label (str) | binds to following short forms |
| **Short form — `Id.`** | R4.1 | `Id.` | back_ref (int) | bind to immediately preceding |
| **Short form — `Id. at NN`** | R4.1 | `Id. at 504` | back_ref (int), pin_cite | |
| **Short form — `Id.` cross-source** | R4.1 | `Id.` | back_ref (int), source_kind | |
| **Short form — case party + at** | R10.9 | `Brown, 347 U.S. at 495` | back_ref (int), case_name_short, pin_cite | |
| **Short form — `Supra`** | R4.2 | `Smith, supra note 12, at 45` | back_ref (int), pin_cite | bind to earlier non-case full cite |
| **Short form — `Supra` (no note)** | R4.2 | `Brown, supra, at 495` | back_ref (int), pin_cite | |
| **Reference citation** | R10.9 | `Roe at 240` | back_ref (int), pin_cite | bind by party name |
| **String cite** | R1.4 | `Brown, 347 U.S. at 495; Bolling, 347 U.S. at 500; Sweatt, 339 U.S. at 634` | (multiple Citation objects sharing a leading signal) | grouping |

### 1.13 Secondary authorities (treatises, restatements, periodicals)

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **Restatement** | R15.8 | `Restatement (Second) of Torts § 402A (Am. L. Inst. 1965)` | series (`First`/`Second`/`Third`/`Fourth`), subject (`Torts`/`Contracts`/`Agency`/...), section, year | ALI (paywalled) |
| **Restatement comment** | R15.8 | `Restatement (Third) of Agency § 7.07 cmt. b (Am. L. Inst. 2006)` | series, subject, section, comment_letter, year | ALI |
| **Restatement illustration** | R15.8 | `Restatement (Second) of Torts § 402A illus. 5 (1965)` | series, subject, section, illustration_number, year | ALI |
| **Restatement reporter's note** | R15.8 | `Restatement (Second) of Torts § 402A reporter's note (1965)` | series, subject, section, year | ALI |
| **Uniform Act** | R15.8 | `U.C.C. § 2-207 (Am. L. Inst. & Unif. L. Comm'n 2022)` | act_short (`U.C.C.`/`U.P.C.`/`U.T.C.`), section, year | ULC |
| **Uniform Act comment** | R15.8 | `U.C.C. § 2-207 cmt. 4 (2022)` | act_short, section, comment_number, year | ULC |
| **ALI Principles** | R15.8 | `Principles of the Law of Software Contracts § 1.05 (Am. L. Inst. 2010)` | series_name, section, year | ALI |
| **Model Penal Code** | R15.8 | `Model Penal Code § 2.02 (Am. L. Inst. 1985)` | section, year | ALI |
| **Treatise (single-volume)** | R15 | `Charles Alan Wright & Arthur R. Miller, Federal Practice and Procedure § 1202 (3d ed. 2022)` | authors, title, section, edition, year | Westlaw / LEXIS (paywalled) |
| **Treatise (multi-volume)** | R15.2 | `5 Charles Alan Wright et al., Federal Practice and Procedure § 1202 (4th ed. 2023)` | volume, authors, title, section, edition, year | Westlaw |
| **Hornbook** | R15 | `Joseph M. Perillo, Calamari and Perillo on Contracts § 2.13 (7th ed. 2014)` | author, title, section, edition, year | Westlaw |
| **Black's Law Dictionary** | R15.8 | `Black's Law Dictionary 1234 (11th ed. 2019)` | page, edition, year | Westlaw |
| **Law review article** | R16 | `Cass R. Sunstein, Beyond the Republican Revival, 97 Yale L.J. 1539, 1550 (1988)` | author(s), title, volume, journal, page, pin_cite, year | HeinOnline / Google Scholar |
| **Law review — student note** | R16 | `Jane Doe, Note, Title, 100 Harv. L. Rev. 1 (2023)` | author, title, volume, journal, page, year, type (`note`/`comment`/`recent_case`) | HeinOnline |
| **Symposium** | R16.6 | `Symposium, Title, 95 Cornell L. Rev. 1 (2010)` | title, volume, journal, page, year | HeinOnline |
| **Newspaper (print)** | R16.6 | `Adam Liptak, Title, N.Y. Times, Mar. 14, 2023, at A1` | author, title, paper, exact_date, page | n/a |
| **Magazine** | R16.6 | `Jane Mayer, Title, New Yorker, Mar. 14, 2023, at 32` | author, title, magazine, exact_date, page | n/a |

### 1.14 Internet, electronic, unpublished

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **Internet — direct cite** | R18 | `Internet Citation Guide, Cornell L. Sch., https://www.law.cornell.edu/citation/ (last visited May 7, 2026)` | title, source_org, url, last_visited | n/a |
| **Internet — parallel to print** | R18.2 | `Adam Liptak, Title, N.Y. Times (Mar. 14, 2023), https://www.nytimes.com/...` | author, title, paper, exact_date, url | n/a |
| **Blog post** | R18.2 | `Jack Goldsmith, Title, Lawfare (Mar. 14, 2023, 9:00 AM), https://www.lawfareblog.com/...` | author, title, blog, exact_datetime, url | n/a |
| **Social media (X/Twitter)** | R18.2 | `@realDonaldTrump, X (Mar. 14, 2023, 9:00 AM), https://x.com/.../status/...` | handle, platform, exact_datetime, url, post_id | n/a |
| **YouTube / video** | R18.2 | `Title, YouTube (Mar. 14, 2023), https://www.youtube.com/watch?v=...` | title, platform, exact_date, url, video_id | n/a |
| **Wayback / Perma archive** | R18.3 | `Title, https://perma.cc/ABCD-1234` | title, archive_url, archive_id, original_url (optional) | perma.cc / archive.org |
| **SSRN preprint** | R17 | `Jane Doe, Title (Mar. 1, 2023), https://ssrn.com/abstract=1234567` | author, title, exact_date, ssrn_id | ssrn.com |
| **arXiv preprint** | R17 / R6.2 | `Jane Doe, Title, arXiv:2401.12345 (2024)` | author, title, arxiv_id, year | arxiv.org |
| **Working paper** | R17.2 | `John Doe, Title (Nat'l Bureau of Econ. Rsch., Working Paper No. 12345, 2023)` | author, title, series_org, paper_number, year | NBER / SSRN |
| **Unpublished manuscript** | R17 | `Jane Doe, Title (Mar. 1, 2023) (unpublished manuscript) (on file with author)` | author, title, exact_date, status | n/a |
| **DOI** | R6.2(b) | `https://doi.org/10.1234/abcd` | doi | doi.org |
| **PubMed** | R6.2(b) | `PMID: 12345678` | pmid | pubmed.ncbi.nlm.nih.gov |

### 1.15 Specialty / looseleaf services

| Family | Bluebook | Canonical example | Structured fields | Resolver |
|---|---|---|---|---|
| **CCH topical reporter** | R19 | `[2022 Transfer Binder] Fed. Sec. L. Rep. (CCH) ¶ 99,123 (S.D.N.Y. Mar. 1, 2022)` | binder, reporter (`Fed. Sec. L. Rep.`/`Stand. Fed. Tax Rep.`/...), publisher (`CCH`), paragraph, court, exact_date | CCH (paywalled) |
| **BNA topical reporter** | R19 | `14 OSHA Cases (BNA) 1234 (1990)` | volume, reporter, publisher (`BNA`), page, year | Bloomberg Law |
| **RIA topical reporter** | R19 | `2023 Tax Mgmt. (BNA) 456 (Apr. 2023)` | volume, reporter, publisher (`RIA`/`BNA`), page, exact_date | Bloomberg Law |
| **Looseleaf — federal securities** | R19 | `Fed. Sec. L. Rep. (CCH) ¶ 12,345` | reporter, publisher, paragraph | CCH |
| **Looseleaf — labor / employment** | R19 | `Lab. L. Rep. (CCH) ¶ 5,678` | reporter, publisher, paragraph | CCH |
| **State Bar Ethics Opinion** | R14.4 | `N.Y. State Bar Ass'n Comm. on Pro. Ethics, Op. 1234 (2023)` | state, opinion_number, year | per-state bar |

---

## 2. Financial citations

### 2.1 Securities filings (SEC)

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **Form 10-K** | `Acme Corp., Annual Report (Form 10-K) (Feb. 14, 2024)` | filer, form (`10-K`), filing_date, accession_number | sec.gov/EDGAR |
| **Form 10-Q** | `Acme Corp., Quarterly Report (Form 10-Q) (May 1, 2024)` | filer, form (`10-Q`), filing_date, period_of_report | sec.gov/EDGAR |
| **Form 8-K** | `Acme Corp., Current Report (Form 8-K) (Mar. 14, 2024) (Item 1.01, Material Definitive Agreement)` | filer, form (`8-K`), filing_date, item_number, item_title | sec.gov/EDGAR |
| **Form S-1 / S-3 / S-4** | `Acme Corp., Registration Statement (Form S-1) (Jan. 5, 2024)` | filer, form, filing_date | sec.gov/EDGAR |
| **Schedule 13D / 13G** | `Acme Holdings, Schedule 13D (Mar. 1, 2024)` | filer, schedule, filing_date, target_company | sec.gov/EDGAR |
| **Form 13F** | `BigFund LLC, Form 13F-HR (Feb. 14, 2024)` | filer, form (`13F-HR`/`13F-NT`), filing_date, period_of_report | sec.gov/EDGAR |
| **Schedule 14A (proxy statement)** | `Acme Corp., Proxy Statement (Schedule 14A) (Mar. 14, 2024)` | filer, schedule, filing_date | sec.gov/EDGAR |
| **Form ADV (investment adviser)** | `BigAdvisor LLC, Form ADV (Mar. 31, 2024)` | filer, form, filing_date, crd_number | sec.gov/IAPD |
| **Form D (Reg D offering)** | `Acme LLC, Form D (Apr. 1, 2024)` | filer, form, filing_date, offering_amount | sec.gov/EDGAR |

### 2.2 SEC rulemaking / interpretive

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **Securities Act Release (33-)** | `Securities Act Release No. 33-10777` | act (`33`), release_number, fed_reg_volume, fed_reg_page, exact_date, title | sec.gov |
| **Exchange Act Release (34-)** | `Exchange Act Release No. 34-94168, 87 Fed. Reg. 8019 (Feb. 11, 2022)` | act (`34`), release_number, fed_reg_volume, fed_reg_page, exact_date | sec.gov |
| **Investment Company Act Release (IC-)** | `Investment Company Act Release No. IC-34123 (Mar. 1, 2024)` | act (`IC`), release_number, exact_date | sec.gov |
| **Investment Advisers Act Release (IA-)** | `Investment Advisers Act Release No. IA-6500 (Apr. 5, 2024)` | act (`IA`), release_number, exact_date | sec.gov |
| **SEC No-Action Letter** | `Acme Corp., SEC No-Action Letter, 2022 WL 1234567 (Mar. 1, 2022)` | requestor, division (`Corp. Fin.`/`IM`/`TM`), exact_date, response_date, wl_id | sec.gov/divisions |
| **SEC Staff Accounting Bulletin (SAB)** | `SEC Staff Accounting Bulletin No. 121` | sab_number | sec.gov |
| **SEC Staff Legal Bulletin (SLB)** | `SEC Staff Legal Bulletin No. 14L (Nov. 3, 2021)` | slb_number, exact_date | sec.gov |
| **SEC Compliance & Disclosure Interpretation (C&DI)** | `C&DI Question 234.01 (Securities Act Sections)` | series, question, section_topic | sec.gov |
| **SEC Concept Release** | `Concept Release on Custody Rule, Securities Act Release No. 33-9658 (Feb. 26, 2015)` | title, release_number, exact_date | sec.gov |
| **SEC Interpretive Release** | `Interpretive Release Concerning Custody Rule, Securities Act Release No. 33-XXXX` | title, release_number | sec.gov |
| **SEC Comment Letter** | `Acme Corp. SEC Comment Letter (Apr. 1, 2024)` | filer, exact_date, accession_number | sec.gov/EDGAR |
| **EDGAR Filing accession number** | `Accession No. 0001234567-24-001234` | accession_number, filer, filing_date | sec.gov/EDGAR |

### 2.3 FINRA / SRO / exchange rules

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **FINRA Rule** | `FINRA Rule 2111` | rule_number | finra.org |
| **FINRA Regulatory Notice** | `FINRA Regulatory Notice 23-12 (Apr. 2023)` | notice_number, exact_date | finra.org |
| **FINRA Disciplinary Decision** | `Dep't of Enf't v. Doe, FINRA Disciplinary Proceeding No. 2020012345601 (NAC Apr. 1, 2023)` | proceeding_number, decision_authority (`OHO`/`NAC`), exact_date | finra.org |
| **MSRB Rule** | `MSRB Rule G-15` | rule_number | msrb.org |
| **NYSE Rule** | `NYSE Rule 123` | rule_number | nyse.com |
| **NYSE Information Memo** | `NYSE Information Memo 23-12 (Apr. 2023)` | memo_number, exact_date | nyse.com |
| **Nasdaq Rule** | `Nasdaq Rule 5605(d)` | rule_number, subdivisions | nasdaq.com |
| **Cboe Rule** | `Cboe Rule 4.1` | rule_number, exchange (`BZX`/`BYX`/`EDGA`/`EDGX`/`Options`) | cboe.com |
| **OCC By-Laws / Rules** | `OCC By-Laws § 1.1; OCC Rule 101` | section_or_rule | theocc.com |

### 2.4 Banking regulators

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **Federal Reserve Regulation (Reg A–Z)** | `12 C.F.R. § 226.5` (Reg Z, Truth in Lending) / `Regulation Z, 12 C.F.R. pt. 226` | reg_letter (`A`–`Z`/`AA`–`KK`), cfr_title, cfr_part, cfr_section | federalreserve.gov |
| **Federal Reserve SR Letter** | `SR 23-04 (Mar. 1, 2023)` | letter_number, exact_date | federalreserve.gov |
| **Federal Reserve CA Letter** | `CA 23-01 (Jan. 5, 2023)` | letter_number, exact_date | federalreserve.gov |
| **Federal Reserve Interpretive Letter** | `Bd. of Governors Interp. Ltr. (Mar. 1, 2023)` | exact_date, subject | federalreserve.gov |
| **FDIC Financial Institution Letter (FIL)** | `FIL-12-2023 (Mar. 1, 2023)` | fil_number, year, exact_date | fdic.gov |
| **FDIC Statement of Policy** | `FDIC Statement of Policy on Acme, 88 Fed. Reg. 1234 (Jan. 5, 2023)` | title, fed_reg_volume, fed_reg_page, exact_date | fdic.gov |
| **OCC Bulletin** | `OCC Bulletin 2023-10 (Mar. 1, 2023)` | bulletin_number, exact_date | occ.gov |
| **OCC Interpretive Letter** | `OCC Interp. Ltr. 1234 (Mar. 1, 2023)` | letter_number, exact_date | occ.gov |
| **OCC Conditional Approval** | `OCC Conditional Approval No. 1234 (Apr. 1, 2023)` | approval_number, exact_date | occ.gov |
| **CFPB Bulletin** | `CFPB Bulletin 2023-01 (Mar. 1, 2023)` | bulletin_number, exact_date | consumerfinance.gov |
| **CFPB Compliance Bulletin** | `CFPB Compliance Bulletin 2023-01 (Apr. 1, 2023)` | bulletin_number, exact_date | consumerfinance.gov |
| **CFPB Circular** | `CFPB Circular 2023-01 (May 1, 2023)` | circular_number, exact_date | consumerfinance.gov |
| **CFPB Advisory Opinion** | `CFPB Advisory Opinion, 88 Fed. Reg. 1234 (Jan. 5, 2023)` | title, fed_reg_volume, fed_reg_page, exact_date | consumerfinance.gov |
| **NCUA Letter to Credit Unions** | `NCUA Letter to Credit Unions 23-01 (Jan. 5, 2023)` | letter_number, exact_date | ncua.gov |
| **Basel framework** | `Basel III: Finalising post-crisis reforms (Dec. 2017)` | document_title, document_id, exact_date | bis.org |

### 2.5 Commodities / futures (CFTC)

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **CFTC Rule** | `17 C.F.R. § 1.3` | (cited as CFR — cross-references to legal taxonomy) | ecfr.gov |
| **CFTC Interpretive Letter** | `CFTC Interp. Ltr. 23-12 (Apr. 1, 2023)` | letter_number, exact_date, division | cftc.gov |
| **CFTC No-Action Letter** | `CFTC No-Action Letter 23-05 (Mar. 1, 2023)` | letter_number, exact_date, division (`DSIO`/`DCR`/`DMO`) | cftc.gov |
| **CFTC Advisory** | `CFTC Advisory 23-01 (Jan. 5, 2023)` | advisory_number, exact_date | cftc.gov |
| **CFTC Order** | `In re Acme Corp., CFTC Docket No. 23-01 (Jan. 5, 2023)` | docket_number, exact_date, parties | cftc.gov |

### 2.6 Insurance

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **NAIC Model Act** | `NAIC Risk-Based Capital (RBC) for Insurers Model Act (2022)` | model_name, year | naic.org |
| **NAIC Bulletin** | `NAIC Bulletin 2023-01 (Mar. 1, 2023)` | bulletin_number, exact_date | naic.org |
| **State Insurance Code** | `Cal. Ins. Code § 790.03` | (cross-reference to state code in legal taxonomy) | per-state |
| **State insurance bulletin** | `N.Y. Ins. Dept. Office of General Counsel Op. 23-01 (Jan. 5, 2023)` | state, opinion_number, exact_date | per-state |

### 2.7 International financial bodies

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **IOSCO Standard / Report** | `IOSCO Final Report, Title (FR XX-2023, Apr. 2023)` | document_id, title, exact_date | iosco.org |
| **FATF Recommendation** | `FATF Recommendation 10 (2012)` | recommendation_number, year | fatf-gafi.org |
| **BCBS Standard** | `BCBS d544, Final Standard on Operational Resilience (Mar. 2021)` | document_id, title, exact_date | bis.org |
| **Financial Stability Board** | `FSB, Title (Apr. 1, 2023)` | title, exact_date | fsb.org |

---

## 3. Accounting citations

### 3.1 US GAAP (FASB)

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **ASC (Accounting Standards Codification)** | `FASB ASC 805-10-25-1` | topic (805), subtopic (10), section (25), paragraph (1) | fasb.org (subscription) |
| **ASC — section-level** | `ASC 805-10-25` | topic, subtopic, section | fasb.org |
| **ASC — topic-level** | `ASC 606` | topic | fasb.org |
| **ASU (Accounting Standards Update)** | `ASU 2023-09, Improvements to Income Tax Disclosures (Dec. 2023)` | year, sequence_number, title, exact_date | fasb.org |
| **FASB Statement (pre-codification)** | `FAS 142, Goodwill and Other Intangible Assets (June 2001)` | statement_number, title, exact_date | fasb.org (historical) |
| **FASB Interpretation (FIN, pre-codification)** | `FIN 48, Accounting for Uncertainty in Income Taxes (June 2006)` | interpretation_number, title, exact_date | fasb.org (historical) |
| **FASB Technical Bulletin** | `FASB Technical Bulletin 90-1 (Dec. 1990)` | year, sequence_number, title, exact_date | fasb.org |
| **FASB Implementation Guide** | `FASB Implementation Guide on ASC 606 (Apr. 2017)` | topic, exact_date | fasb.org |
| **EITF Issue (Emerging Issues Task Force)** | `EITF Issue 02-13, Deferred Income Tax Considerations (2002)` | year, sequence_number, title | fasb.org |
| **EITF Topic** | `EITF Topic D-110` | topic_id | fasb.org |
| **FASB Concepts Statement (CON)** | `FASB Statement of Financial Accounting Concepts No. 8 (Sept. 2010)` | concept_number, title, exact_date | fasb.org |
| **FASB Staff Position (FSP)** | `FSP FAS 142-3 (Apr. 2008)` | original_statement, sequence, exact_date | fasb.org (historical) |

### 3.2 PCAOB / AICPA / auditing

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **PCAOB Auditing Standard (AS)** | `PCAOB AS 2401, Consideration of Fraud in a Financial Statement Audit` | as_number, title | pcaobus.org |
| **PCAOB Staff Audit Practice Alert** | `PCAOB Staff Audit Practice Alert No. 12 (Sept. 2014)` | alert_number, exact_date | pcaobus.org |
| **PCAOB Release** | `PCAOB Release No. 2023-001 (Mar. 1, 2023)` | release_number, exact_date | pcaobus.org |
| **PCAOB Rule** | `PCAOB Rule 3502` | rule_number | pcaobus.org |
| **AICPA Statement on Auditing Standards (SAS)** | `AICPA SAS 145, Understanding the Entity (Oct. 2021)` | sas_number, title, exact_date | aicpa.org |
| **AICPA Statement on Standards for Attestation Engagements (SSAE)** | `AICPA SSAE 18 (Apr. 2016)` | ssae_number, exact_date | aicpa.org |
| **AICPA Statement on Standards for Accounting and Review Services (SSARS)** | `AICPA SSARS 25 (Feb. 2020)` | ssars_number, exact_date | aicpa.org |
| **AICPA Statement of Position (SOP)** | `AICPA SOP 03-1 (Dec. 2003)` | year, sequence, exact_date | aicpa.org |
| **AICPA Audit & Accounting Guide** | `AICPA Audit & Accounting Guide: Health Care Entities (2023)` | title, year | aicpa.org |
| **AICPA Code of Professional Conduct** | `AICPA Code of Pro. Conduct, ET § 1.295` | section, year | aicpa.org |
| **AICPA Practice Alert** | `AICPA Practice Alert 2023-01 (Mar. 1, 2023)` | alert_number, exact_date | aicpa.org |
| **AICPA Technical Question and Answer (TQA)** | `AICPA TQA 1300.10` | tqa_number | aicpa.org |
| **AICPA Issues Paper** | `AICPA Issues Paper, Title (Mar. 1, 2023)` | title, exact_date | aicpa.org |
| **PCC (Private Company Council)** | `PCC Issue 23-01 (Mar. 1, 2023)` | year, sequence, exact_date | fasb.org/pcc |

### 3.3 SEC accounting (cross-references to SEC + accounting)

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **Regulation S-X** | `17 C.F.R. § 210.X-XX` (referenced as `Reg. S-X`) | regulation (`S-X`), cfr_section, item | ecfr.gov |
| **Regulation S-K** | `17 C.F.R. § 229.XXX` (referenced as `Reg. S-K`) | regulation (`S-K`), cfr_section, item | ecfr.gov |
| **Regulation G (non-GAAP)** | `17 C.F.R. § 244.100` | regulation (`G`), cfr_section | ecfr.gov |
| **SEC Financial Reporting Manual** | `SEC Div. of Corp. Fin., Financial Reporting Manual § 1110.1 (2023)` | section, year | sec.gov |
| **SEC Industry Guides** | `SEC Industry Guide 3, Statistical Disclosure by Bank Holding Companies` | guide_number, title | sec.gov |
| **SEC Staff Accounting Bulletin (SAB)** | `SAB No. 121 (Mar. 31, 2022)` (already in §2.2) | sab_number, exact_date | sec.gov |
| **SEC Form & Instruction** | `Item 303 of Reg. S-K, MD&A Disclosure (Form 10-K)` | item_or_form, regulation, topic | sec.gov |

### 3.4 IFRS / international accounting

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **IFRS Standard** | `IFRS 15, Revenue from Contracts with Customers (May 2014)` | standard_number, title, issue_date | ifrs.org |
| **IFRS Standard — paragraph** | `IFRS 15.31` (paragraph 31) | standard_number, paragraph | ifrs.org |
| **IAS (legacy IFRS)** | `IAS 36, Impairment of Assets (Mar. 2004)` | ias_number, title, issue_date | ifrs.org |
| **IAS — paragraph** | `IAS 36.12` | ias_number, paragraph | ifrs.org |
| **IFRIC Interpretation** | `IFRIC 23, Uncertainty over Income Tax Treatments (June 2017)` | ifric_number, title, issue_date | ifrs.org |
| **SIC Interpretation (legacy)** | `SIC-7, Introduction of the Euro (May 1998)` | sic_number, title, issue_date | ifrs.org |
| **IFRS Practice Statement** | `IFRS Practice Statement 1, Management Commentary (Dec. 2010)` | statement_number, title, issue_date | ifrs.org |
| **IFRS Conceptual Framework** | `IFRS Conceptual Framework for Financial Reporting (Mar. 2018), ¶ 4.5` | paragraph, issue_date | ifrs.org |
| **ISA (International Standards on Auditing)** | `ISA 315 (Revised 2019), Identifying and Assessing Risks (Dec. 2019)` | isa_number, revision, title, exact_date | iaasb.org |
| **ISAE (International Standard on Assurance Engagements)** | `ISAE 3000 (Revised) (Dec. 2013)` | isae_number, revision, exact_date | iaasb.org |
| **ISRE (International Standard on Review Engagements)** | `ISRE 2400 (Revised) (Sept. 2012)` | isre_number, revision, exact_date | iaasb.org |
| **IESBA Code** | `IESBA Code of Ethics for Pro. Accountants § 290` | section, year | iesbaecode.org |

### 3.5 Government / non-profit accounting

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **GASB Statement** | `GASB Statement No. 87, Leases (June 2017)` | statement_number, title, exact_date | gasb.org |
| **GASB Statement — paragraph** | `GASB Statement No. 87, ¶ 12` | statement_number, paragraph | gasb.org |
| **GASB Interpretation** | `GASB Interpretation No. 6 (Mar. 2000)` | interpretation_number, exact_date | gasb.org |
| **GASB Implementation Guide** | `GASB Implementation Guide 2019-1 (May 2019)` | year, sequence, exact_date | gasb.org |
| **GASB Concepts Statement** | `GASB Concepts Statement No. 1 (May 1987)` | concept_number, exact_date | gasb.org |
| **GASB Technical Bulletin** | `GASB Technical Bulletin 2008-1 (Dec. 2008)` | year, sequence, exact_date | gasb.org |
| **FASAB Standard (federal)** | `FASAB SFFAS 56, Classified Activities (Oct. 2018)` | sffas_number, title, exact_date | fasab.gov |
| **FASAB Concepts Statement** | `FASAB Concepts Statement 1 (Sept. 1993)` | concept_number, exact_date | fasab.gov |
| **OMB Circular** | `OMB Circular A-133, Audits of States, Local Governments, and Non-Profit Organizations (Rev. 2007)` | circular_id (`A-133`), title, revision | whitehouse.gov/omb |
| **Yellow Book (GAO Government Auditing Standards)** | `GAO, Government Auditing Standards (2018 Rev.)` | revision_year, title | gao.gov |

### 3.6 Tax accounting (cross-references to legal IRS taxonomy)

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **ASC 740 (Income Taxes)** | `FASB ASC 740-10-25-6` (uncertain tax positions) | (cross-reference to §3.1) | fasb.org |
| **Internal Revenue Code** | `I.R.C. § 162` | (cross-reference to §1.3) | uscode.house.gov |
| **Treasury Regulation** | `Treas. Reg. § 1.162-1` | (cross-reference to §1.6) | ecfr.gov |
| **Revenue Ruling** | `Rev. Rul. 2019-11` | (cross-reference to §1.8) | irs.gov |
| **APB Opinion (legacy, pre-FASB)** | `APB Op. 18, Equity Method (Mar. 1971)` | opinion_number, title, exact_date | fasb.org (historical) |
| **APB Statement (legacy)** | `APB Statement No. 4 (Oct. 1970)` | statement_number, exact_date | fasb.org (historical) |

### 3.7 Industry-specific accounting

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **NAIC SAP (Statutory Accounting Principles)** | `NAIC SSAP No. 5R, Liabilities, Contingencies and Impairments` | ssap_number, title, revision | naic.org |
| **OCC Bank Accounting Advisory Series (BAAS)** | `OCC, Bank Accounting Advisory Series (Aug. 2023)` | edition_date | occ.gov |
| **Federal Reserve Call Report (FFIEC 031/041/051)** | `FFIEC 031, Schedule RC-N, item 5` | form_number, schedule, item, period | ffiec.gov |
| **NCUA Call Report (5300)** | `NCUA Form 5300, Schedule A` | form_number, schedule, period | ncua.gov |
| **HUD Audit Guide** | `HUD Audit Guide for Annual Audits, Ch. 2` | chapter, edition_year | hud.gov |
| **DCAA Contract Audit Manual (CAM)** | `DCAA CAM § 2-301` | section | dcaa.mil |

### 3.8 Sustainability / ESG reporting

| Family | Canonical example | Structured fields | Resolver |
|---|---|---|---|
| **GRI Standard** | `GRI 305: Emissions 2016` | standard_number, title, version_year | globalreporting.org |
| **SASB Standard** | `SASB FB-FR-110a.1 (Food & Beverage / Restaurants — Fleet Fuel)` | sector, industry, topic, code, version | sasb.org |
| **TCFD Recommendation** | `TCFD Recommended Disclosures (June 2017)` | document_title, exact_date | fsb-tcfd.org |
| **ISSB IFRS Sustainability Standard** | `IFRS S1, General Requirements for Disclosure of Sustainability-related Financial Information (June 2023)` | standard_number (`S1`/`S2`/...), title, exact_date | ifrs.org/issb |
| **ESRS (EU CSRD)** | `ESRS 2, General Disclosures` | standard_number, title | efrag.org |
| **CDP Questionnaire** | `CDP Climate Change Questionnaire 2023, C2.1` | questionnaire, year, item_code | cdp.net |

---

## 4. Tier-4 / out-of-scope (deferred)

Listed for completeness so the boundary is explicit; not targeted in
v0.2 unless flagged by the user.

| Family | Canonical example | Reason deferred |
|---|---|---|
| Foreign cases (UK / Canada / EU neutral citations) | `Donoghue v Stevenson [1932] AC 562 (HL)`, `R. v. Oakes, [1986] 1 S.C.R. 103 (Can.)`, `Case C-362/14, Schrems v. Data Prot. Comm'r, ECLI:EU:C:2015:650` | Per-jurisdiction format families; under 0.3% of US-practitioner brief tokens |
| Foreign statutes | `Human Rights Act 1998, c. 42, § 3 (UK)` | Same |
| ICJ / WTO / international tribunals | `Nicar. v. U.S., 1986 I.C.J. 14 (June 27)`, `U.S. — Steel Safeguards, WT/DS248/AB/R (Nov. 10, 2003)` | Same |
| UN documents (G.A. Res., S.C. Res.) | `G.A. Res. 217 (III) A, Universal Declaration of Human Rights (Dec. 10, 1948)` | Same |
| Book reviews | `John Doe, Book Note, Title, 100 Harv. L. Rev. 200 (2023) (reviewing Author, Title (2022))` | Rare; nested-citation form |
| Bluebook formatting-only rules (Rule 5 block quotes, Rule 8 capitalization, Bluepages B B small caps) | n/a | Formatting, not citation tokens |

---

## 5. Cross-reference + structural conventions

Common patterns that apply across multiple citation families above:

- **Compound cites** (multiple parallel reporters in one citation):
  emit one `Citation` with a `parallel_cites: list[Citation]` field.
- **Cross-source short forms** (`Id.` referring to a treatise rather
  than a case): `back_ref` resolves to whatever the immediately
  preceding citation was — case, statute, treatise, etc.
- **String cites** (`See A; B; C`): each cite is a separate `Citation`;
  a `string_cite_group: int | None` field links them and the leading
  `signal` propagates to all members of the group.
- **Citation in quoted text**: when a quotation reproduces another
  citation, the inner cite is parsed into `inner_citations` on the
  parenthetical (`(quoting Sweatt, 339 U.S. at 634)`) without
  duplicating it as a top-level cite.
- **Multi-section ranges** (`§§ 1-5`): emit per-section citations or
  a single citation with `section_range: (start, end)` — TBD per
  family; default to per-section emission for indexing.
- **Hereinafter chains** (`(hereinafter "Restatement")`): the
  declaration emits a `HereinafterCitation` with `label` + the
  resolved antecedent; subsequent uses of the label resolve via
  `back_ref` to the original full cite.
- **Pin-cite kinds**: `page` (default), `paragraph` (`¶`), `section`
  (`§`), `note` (`n.`), `line` (`l.`), `star` (`*N` for Westlaw /
  LEXIS pagination).

---

## 6. Open questions

These are decisions deferred to implementation time, not gaps in the
taxonomy:

1. Should `Citation.kind` be a flat string discriminator (current
   design) or a nested family / subfamily tuple? Flat keeps the
   union manageable; nested would let `kind="agency.nlrb"`,
   `kind="agency.bia"` share parsing infra.
2. `parallel_cites` on cases: emit as nested `CaseCitation` objects
   or as flat `(reporter, volume, page)` tuples?
3. Do we want a separate `JurisdictionCitation` mixin to thread
   `(country, state, federal_district, federal_circuit)` consistently
   across families, or just per-family `state` / `circuit` /
   `district` fields?
4. Resolver auth credentials: `irs.gov` / `sec.gov` / `congress.gov`
   are unauthenticated; HeinOnline / Westlaw / LEXIS / CCH / BNA /
   Bloomberg Law / Aispace are paywalled. The `[heavy]` extra should
   support an `auth=` kwarg taking a per-resolver `SecretStr` token,
   sourced from `KaosCitationsSettings`.
5. International framework standards (Basel, IOSCO, FATF) — should
   they be a separate `[international_finance]` extra rather than
   the default `[heavy]`?
