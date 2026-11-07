"""Provisional competency framework content for the Official Statistical System.

EVIDENCE STATUS: every item here is PROVISIONAL unless a source_ref points at a specific official
document. This dictionary was authored for this prototype, informed by:
  - MoSPI *Compendium of Roles and Responsibilities of Divisions and Units of MoSPI* (25 Mar 2025)
  - MoSPI *Reference Manual for ISS Probationary Officers* (NSSTA/NSC, 2018)
  - DoPT/ISTM *Framework of Roles, Activities and Competencies (FRAC)* concept
It is NOT an officially gazetted MoSPI competency framework and must be reviewed by domain experts
before operational use. The application surfaces this status in the API and UI.
"""
from __future__ import annotations

FRAMEWORK_LABEL = "OSS-2026.1"
FRAMEWORK_NOTES = (
    "Prototype competency framework for India's Official Statistical System. Authored from public "
    "MoSPI/NSSTA role descriptions and the Mission Karmayogi FRAC concept. Provisional: requires "
    "expert validation before operational use."
)

# ---------------------------------------------------------------- proficiency scale
LEVELS = [
    {
        "level": 1,
        "label": "Aware",
        "summary": "Recognises terminology and understands why the task matters.",
        "criteria": [
            "Can name the key concepts and where they fit in the statistical production process",
            "Requires step-by-step guidance to perform the task",
        ],
    },
    {
        "level": 2,
        "label": "Assisted",
        "summary": "Performs routine tasks with supervision and a checklist.",
        "criteria": [
            "Completes standard tasks with review by a senior officer",
            "Identifies obvious errors in own output when pointed out",
        ],
    },
    {
        "level": 3,
        "label": "Independent",
        "summary": "Performs the full task unsupervised in standard situations.",
        "criteria": [
            "Produces correct output independently on routine cases",
            "Explains methodological choices to a colleague",
        ],
    },
    {
        "level": 4,
        "label": "Proficient",
        "summary": "Handles non-standard cases and justifies methodological decisions.",
        "criteria": [
            "Adapts methods to non-standard situations and documents the rationale",
            "Reviews and corrects the work of others",
        ],
    },
    {
        "level": 5,
        "label": "Expert",
        "summary": "Sets method, mentors others and defends the approach to external bodies.",
        "criteria": [
            "Designs or revises methodology and defends it before review committees",
            "Builds organisational capability through training and standards",
        ],
    },
]

