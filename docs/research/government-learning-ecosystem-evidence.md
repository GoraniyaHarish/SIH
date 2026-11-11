# Government learning ecosystem evidence register

**Review date:** 11 November 2026  
**Purpose:** Establish what can be evidenced from public MoSPI/NSSTA/iGOT pages before PRAMANA imports or recommends external learning programmes.

This register is a research aid, not an integration specification. Public pages establish that a programme or learning resource is listed; they do not establish API access, eligibility for a particular employee, seat availability, enrolment permission, completion synchronization, or MoSPI endorsement of PRAMANA's competency mapping.

## 1. NSSTA public evidence

### 1.1 TPAC records

The official NSSTA Documents page has a TPAC section listing:

| Record | Reference | Issue date | Evidence interpretation |
|---|---|---:|---|
| Minutes of the Meeting of TPAC FY 2025-26 | L-14011/02/TPAC/2022-23/NSSTA | 07-04-2025 | Officially listed meeting record; not a course enrolment API or course schedule |
| Minutes of the Meeting of TPAC FY 2024-25 | TPAC/2024-25/NSSTA | 07-03-2024 | Officially listed meeting record |
| Minutes of the Meeting of TPAC FY 2023-24 | L-14011/02/TPAC/2022-23/NSSTA | 05-04-2023 | Officially listed meeting record |
| Minutes of the Meeting of TPAC FY 2022-23 | Y-11011/11/IES/2020-21/NSSTA | 11-03-2022 | Officially listed meeting record |
| Minutes of the Meeting of TPAC FY 2021-22 | Y-11011/11/IES/2020-21/NSSTA | 04-03-2021 | Officially listed meeting record |
| Minutes of the Meeting of TPAC FY 2020-21 | L-14011/1/2012-13-TPAC/Trg | 20-02-2020 | Officially listed meeting record |

Source: https://nssta.gov.in/document

The same page's Training Calendar section displayed “No Record Found” when retrieved. Do not infer that no training takes place; only state that the public page did not expose a current calendar record in this retrieval.

### 1.2 Publicly described NSSTA training categories

The official NSSTA Trainings/Offerings page describes multiple categories, including ISS probationary training, ISS refresher training, JTS induction, SSS induction, SSS refresher, State/UT training, international training, university awareness programmes, and demand-based training.

The page states that ISS probationary training follows an approved training calendar and may be delivered at NSSTA or partner institutes. It describes SSS refresher programmes as covering domain-specific, behavioural and functional competency requirements. State/UT ToT topics listed include:
- Index Numbers and Price Statistics
- Social Statistics
- National Accounts Statistics
- Sampling Methods and Techniques Used in Large-Scale Sample Surveys
- Demography and Population Studies

Examples shown in the public page's participant/programme tables include:
- SSS Refresher Training, 2026: “Remote sensing & GIS Technology and its Applications for Disaster Management”.
- State/UT training, 2024: “Sampling Methods and Techniques Used in Large Scale Surveys”.

Source: https://nssta.gov.in/offerings

**Data caution:** The offerings page is a public activity/participant listing. It does not, by itself, establish a current upcoming course, open registration, duration, prerequisites, seat availability, or an authoritative competency-to-course mapping. Do not seed fabricated dates, durations, costs, eligibility, or enrolment links from these records.

### 1.3 NSSTA mandate context

NSSTA describes itself as a Central Training Institute under MoSPI and states its mandate includes training statistical and non-statistical manpower in theoretical/applied statistics, data collection, collation, analysis, dissemination, and monitoring/evaluation. Its training covers domain-specific, behavioural and functional requirements.

Sources:
- https://nssta.gov.in/aboutus
- https://nssta.gov.in/history

## 2. Public iGOT Karmayogi catalogue evidence

The public iGOT Karmayogi portal exposes course/resource pages with title, provider, description, duration, learning outcomes and tags for some resources. Examples retrieved during this review include:

| Resource | Provider | Public metadata observed | URL |
|---|---|---|---|
| Responsible Data Management | DataDotOrg | Listed in a public course-recommendation PDF; duration shown as 1h 58m | https://portal.igotkarmayogi.gov.in/app/toc/do_1140994741049999361127 |
| AI: Expert's Insights | Invest India | Public resource page; AI and data analysis/visualization themes; 7m 23s | https://portal.igotkarmayogi.gov.in/viewer/video/do_113923178878197760193 |
| Disaster Management / Civil Defence resource | National Disaster Response Force | Public ToC page; 1h 16m, 12 modules and final test; tags include disaster management | https://portal.igotkarmayogi.gov.in/public/toc/do_1143166853070028801812/overview |

Additional source:
https://portal.igotkarmayogi.gov.in/content-store/orgStore/0133809553768366080/1729231972061_Course%20Recommendations_Karmayogi%20Saptah.pdf

These are evidence that a public catalogue exists. They are not evidence of MoSPI-specific course endorsement or that each resource closes a particular statistical competency gap. The competency mapping must be reviewed by a qualified domain owner and stored as provisional until approved.

## 3. Integration boundary and current status

| Capability | Public evidence found | What remains required | PRAMANA status |
|---|---|---|---|
| Browse public iGOT resource links | Public course/resource pages are accessible | Stable catalogue metadata, allowed use, refresh strategy and mapping governance | Research evidence only; not an authenticated API integration |
| iGOT enrolment | Public pages show sign-in/register workflows | Authorized partner/API specification, credentials, scopes, consent and test environment | Not configured / not implemented as live sync |
| iGOT completion/progress sync | Public resource pages describe tracked learning | Authorized event/API contract, identity matching, reconciliation and audit requirements | Not configured / not implemented |
| NSSTA TPAC records | Official TPAC minutes are publicly listed | Review of the actual minutes and approved training plan, structured course metadata and owner approval | Public evidence register only |
| NSSTA programme discovery | Public offerings page describes programme categories and historical examples | Current schedule, eligibility, availability, application process and stable source IDs | Not an enrolment integration |
| Competency-to-course mapping | Some public resource learning outcomes and tags are visible | Domain expert review and MoSPI/NSSTA approval | Provisional mapping only |

## 4. Safe implementation guidance

1. Preserve each source URL, retrieval date, title, provider, source publication date (when actually shown), and evidence status.
2. Use “official” only to describe the provenance of the source record itself; do not imply that a PRAMANA competency mapping or recommendation has official approval.
3. Use “provisional” for competency mappings pending subject-matter review.
4. Do not convert a past participant listing into an upcoming course offering.
5. Do not fabricate duration, cost, eligibility, schedule, seat availability, enrolment status, or completion.
6. External links should be clearly labelled as opening the provider's site; PRAMANA must not imply that the learner has been enrolled.
7. Before a live iGOT connector is built, obtain written authorization and the supported API specification from the platform owner. Do not scrape authenticated user data or reverse-engineer private endpoints.
8. Keep the local competency-gap and recommendation workflow usable when external platforms are unavailable.

## 5. Recommendation for the prototype

For the current SIH demonstration, use:
- PRAMANA's existing local demonstration course catalogue, explicitly labelled as demonstration data.
- A separately labelled “Public learning resources” list sourced from public iGOT/NSSTA pages, with source dates and external links.
- A provisional competency match with an explanation of the matching tags/learning outcomes and a visible “mapping requires domain review” badge.
- No simulated enrolment, completion callback, live synchronization, or government approval claim.

This creates a truthful and demonstrable discovery workflow while preserving a clear path to authorized integrations.
