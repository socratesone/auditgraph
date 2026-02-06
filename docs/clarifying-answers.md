# Clarifying Answers and Implementation Assumptions

This document captures the assumed answers to the clarifying questions and ties them to the current implementation plan. These answers can be revised once stakeholders confirm priorities.

## A) Users and Workflows

1) **Primary user profile**
   - **Answer:** A small engineering team (2–8 people) with one primary maintainer.
   - **Why:** Balances solo workflows with light collaboration, so deterministic outputs and repeatable runs matter.

2) **Knowledge domains**
   - **Answer:** Primarily software-engineering concepts with a small amount of project planning and research notes.
   - **Why:** Drives strong support for code symbols, ADRs, and reproducible provenance.

3) **Top 5 workflows (ranked)**
   - **Answer:**
     1. Codebase comprehension
     2. ADRs
     3. Debugging logs
     4. Project planning
     5. Quick capture notes

4) **Query/answer expectations**
   - **Answer:** Question answering with citations and inspectable result explanations.
   - **Why:** Trust and auditability are central; raw graph exploration is secondary.

5) **Ingestion volume and scale**
   - **Answer:** Daily 10–50 files, 2–10 MB, and 2–10k LOC changed; weekly up to 500 files.
   - **Why:** Suggests incremental ingestion with hashes and stable manifests.

6) **Latency tolerance by workflow**
   - **Answer:**
     - Search/query: <200 ms p50, <1s p95
     - Ingest/extract: background batch acceptable up to 10–30s for 100 files
     - UI navigation: <1s

7) **Maintenance budget**
   - **Answer:** 5 minutes/day for review queue triage.
   - **Why:** Allows conservative defaults but enables optional proposals.

## B) Data Sources and Formats

1) **Day-1 sources (must-have)**
   - **Answer:** Markdown, plain text, Git repos.

2) **PDF reality**
   - **Answer:** Born-digital text only; OCR deferred.

3) **Code languages**
   - **Answer:** Python, TypeScript/JavaScript, Go (start with heuristics; add AST later).

4) **Structured sources**
   - **Answer:** JSON/YAML manifests and OpenAPI specs (opt-in).

5) **Capture channels**
   - **Answer:** Manual CLI import + Git-based scanning; watcher later.

6) **Normalization rules**
   - **Answer:** Canonical frontmatter schema preferred, with best-effort fallback.

## C) Determinism and Trust

1) **Determinism boundaries**
   - **Answer:** Extraction outputs, link creation, ranking order, and QA responses must be deterministic.

2) **Failure modes**
   - **Answer:** Record "unknown" and queue for review; skip only on parse failure with log entry.

3) **Audit artifacts**
   - **Answer:** Per-artifact hashes, per-run manifests, provenance edges, pipeline version pin, and prompt logs for optional LLM.

4) **Config immutability**
   - **Answer:** Immutable profile snapshots per run; config can evolve but runs reference a snapshot hash.

5) **Ranking determinism**
   - **Answer:** Stable order required across OS/hardware with explicit tie-break keys.

## D) Knowledge Model

1) **Definitions**
   - **Entity:** A canonical node (symbol, file, person, project, decision, error signature).
   - **Fact/Claim:** Atomic assertion with provenance.
   - **Note:** User-authored source artifact.
   - **Task:** Action item extracted or written in notes.
   - **Decision:** ADR-style resolved choice with rationale.
   - **Event:** Time-scoped occurrence (incident, deploy, meeting).

2) **Contradictions**
   - **Answer:** Explicit support for contradictory claims with a conflict flag.

3) **Temporal facts**
   - **Answer:** Required; time windows supported for decisions and events.

4) **Confidence**
   - **Answer:** Rule-based confidence only in MVP.

5) **Ontologies / typing**
   - **Answer:** Single shared ontology with namespaces per domain.

## E) Search and Retrieval

1) **Query types**
   - **Answer:** Keyword, hybrid (keyword + semantic), graph traversal, and "show sources for claim".

2) **Dataset scale**
   - **Answer:** 10k notes, 50 repos, 1M code symbols within 12 months.

3) **Local embeddings constraints**
   - **Answer:** CPU-only local embeddings, optional, <=1.5 GB model size.

4) **Offline-first UX**
   - **Answer:** Fully offline core; semantic search optional offline.

## F) Linking and Navigation

1) **Link generation policy**
   - **Answer:** Deterministic rules only for authoritative links; optional suggestions flagged as non-authoritative.

2) **Link types**
   - **Answer:** mentions, defines, implements, depends_on, decided_in, relates_to, cites.

3) **Explainability**
   - **Answer:** Always require rule id + evidence snippet; include similarity score when applicable.

4) **Backlinks and neighborhoods**
   - **Answer:** Backlinks computed on demand in MVP; stored when performance demands it.

## G) Automation and Integrations

1) **Automations**
   - **Answer:** Daily digest and changed-since-yesterday reports.

2) **Interface preference**
   - **Answer:** CLI-first, optional local web UI later.

3) **Editor integration depth**
   - **Answer:** Open results and insert links (phase 2+).

4) **Extensibility model**
   - **Answer:** Script-based plugins (Python) with deterministic outputs.

## H) Privacy, Security, Compliance

1) **Encryption at rest**
   - **Answer:** Not required for source store; optional for exports.

2) **Secrets handling**
   - **Answer:** Automatic detection + redaction in derived artifacts and exports.

3) **Multi-profile separation**
   - **Answer:** Required; separate profile roots with no cross-profile queries.

4) **Export policy**
   - **Answer:** Support redaction profiles for clean-room sharing.

## I) Distribution and Maintainability

1) **Target OS**
   - **Answer:** Linux + macOS day 1.

2) **Packaging**
   - **Answer:** Python package with a console script.

3) **Upgrade strategy**
   - **Answer:** Derived artifacts can be rebuilt; keep old outputs in versioned run folders.

4) **Performance budgets**
   - **Answer:** Index footprint <=2x source size.

## Implementation Notes

- The CLI scaffold establishes the command surface (init/version/ingest/extract/link/index/query/rebuild) and provides a workspace initializer.
- The sample `config/pkg.yaml` encodes the assumed defaults for normalization, extraction, linking, and search.

## J) Pipeline Stages

1) **Atomic write strategy**
   - **Answer:** Write artifacts to temp paths, atomically rename/move into place, then write the manifest last.

2) **Dependency validation**
   - **Answer:** Require upstream manifests for the same run_id before stage execution.

3) **Recovery rule**
   - **Answer:** If the manifest is missing, discard temp artifacts and rerun the stage.

## K) Storage Layout and Artifacts

1) **Storage root**
   - **Answer:** `.pkg/profiles/<profile>/` with run manifests under `.pkg/profiles/<profile>/runs/<run_id>/`.

2) **Sharding rule**
   - **Answer:** Two-character ID prefix sharding for entities, claims, and links.

3) **Stable IDs**
   - **Answer:** Canonicalized inputs hashed with sha256 and type prefixes; changes require version bumps.

## L) Linking and Explainability

1) **Link generation policy**
   - **Answer:** Deterministic rules produce authoritative links; optional suggestions are flagged non-authoritative.

2) **Link types**
   - **Answer:** mentions, defines, implements, depends_on, decided_in, relates_to, cites.

3) **Explainability payload**
   - **Answer:** Rule id + evidence snippet reference; include similarity score when applicable.

4) **Backlinks policy**
   - **Answer:** Backlinks computed on demand in MVP; stored only when performance requires it.