# ---------------------------------------------------------------- domains & competencies
DOMAINS = [
    {
        "code": "STAT",
        "name": "Official Statistics Foundations",
        "kind": "domain",
        "description": "The statistical production process, national statistical system institutions and legal basis.",
        "source_ref": "MoSPI Compendium of Roles and Responsibilities (2025); MoSPI National Policy on Official Statistics (draft 2018)",
        "competencies": [
            ("STAT.01", "Statistical production process",
             "Understands the end-to-end sequence from user needs to dissemination and revision.",
             "Errors anywhere in the production chain propagate into published statistics.",
             ["Describes the stages of the official statistics value chain", "Locates the quality control gates in a survey cycle"]),
            ("STAT.02", "National Statistical System institutions",
             "Knows the mandates of MoSPI, NSO, NSC, NSSTA and state statistical bodies.",
             "Work is commissioned, cleared and disseminated through specific institutional channels.",
             ["Identifies which body approves a new statistical series", "Routes a methodological query to the correct institution"]),
            ("STAT.03", "Statistical legislation and confidentiality",
             "Applies the legal obligations around collection, confidentiality and release of statistical data.",
             "Improper handling of unit-level data is a legal and ethical breach.",
             ["Applies confidentiality rules to a micro-data request", "Identifies when a release requires clearance"]),
        ],
    },
    {
        "code": "SAMP",
        "name": "Survey Design and Sampling",
        "kind": "technical",
        "description": "Sample design, instrument design and field operations for national sample surveys.",
        "source_ref": "MoSPI Reference Manual for ISS Probationary Officers (NSSTA/NSC 2018)",
        "competencies": [
            ("SAMP.01", "Sampling design",
             "Chooses and documents an appropriate sample design including stratification and stage selection.",
             "Sample design determines the validity and precision of every estimate produced.",
             ["Explains stratification choice for a household survey", "Computes a first-stage selection probability"]),
            ("SAMP.02", "Sample size and allocation",
             "Derives sample size from precision requirements and allocates it across strata.",
             "Under-sized samples cannot support the intended disaggregation.",
             ["Computes sample size for a given margin of error", "Allocates sample across strata using a stated rule"]),
            ("SAMP.03", "Survey instrument design",
             "Designs questionnaire schedules with valid question wording, skip logic and code lists.",
             "Instrument defects are the largest source of non-sampling error.",
             ["Detects leading or double-barrelled questions", "Specifies skip logic and validation rules for a schedule"]),
            ("SAMP.04", "Field operations and supervision",
             "Plans field work, supervises investigators and controls field-level quality.",
             "Field execution determines response rates and data reliability.",
             ["Prepares a field work plan with replacement rules", "Applies a field scrutiny checklist to returned schedules"]),
        ],
    },
    {
        "code": "EST",
        "name": "Estimation and Statistical Inference",
        "kind": "technical",
        "description": "Estimation, weighting, variance estimation and treatment of non-response.",
        "source_ref": "Standard survey methodology; MoSPI survey reports describe estimation procedures",
        "competencies": [
            ("EST.01", "Estimation under complex designs",
             "Applies design-consistent estimators with appropriate weights.",
             "Unweighted tabulation of a complex sample yields biased estimates.",
             ["Computes a weighted estimate from unit-level data", "Explains why design weights matter"]),
            ("EST.02", "Variance estimation and precision reporting",
             "Produces standard errors using design-appropriate methods and reports them alongside estimates.",
             "Point estimates without precision measures cannot be interpreted responsibly.",
             ["Obtains a standard error using a replication or linearisation method", "Interprets a confidence interval for a policy audience"]),
            ("EST.03", "Non-response and imputation",
             "Diagnoses non-response and applies documented imputation or adjustment.",
             "Unadjusted non-response silently biases published totals.",
             ["Measures unit and item non-response", "Documents an imputation method and its assumptions"]),
        ],
    },
    {
        "code": "NA",
        "name": "National Accounts",
        "kind": "domain",
        "description": "Compilation of national accounts aggregates and their conceptual basis.",
        "source_ref": "MoSPI/NSO National Accounts Statistics publications",
        "competencies": [
            ("NA.01", "National accounts concepts and identities",
             "Applies the production, income and expenditure identities and the SNA institutional sector framework.",
             "GDP compilation and reconciliation depend on these identities.",
             ["Checks a value-added calculation for internal consistency", "Classifies a transaction by institutional sector"]),
            ("NA.02", "Compilation methods and base revision",
             "Applies compilation methods for a sector and understands base-year revision practice.",
             "Series revisions must be methodologically defensible and documented.",
             ["Describes how an activity estimate is compiled", "Explains the effect of a base-year revision"]),
        ],
    },
    {
        "code": "PRICE",
        "name": "Price and Industrial Statistics",
        "kind": "domain",
        "description": "Consumer and producer price indices, industrial production and deflation.",
        "source_ref": "MoSPI/NSO CPI, WPI and IIP methodological notes",
        "competencies": [
            ("PRICE.01", "Price index construction",
             "Constructs and interprets Laspeyres/Paasche/Fisher indices with correct weighting.",
             "Index methodology determines measured inflation.",
             ["Computes a weighted price index from item data", "Explains substitution bias in a fixed-basket index"]),
            ("PRICE.02", "Index review and item basket maintenance",
             "Reviews item baskets, weights and outlets as consumption patterns change.",
             "Stale baskets misstate current price movement.",
             ["Proposes a basket revision with evidence", "Assesses the impact of a weight change"]),
        ],
    },
    {
        "code": "DQ",
        "name": "Data Quality, Metadata and Dissemination",
        "kind": "domain",
        "description": "Quality dimensions, metadata standards, revision policy and dissemination.",
        "source_ref": "MoSPI National Policy on Official Statistics (draft 2018); international quality frameworks",
        "competencies": [
            ("DQ.01", "Data quality dimensions",
             "Assesses accuracy, coherence, timeliness, comparability and interpretability using defined criteria.",
             "Quality cannot be improved without being measured against explicit dimensions.",
             ["Scores a dataset against quality dimensions", "Designs a quality indicator for a survey round"]),
            ("DQ.02", "Metadata and documentation",
             "Produces machine-usable metadata describing concepts, methods and quality.",
             "Undocumented statistics cannot be reused or defended.",
             ["Writes a methodological note for a release", "Completes a metadata record for a dataset"]),
            ("DQ.03", "Revision and dissemination policy",
             "Applies a documented revision policy and appropriate release practice.",
             "Undisclosed revisions damage institutional credibility.",
             ["Classifies a change as routine revision versus error correction", "Applies pre-release access rules"]),
        ],
    },
    {
        "code": "COMP",
        "name": "Statistical Computing and Data Engineering",
        "kind": "technical",
        "description": "Reproducible statistical computing, data pipelines and database work.",
        "source_ref": "Generic technical competency; no official MoSPI syllabus located",
        "competencies": [
            ("COMP.01", "Reproducible analysis in R or Python",
             "Writes scripted, version-controlled analysis that another officer can re-run.",
             "Reproducibility is a precondition for methodological audit.",
             ["Converts a manual tabulation into a script", "Structures a project for reproducibility"]),
            ("COMP.02", "Data validation and pipeline integrity",
             "Implements validation rules and audit trails in data processing pipelines.",
             "Silent processing errors corrupt published series.",
             ["Writes range, consistency and duplicate checks", "Designs an audit trail for a processing step"]),
            ("COMP.03", "Database and SQL competence",
             "Queries and maintains survey micro-data using relational databases.",
             "Large unit-level datasets require disciplined database handling.",
             ["Writes joins and aggregations over micro-data", "Designs indexes for a query workload"]),
        ],
    },
    {
        "code": "ECON",
        "name": "Econometric and Economic Analysis",
        "kind": "technical",
        "description": "Applied econometrics and economic interpretation of statistical series.",
        "source_ref": "Generic technical competency; no official MoSPI syllabus located",
        "competencies": [
            ("ECON.01", "Regression modelling and diagnostics",
             "Specifies, estimates and diagnoses regression models on survey or time-series data.",
             "Analytical claims must survive basic specification checks.",
             ["Interprets coefficients with correct standard errors", "Detects heteroskedasticity or collinearity"]),
            ("ECON.02", "Time-series analysis",
             "Handles seasonality, trend and stationarity in official time series.",
             "Unadjusted series comparisons mislead policy users.",
             ["Applies seasonal adjustment and explains the method", "Tests for unit roots before modelling"]),
        ],
    },
    {
        "code": "GIS",
        "name": "Geospatial Statistics",
        "kind": "technical",
        "description": "Spatial data handling and geospatial linkage for statistical production.",
        "source_ref": "Generic technical competency; no official MoSPI syllabus located",
        "competencies": [
            ("GIS.01", "Spatial data handling",
             "Manages coordinate systems, spatial joins and geo-referenced survey frames.",
             "Mis-projected data corrupts spatial analysis and mapping.",
             ["Reprojects a layer correctly", "Performs a point-in-polygon join for frame construction"]),
            ("GIS.02", "Small-area and grid statistics",
             "Produces disaggregated estimates using small-area or grid-based methods.",
             "Policy demand increasingly requires sub-district estimates.",
             ["Explains the assumptions of a small-area model", "Produces a grid-based aggregation"]),
        ],
    },
    {
        "code": "AIDATA",
        "name": "Big Data and Responsible AI for Official Statistics",
        "kind": "technical",
        "description": "Alternative data sources, machine learning and responsible AI use in statistical production.",
        "source_ref": "Generic technical competency; emerging area, no official MoSPI syllabus located",
        "competencies": [
            ("AIDATA.01", "Alternative and big data sources",
             "Assesses fitness-for-purpose of non-survey data sources for statistical use.",
             "New sources can improve timeliness but carry coverage and selection bias.",
             ["Evaluates coverage bias in an administrative source", "Documents the quality limits of an alternative source"]),
            ("AIDATA.02", "Machine learning with statistical rigour",
             "Applies ML methods with proper validation, uncertainty and bias assessment.",
             "Unvalidated models produce confident but wrong statistics.",
             ["Designs a leakage-free validation split", "Reports model uncertainty honestly"]),
            ("AIDATA.03", "Responsible AI governance",
             "Applies transparency, explainability and fairness requirements to statistical AI use.",
             "Statistical AI decisions affect public trust and policy.",
             ["Documents model limitations for a statistical release", "Identifies a fairness risk in a classification model"]),
        ],
    },
    {
        "code": "COMM",
        "name": "Statistical Communication and Dissemination",
        "kind": "functional",
        "description": "Communicating statistics accurately to policy and public audiences.",
        "source_ref": "Generic functional competency; MoSPI dissemination practice",
        "competencies": [
            ("COMM.01", "Data visualisation integrity",
             "Creates charts that represent data truthfully without distortion.",
             "Misleading visualisation destroys trust even when the numbers are right.",
             ["Detects a truncated-axis distortion", "Chooses an appropriate chart for a distribution"]),
            ("COMM.02", "Statistical writing for policy",
             "Writes release notes and briefs that state findings, uncertainty and limitations clearly.",
             "Users act on interpretation, not raw tables.",
             ["Writes a findings summary with uncertainty", "Translates a regression result for a non-technical reader"]),
        ],
    },
    {
        "code": "GOV",
        "name": "Professional and Governance Competencies",
        "kind": "behavioural",
        "description": "Functional and behavioural competencies for statistical cadres (FRAC-aligned).",
        "source_ref": "DoPT/ISTM Framework of Roles, Activities and Competencies (FRAC)",
        "competencies": [
            ("GOV.01", "Stakeholder coordination",
             "Coordinates with data providers, ministries and state counterparts to deliver statistical work.",
             "Statistical production depends on inter-institutional cooperation.",
             ["Plans a data-sharing arrangement with a line ministry", "Handles a data-quality dispute with a provider"]),
            ("GOV.02", "Training and capability building",
             "Delivers training and mentoring to strengthen statistical capability in a team.",
             "Capacity building is a stated objective of the statistical system.",
             ["Designs a short training session for field staff", "Assesses a trainee's competency gap"]),
            ("GOV.03", "Integrity and ethics in statistics",
             "Upholds independence, objectivity and transparency in statistical work.",
             "Political or administrative pressure on statistics must be resisted on principle.",
             ["Identifies a conflict of interest in a release decision", "Applies a documented escalation path"]),
        ],
    },
]

# prerequisite edges: (competency, prerequisite, min_level)
PREREQUISITES = [
    ("SAMP.02", "SAMP.01", 3),
    ("SAMP.04", "SAMP.03", 2),
    ("EST.01", "SAMP.01", 3),
    ("EST.02", "EST.01", 3),
    ("EST.03", "EST.01", 2),
    ("NA.02", "NA.01", 3),
    ("PRICE.02", "PRICE.01", 3),
    ("DQ.02", "DQ.01", 2),
    ("DQ.03", "DQ.01", 3),
    ("ECON.01", "EST.01", 3),
    ("ECON.02", "ECON.01", 2),
    ("GIS.02", "GIS.01", 3),
    ("AIDATA.02", "COMP.01", 3),
    ("AIDATA.03", "AIDATA.02", 2),
    ("COMM.01", "DQ.01", 2),
]

# ---------------------------------------------------------------- job roles
JOB_ROLES = [
    {
        "code": "JSO",
        "title": "Junior Statistical Officer / Statistical Investigator",
        "cadre": "Subordinate Statistical Service",
        "grade": "Entry",
        "description": "Collects field data, administers schedules and performs first-level validation.",
        "reqs": [
            ("STAT.01", 3, 5, True), ("STAT.02", 2, 3, False), ("STAT.03", 3, 4, True),
            ("SAMP.03", 3, 4, True), ("SAMP.04", 3, 4, True),
            ("COMP.02", 2, 3, False), ("COMM.01", 2, 2, False), ("GOV.03", 3, 5, True),
        ],
    },
    {
        "code": "SO",
        "title": "Statistical Officer (Regional / Zonal)",
        "cadre": "Subordinate Statistical Service",
        "grade": "Middle",
        "description": "Supervises field operations, scrutinises schedules and audits field quality.",
        "reqs": [
            ("STAT.01", 4, 5, True), ("SAMP.01", 3, 5, True), ("SAMP.03", 4, 4, True),
            ("SAMP.04", 4, 5, True), ("EST.01", 3, 4, True), ("COMP.02", 3, 3, False),
            ("DQ.01", 3, 4, True), ("GOV.01", 3, 4, False), ("GOV.02", 3, 3, False),
        ],
    },
    {
        "code": "ISS-SURVEY",
        "title": "ISS Officer — Survey Design and Operations",
        "cadre": "Indian Statistical Service",
        "grade": "JTS/STS",
        "description": "Designs sample surveys, instruments and estimation methodology.",
        "reqs": [
            ("STAT.01", 4, 5, True), ("STAT.02", 4, 4, False), ("STAT.03", 4, 5, True),
            ("SAMP.01", 5, 5, True), ("SAMP.02", 4, 5, True), ("SAMP.03", 4, 4, True),
            ("EST.01", 4, 5, True), ("EST.02", 4, 5, True), ("EST.03", 4, 4, True),
            ("COMP.01", 3, 3, False), ("DQ.02", 4, 4, True), ("GOV.01", 4, 3, False),
        ],
    },
    {
        "code": "ISS-NA",
        "title": "ISS Officer — National Accounts",
        "cadre": "Indian Statistical Service",
        "grade": "JTS/STS",
        "description": "Compiles national accounts aggregates and manages base revisions.",
        "reqs": [
            ("STAT.01", 4, 5, True), ("NA.01", 5, 5, True), ("NA.02", 4, 5, True),
            ("EST.01", 4, 4, True), ("ECON.01", 4, 4, True), ("ECON.02", 4, 3, False),
            ("COMP.01", 3, 3, False), ("DQ.02", 4, 4, True), ("GOV.03", 4, 4, True),
        ],
    },
    {
        "code": "ISS-PRICE",
        "title": "ISS Officer — Price and Industrial Statistics",
        "cadre": "Indian Statistical Service",
        "grade": "JTS/STS",
        "description": "Produces and reviews price and industrial production indices.",
        "reqs": [
            ("STAT.01", 4, 4, True), ("PRICE.01", 5, 5, True), ("PRICE.02", 4, 5, True),
            ("EST.01", 4, 4, True), ("EST.02", 3, 3, False), ("DQ.01", 4, 4, True),
            ("DQ.03", 4, 4, True), ("COMM.02", 3, 3, False), ("COMP.01", 3, 2, False),
        ],
    },
    {
        "code": "ANALYST",
        "title": "Statistical Data Analyst",
        "cadre": "Statistical cadre",
        "grade": "Middle",
        "description": "Performs estimation, statistical computing and analytical support.",
        "reqs": [
            ("STAT.01", 3, 4, True), ("EST.01", 4, 5, True), ("EST.02", 3, 4, True),
            ("EST.03", 3, 4, True), ("COMP.01", 4, 5, True), ("COMP.02", 4, 4, True),
            ("COMP.03", 4, 4, True), ("ECON.01", 3, 4, True), ("ECON.02", 3, 3, False),
            ("COMM.01", 3, 3, False),
        ],
    },
    {
        "code": "DQOFF",
        "title": "Data Quality and Dissemination Officer",
        "cadre": "Statistical cadre",
        "grade": "Middle/Senior",
        "description": "Owns quality assessment, metadata, revision policy and dissemination.",
        "reqs": [
            ("STAT.01", 4, 4, True), ("STAT.03", 4, 5, True), ("DQ.01", 5, 5, True),
            ("DQ.02", 5, 5, True), ("DQ.03", 4, 5, True), ("EST.02", 3, 3, False),
            ("COMM.01", 4, 4, True), ("COMM.02", 4, 4, True), ("GOV.01", 3, 3, False),
        ],
    },
    {
        "code": "TRAINER",
        "title": "Statistical Trainer / Capacity Building Officer",
        "cadre": "Statistical cadre / NSSTA",
        "grade": "Senior",
        "description": "Conducts training needs analysis, curriculum design and assessment.",
        "reqs": [
            ("STAT.01", 4, 4, True), ("STAT.02", 4, 4, True), ("GOV.02", 5, 5, True),
            ("GOV.01", 4, 4, True), ("GOV.03", 4, 5, True), ("DQ.01", 3, 3, False),
            ("COMM.02", 4, 4, True), ("SAMP.01", 3, 3, False), ("EST.01", 3, 3, False),
            ("AIDATA.03", 3, 3, False),
        ],
    },
]

# ---------------------------------------------------------------- courses (DEMONSTRATION content)
# provider_url is intentionally omitted wherever we could not verify a real public URL.
COURSES = [
    {
        "code": "C-STAT-101",
        "title": "Foundations of India's Official Statistical System",
        "summary": "How official statistics are produced, cleared and disseminated in India.",
        "provider": "NSSTA (indicative)",
        "level": "foundation",
        "duration_minutes": 180,
        "tags": ["official statistics", "governance", "foundations"],
        "objectives": [
            "Describe the statistical production value chain",
            "Identify the mandate of MoSPI, NSO, NSC and NSSTA",
            "Apply confidentiality rules to micro-data requests",
        ],
        "competencies": [("STAT.01", 3), ("STAT.02", 2), ("STAT.03", 2)],
        "materials": [
            ("Statistical production value chain", "reading", 45),
            ("Institutions and mandates", "reading", 40),
            ("Confidentiality and release practice", "reading", 35),
            ("Knowledge check", "quiz", 20),
        ],
    },
    {
        "code": "C-SAMP-201",
        "title": "Sample Design for Household Surveys",
        "summary": "Stratification, multi-stage selection and sample allocation for national surveys.",
        "provider": "NSSTA (indicative)",
        "level": "advanced",
        "duration_minutes": 360,
        "tags": ["sampling", "survey design", "methodology"],
        "objectives": [
            "Select a defensible sample design for a household survey",
            "Derive sample size from precision requirements",
            "Document the design for a methodological note",
        ],
        "competencies": [("SAMP.01", 4), ("SAMP.02", 4), ("EST.01", 2)],
        "materials": [
            ("Stratification and stage selection", "reading", 70),
            ("Sample size derivation", "worked_example", 60),
            ("Allocation across strata", "worked_example", 50),
            ("Design documentation", "reading", 40),
        ],
    },
    {
        "code": "C-SAMP-202",
        "title": "Questionnaire and Schedule Design",
        "summary": "Writing valid questions, skip logic and validation rules for statistical schedules.",
        "provider": "NSSTA (indicative)",
        "level": "intermediate",
        "duration_minutes": 210,
        "tags": ["survey design", "instrument", "questionnaire"],
        "objectives": [
            "Detect flawed question wording",
            "Specify skip logic and consistency checks",
            "Pilot a schedule before full field launch",
        ],
        "competencies": [("SAMP.03", 4), ("SAMP.04", 2)],
        "materials": [
            ("Question wording pitfalls", "reading", 45),
            ("Skip logic and validation rules", "reading", 50),
            ("Field pilot design", "reading", 35),
        ],
    },
    {
        "code": "C-EST-301",
        "title": "Estimation and Variance for Complex Samples",
        "summary": "Design-consistent estimation, weighting and variance estimation.",
        "provider": "NSSTA (indicative)",
        "level": "advanced",
        "duration_minutes": 420,
        "tags": ["estimation", "variance", "weighting"],
        "objectives": [
            "Compute design-consistent estimates with weights",
            "Produce and interpret standard errors",
            "Handle non-response with a documented adjustment",
        ],
        "competencies": [("EST.01", 4), ("EST.02", 4), ("EST.03", 3)],
        "materials": [
            ("Weighting and design consistency", "reading", 70),
            ("Linearisation and replication", "worked_example", 80),
            ("Non-response adjustment", "reading", 60),
        ],
    },
    {
        "code": "C-NA-401",
        "title": "National Accounts Compilation",
        "summary": "SNA identities, sector classification and compilation methods.",
        "provider": "NSSTA (indicative)",
        "level": "advanced",
        "duration_minutes": 480,
        "tags": ["national accounts", "GDP", "SNA"],
        "objectives": [
            "Apply production, income and expenditure identities",
            "Compile an activity-level value added estimate",
            "Explain the effect of a base-year revision",
        ],
        "competencies": [("NA.01", 4), ("NA.02", 4), ("ECON.01", 2)],
        "materials": [
            ("SNA identities and sectors", "reading", 80),
            ("Compilation by activity", "worked_example", 90),
            ("Base revision practice", "reading", 60),
        ],
    },
    {
        "code": "C-PRICE-402",
        "title": "Price Index Construction and Review",
        "summary": "Basket design, weighting formula choice and index maintenance.",
        "provider": "NSSTA (indicative)",
        "level": "advanced",
        "duration_minutes": 300,
        "tags": ["price statistics", "CPI", "index numbers"],
        "objectives": [
            "Compute a weighted index from item-level prices",
            "Compare Laspeyres, Paasche and Fisher indices",
            "Plan an item basket revision",
        ],
        "competencies": [("PRICE.01", 4), ("PRICE.02", 3)],
        "materials": [
            ("Index number formulae", "reading", 55),
            ("Basket and weight maintenance", "reading", 50),
            ("Revision impact assessment", "worked_example", 45),
        ],
    },
    {
        "code": "C-DQ-501",
        "title": "Data Quality Assessment and Metadata",
        "summary": "Quality dimensions, indicator design and machine-usable metadata.",
        "provider": "NSSTA (indicative)",
        "level": "intermediate",
        "duration_minutes": 240,
        "tags": ["data quality", "metadata", "dissemination"],
        "objectives": [
            "Score a dataset against six quality dimensions",
            "Write a methodological note",
            "Apply a revision policy",
        ],
        "competencies": [("DQ.01", 4), ("DQ.02", 4), ("DQ.03", 3)],
        "materials": [
            ("Quality dimensions in practice", "reading", 55),
            ("Writing metadata", "reading", 45),
            ("Revision and correction policy", "reading", 40),
        ],
    },
    {
        "code": "C-COMP-601",
        "title": "Reproducible Statistical Computing in Python",
        "summary": "Scripted, version-controlled analysis with validation checks.",
        "provider": "Internal capacity building (indicative)",
        "level": "intermediate",
        "duration_minutes": 300,
        "tags": ["python", "reproducibility", "data engineering"],
        "objectives": [
            "Structure an analysis project for reproducibility",
            "Implement validation rules on incoming data",
            "Produce a re-runnable tabulation",
        ],
        "competencies": [("COMP.01", 4), ("COMP.02", 3), ("COMP.03", 2)],
        "materials": [
            ("Project structure and versioning", "reading", 45),
            ("Validation rule implementation", "worked_example", 60),
            ("From spreadsheet to script", "worked_example", 70),
        ],
    },
    {
        "code": "C-COMP-602",
        "title": "SQL for Survey Micro-data",
        "summary": "Querying, joining and indexing unit-level survey data.",
        "provider": "Internal capacity building (indicative)",
        "level": "intermediate",
        "duration_minutes": 240,
        "tags": ["sql", "databases", "microdata"],
        "objectives": [
            "Write joins and aggregations over micro-data",
            "Choose indexes for a query workload",
            "Protect confidentiality in extracts",
        ],
        "competencies": [("COMP.03", 4), ("COMP.02", 2)],
        "materials": [
            ("Relational model for survey data", "reading", 50),
            ("Aggregation and window functions", "worked_example", 55),
            ("Indexing and confidentiality in extracts", "reading", 40),
        ],
    },
    {
        "code": "C-ECON-701",
        "title": "Applied Econometrics for Official Statistics",
        "summary": "Regression with survey data, diagnostics and cautious interpretation.",
        "provider": "NSSTA (indicative)",
        "level": "advanced",
        "duration_minutes": 360,
        "tags": ["econometrics", "regression", "analysis"],
        "objectives": [
            "Specify and diagnose a regression on survey data",
            "Interpret coefficients with correct uncertainty",
            "Handle seasonality in official series",
        ],
        "competencies": [("ECON.01", 4), ("ECON.02", 3), ("EST.02", 2)],
        "materials": [
            ("Specification and diagnostics", "reading", 70),
            ("Weighted regression", "worked_example", 55),
            ("Seasonal adjustment", "reading", 50),
        ],
    },
    {
        "code": "C-GIS-801",
        "title": "Geospatial Methods for Statistical Production",
        "summary": "Projections, spatial joins and grid-based aggregation.",
        "provider": "Internal capacity building (indicative)",
        "level": "intermediate",
        "duration_minutes": 240,
        "tags": ["gis", "geospatial", "small area"],
        "objectives": [
            "Reproject layers correctly",
            "Perform point-in-polygon joins for frame construction",
            "Produce grid-based aggregates",
        ],
        "competencies": [("GIS.01", 4), ("GIS.02", 2)],
        "materials": [
            ("Coordinate systems and projections", "reading", 45),
            ("Spatial joins for frames", "worked_example", 50),
            ("Grid-based statistics", "reading", 40),
        ],
    },
    {
        "code": "C-AI-901",
        "title": "Responsible AI and Big Data in Official Statistics",
        "summary": "Alternative data sources, ML validation and AI governance for statistics.",
        "provider": "Internal capacity building (indicative)",
        "level": "advanced",
        "duration_minutes": 300,
        "tags": ["ai", "big data", "responsible ai", "machine learning"],
        "objectives": [
            "Assess fitness-for-purpose of an alternative data source",
            "Design leakage-free model validation",
            "Document AI limitations for a statistical release",
        ],
        "competencies": [("AIDATA.01", 4), ("AIDATA.02", 3), ("AIDATA.03", 4)],
        "materials": [
            ("Alternative data and coverage bias", "reading", 55),
            ("Validation without leakage", "worked_example", 50),
            ("AI governance and disclosure", "reading", 45),
        ],
    },
    {
        "code": "C-COMM-1001",
        "title": "Communicating Statistics Without Distortion",
        "summary": "Chart integrity, uncertainty communication and policy briefs.",
        "provider": "Internal capacity building (indicative)",
        "level": "foundation",
        "duration_minutes": 150,
        "tags": ["communication", "visualisation", "dissemination"],
        "objectives": [
            "Detect distorted charts",
            "State uncertainty clearly in a summary",
            "Write a policy-facing findings brief",
        ],
        "competencies": [("COMM.01", 4), ("COMM.02", 4)],
        "materials": [
            ("Chart integrity", "reading", 35),
            ("Uncertainty for policy audiences", "reading", 35),
            ("Findings brief workshop", "worked_example", 40),
        ],
    },
    {
        "code": "C-GOV-1101",
        "title": "Statistical Integrity and Professional Ethics",
        "summary": "Independence, objectivity and escalation paths in statistical work.",
        "provider": "NSSTA (indicative)",
        "level": "foundation",
        "duration_minutes": 120,
        "tags": ["ethics", "governance", "integrity"],
        "objectives": [
            "Recognise pressure that compromises statistical independence",
            "Apply an escalation path",
            "Document a conflict of interest",
        ],
        "competencies": [("GOV.03", 4), ("STAT.03", 2)],
        "materials": [
            ("Independence and objectivity", "reading", 35),
            ("Conflicts of interest", "reading", 30),
            ("Case studies", "reading", 30),
        ],
    },
    {
        "code": "C-GOV-1102",
        "title": "Training Design for Statistical Cadres",
        "summary": "Training needs analysis, session design and assessment.",
        "provider": "Internal capacity building (indicative)",
        "level": "intermediate",
        "duration_minutes": 210,
        "tags": ["training", "capacity building", "facilitation"],
        "objectives": [
            "Conduct a training needs analysis",
            "Design a competency-based session",
            "Assess trainee competency gain",
        ],
        "competencies": [("GOV.02", 4), ("GOV.01", 2), ("COMM.02", 2)],
        "materials": [
            ("Training needs analysis", "reading", 45),
            ("Session design from competencies", "reading", 45),
            ("Assessment of learning", "reading", 35),
        ],
    },
    {
        "code": "C-STAT-102",
        "title": "Field Scrutiny and Survey Quality Control",
        "summary": "Checklists, replacement rules and field audit for survey operations.",
        "provider": "NSSTA (indicative)",
        "level": "intermediate",
        "duration_minutes": 180,
        "tags": ["field operations", "quality control", "supervision"],
        "objectives": [
            "Apply a scrutiny checklist to returned schedules",
            "Plan field supervision and replacement",
            "Detect fabrication patterns in field data",
        ],
        "competencies": [("SAMP.04", 4), ("COMP.02", 2), ("DQ.01", 2)],
        "materials": [
            ("Scrutiny checklist", "reading", 40),
            ("Supervision and replacement rules", "reading", 40),
            ("Detecting fabrication", "worked_example", 35),
        ],
    },
    {
        "code": "C-DQ-502",
        "title": "Dissemination, Revision and Pre-release Practice",
        "summary": "Release calendars, revision policy and pre-release access control.",
        "provider": "NSSTA (indicative)",
        "level": "intermediate",
        "duration_minutes": 150,
        "tags": ["dissemination", "revision", "release"],
        "objectives": [
            "Classify a change as revision or error correction",
            "Apply pre-release access rules",
            "Publish a release calendar",
        ],
        "competencies": [("DQ.03", 4), ("DQ.02", 3), ("COMM.02", 2)],
        "materials": [
            ("Revision policy design", "reading", 40),
            ("Pre-release access", "reading", 30),
            ("Release calendar practice", "reading", 30),
        ],
    },
]

# ---------------------------------------------------------------- demo reference documents
# Short, self-authored briefing notes used to exercise the RAG pipeline. Marked DEMONSTRATION.
DEMO_DOCUMENTS = [
    {
        "filename": "sampling-design-primer.txt",
        "title": "Sampling Design Primer (Demonstration Material)",
        "topic": "Sampling design",
        "competencies": ["SAMP.01", "SAMP.02"],
        "content": """SAMPLING DESIGN PRIMER — DEMONSTRATION MATERIAL

1. PURPOSE OF A SAMPLE DESIGN
A sample design specifies how units are selected from a population frame, how large the sample
should be, and how the selected units are weighted to produce estimates. A design is defensible only
when its selection probabilities are known and documented.

2. STRATIFICATION
Stratification divides the population into non-overlapping groups (strata) that are internally more
homogeneous than the population as a whole. Common stratifiers in Indian household surveys are
region, sector (rural or urban), and population size of the village or urban block. Stratification
reduces variance when between-stratum variation is large relative to within-stratum variation.

3. MULTI-STAGE SELECTION
National household surveys typically use a multi-stage design. In the first stage, primary sampling
units (villages in rural areas, urban blocks in urban areas) are selected with probability
proportional to size. In the second stage, households are selected from each sampled first-stage
unit using a systematic random sample. The inclusion probability of a household is therefore the
product of the first-stage and second-stage selection probabilities.

4. SAMPLE SIZE
Sample size is derived from the precision requirement, not chosen by convenience. For a proportion
estimate, the approximate sample size per domain is n = z^2 * p * (1 - p) / e^2, inflated for the
design effect and for expected non-response. If a design effect of 1.5 and a non-response rate of
10 percent are expected, the computed n is divided by the design effect and multiplied by
1 / (1 - 0.10).

5. SAMPLE ALLOCATION
When total sample size is fixed, proportional allocation distributes it across strata in proportion
to stratum size. Neyman allocation distributes it in proportion to stratum size multiplied by the
within-stratum standard deviation, which minimises variance for a fixed cost when unit costs are
equal across strata.

6. DOCUMENTATION REQUIREMENTS
A sample design note should record the frame used and its known defects, the stratification
variables, the number of stages, the selection method at each stage, the achieved sample size by
domain, the weighting procedure, and the variance estimation method. Without these six elements the
estimates cannot be independently audited.

7. COMMON FAILURES
The most frequent design failures are: an outdated frame that omits new settlements; uncontrolled
replacement of non-responding households, which biases estimates toward households that are easier
to reach; and reporting estimates below the domain level for which the sample was designed.
""",
    },
    {
        "code": "sqc",
        "filename": "survey-quality-control-note.txt",
        "title": "Survey Quality Control Note (Demonstration Material)",
        "topic": "Data quality",
        "competencies": ["DQ.01", "SAMP.04"],
        "content": """SURVEY QUALITY CONTROL NOTE — DEMONSTRATION MATERIAL

1. WHY QUALITY CONTROL IS SEPARATE FROM ESTIMATION
Estimation assumes the data are what they claim to be. Quality control establishes that assumption.
A statistically elegant estimate computed from fabricated returns is worse than no estimate, because
it carries false authority.

2. THE SIX QUALITY DIMENSIONS
Data quality is assessed on six dimensions: relevance, accuracy, timeliness, coherence,
comparability, and interpretability. Each dimension requires an explicit indicator. For accuracy, a
common indicator is the re-interview discrepancy rate. For timeliness, it is the lag in days between
the reference period and the release. For coherence, it is the size of the residual in an accounting
identity.

3. SCRUTINY OF RETURNED SCHEDULES
Scrutiny applies range checks, consistency checks across related items, and duplicate detection. A
range check flags values outside plausible bounds. A consistency check flags combinations that cannot
co-occur, such as a household reporting expenditure on an item while reporting zero consumption of
that item. Duplicate detection compares household identifiers and location against previously
accepted returns.

4. DETECTING FABRICATION
Fabricated returns frequently show digit preference, improbable interview durations, identical
response patterns across different households, and clustering of values around round numbers. Field
audits with surprise re-interviews are the most reliable detection method; statistical screens only
generate suspicion.

5. SUPERVISION RATIOS
A common supervision standard is that at least ten percent of schedules are re-verified by a
supervisor, with a higher ratio for newly recruited investigators. The ratio is a policy choice and
should be documented rather than assumed.

6. NON-SAMPLING ERROR
Non-sampling errors include coverage error, non-response error, measurement error and processing
error. They are usually larger than sampling error in large national surveys and cannot be reduced by
increasing sample size. Reducing them requires instrument design, training, supervision and
processing controls.
""",
    },
    {
        "code": "naindex",
        "filename": "price-index-fundamentals.txt",
        "title": "Price Index Fundamentals (Demonstration Material)",
        "topic": "Price statistics",
        "competencies": ["PRICE.01", "PRICE.02"],
        "content": """PRICE INDEX FUNDAMENTALS — DEMONSTRATION MATERIAL

1. WHAT AN INDEX MEASURES
A price index measures the change in the cost of a fixed basket of goods and services between a base
period and a current period. It is a ratio, not a price level. An index of 142 with base 100 means the
basket costs 42 percent more than in the base period.

2. LASPEYRES, PAASCHE AND FISHER
The Laspeyres index weights price relatives by base-period quantities. The Paasche index weights them
by current-period quantities. The Laspeyres index tends to overstate inflation because it holds the
basket fixed while consumers substitute away from items whose relative prices have risen. The Fisher
index is the geometric mean of the Laspeyres and Paasche indices and is commonly described as
superlative because it satisfies more of the desirable index number axioms.

3. SUBSTITUTION BIAS
Substitution bias is the upward distortion in a fixed-basket index caused by consumers replacing
relatively expensive items with cheaper alternatives. It is a structural feature of Laspeyres indices
and is one reason baskets are revised periodically.

4. WEIGHTING AND THE WEIGHT REFERENCE PERIOD
Weights come from a household consumption expenditure survey and refer to a specific reference
period. If consumption patterns have changed substantially since the weight reference period, the
index becomes less representative. The gap between the weight reference period and the current
period is a quality limitation that should be disclosed.

5. BASKET REVISION
A basket revision updates the item list, the outlet sample and the weights. Revisions are triggered
by evidence of structural change in consumption, by the availability of a newer expenditure survey,
and by the appearance of new products with material expenditure shares. A revision changes the series
level and therefore requires a linking procedure and a published explanation.

6. DEFLATION
Deflation converts nominal values to real values by dividing by an appropriate price index. Using a
general consumer price index to deflate a narrowly defined nominal series introduces measurement
error; the deflator should match the coverage of the series being deflated.

7. INTERPRETATION CAUTIONS
An index covering a national average does not describe the experience of any particular household.
Sub-group indices, where published, are more informative for distributional questions but carry
larger sampling error.
""",
    },
]
