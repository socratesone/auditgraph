# Clarifying Questions

## A) Users and Workflows

1) Primary user profile
- Q: Is the primary user a solo engineer, a team, or a research-heavy group?
- Rationale: Drives permissions, collaboration needs, and conflict resolution strategy.

2) Knowledge domains
- Q: Is the graph mostly software-engineering concepts (APIs, code symbols, ADRs), or mixed (personal + work + research)?
- Rationale: Impacts ontology/typing, redaction, and multi-profile boundaries.

3) Top 5 workflows (ranked)
- Q: Rank the importance of: quick capture notes, ADRs, debugging logs, learning notes, meeting notes, project planning, incident postmortems, codebase comprehension.
- Rationale: Determines MVP features and UI/CLI ergonomics.

4) Query/answer expectations
- Q: Is the system primarily for “search and recall”, or “question answering with citations”, or “graph exploration”?
- Rationale: Changes indexing, explanation UX, and retrieval pipeline complexity.

5) Ingestion volume and scale
- Q: Expected daily and weekly ingestion: number of files, MB, and LOC (lines of code) changed?
- Rationale: Determines incremental indexing design, caching, and performance targets.

6) Latency tolerance by workflow
- Q: What is “instant” for you: <50ms, <200ms, <1s? Which workflows need which?
- Rationale: Informs index strategy and whether background jobs are required.

7) Maintenance budget
- Q: How much manual review is acceptable per day: 0, 5 minutes, 30 minutes?
- Rationale: Sets human-in-the-loop design and confidence thresholds.

## B) Data Sources and Formats

1) Day-1 sources (must-have)
- Q: Which are mandatory on day 1: Markdown, org-mode, plain text, Git repos, code workspaces, PDFs, DOCX, HTML/web clippings, email exports (mbox), issue trackers exports (JSON)?
- Rationale: Sets parser scope and dependency footprint.

2) PDF reality
- Q: Are PDFs primarily “born-digital text” or scanned images?
- Rationale: Scanned PDFs require OCR (error-prone and less deterministic).

3) Code languages
- Q: Which languages must be parsed for symbol extraction (e.g., TS/JS, Python, Go, Rust, PHP, Java)?
- Rationale: AST tooling differs; determines feasibility of deterministic symbol graphs.

4) Structured sources
- Q: Should it ingest OpenAPI specs, Terraform, CI configs, JSON/YAML manifests?
- Rationale: Structured inputs yield high-quality deterministic entities/relations.

5) Capture channels
- Q: Should ingestion be directory-watch based, Git-based, editor-plugin based, or manual “import” commands?
- Rationale: Affects ergonomics and correctness of incremental updates.

6) Normalization rules
- Q: Do you want canonical frontmatter schemas for notes (title, tags, project, status), or “best effort” extraction?
- Rationale: Strong schemas improve determinism and reduce ambiguity.

## C) Determinism and Trust

1) Determinism boundaries
- Q: What must be deterministic: extraction outputs, link creation, ranking order, summaries, QA responses?
- Rationale: Helps decide where to allow optional non-deterministic features (if any).

2) Failure modes
- Q: When extraction fails, should the system: skip, record “unknown”, queue for review, or fall back to heuristics?
- Rationale: Impacts user trust and pipeline completeness.

3) Audit artifacts
- Q: Required audit trail: per-artifact hashes, per-run manifests, provenance edges, pipeline versioning, prompt logs, model version pins?
- Rationale: Defines the “replay” and “diff” contract.

4) Config immutability
- Q: Should runs be tied to immutable “profiles” (config snapshots), or can config evolve in place?
- Rationale: Strongly affects reproducibility and rollbacks.

5) Ranking determinism
- Q: If results have equal scores, must ordering be stable across OS and hardware?
- Rationale: Requires deterministic tie-break rules and stable sorting keys.

## D) Knowledge Model

1) Definitions
- Q: Define (in your terms) what counts as: entity, fact/claim, note, task, decision, event.
- Rationale: Prevents a model that “feels right” but is unusable.

2) Contradictions
- Q: Do you want explicit support for contradicting claims (A vs not-A), or just record both and let the user decide?
- Rationale: Determines claim model and UI for conflicts.

3) Temporal facts
- Q: Do facts need validity windows (“true from-to”) and time-based queries?
- Rationale: Impacts indexing and graph navigation (timelines).

4) Confidence
- Q: Do you want confidence scores? If yes, are they rule-based only, or can they be model-derived?
- Rationale: Model-derived scores can compromise determinism unless pinned and recorded.

5) Ontologies / typing
- Q: Single ontology or multiple (software concepts, personal projects, research papers)?
- Rationale: Influences namespace strategy and collision handling.

## E) Search and Retrieval

1) Query types
- Q: Which must be first-class: keyword, semantic, hybrid, graph traversal, “explain why connected”, “show sources for claim”?
- Rationale: Drives index design and UX.

2) Dataset scale
- Q: Target upper bounds within 12 months: 10k notes? 100 repos? 1M code symbols?
- Rationale: Determines whether embedded DBs are needed for indexes vs pure files.

3) Local embeddings constraints
- Q: Must embeddings be local-only? Any constraints: CPU-only, no GPU, max model size?
- Rationale: Determines feasibility and latency.

4) Offline-first UX
- Q: Should search be fully available offline with no degradation, or is semantic search optional offline?
- Rationale: Impacts packaging and default pipeline.

## F) Linking and Navigation

1) Link generation policy
- Q: Strict deterministic rules only, or allow optional suggestions (flagged as non-authoritative)?
- Rationale: Keeps core graph stable while enabling helpful extras.

2) Link types
- Q: Which typed edges matter most: mentions, defines, implements, depends_on, caused_by, decided_in, relates_to, cites?
- Rationale: Determines schema and UI filters.

3) Explainability
- Q: For every link, do you require “why”: match rule, evidence snippet, similarity score, or symbol reference?
- Rationale: Forces inspectability and trust.

4) Backlinks and neighborhoods
- Q: Must backlinks be explicit stored artifacts (diffable), or can they be computed on demand?
- Rationale: Stored backlinks improve speed but require maintenance logic.

## G) Automation and Integrations

1) Automations
- Q: Which are must-have: daily digest, “changed since yesterday”, stale-link detection, project memory snapshots, auto-ADR from PRs?
- Rationale: Determines scheduler and policy engine scope.

2) Interface preference
- Q: CLI-first only, or CLI + TUI (terminal UI), or a local web UI?
- Rationale: Impacts architecture (server component vs pure CLI).

3) Editor integration depth
- Q: Minimum editor integration: open results, insert links, capture note templates, inline graph peek?
- Rationale: Changes plugin APIs and prioritization.

4) Extensibility model
- Q: Do you prefer plugins as scripts (bash/python), WASM modules, or compiled plugins?
- Rationale: Affects security model and determinism guarantees.

## H) Privacy, Security, Compliance

1) Encryption at rest
- Q: Do you require encryption at rest for the store, or only for exports/sync?
- Rationale: Encryption complicates diffability unless carefully designed.

2) Secrets handling
- Q: Should secrets be automatically detected and redacted from derived artifacts?
- Rationale: Prevents leaks into indexes and exports.

3) Multi-profile separation
- Q: Need separate profiles (work vs personal) with hard isolation?
- Rationale: Determines directory layout and cross-profile querying rules.

4) Export policy
- Q: Should exports support redaction profiles and allow “clean-room” sharing?
- Rationale: Impacts provenance and packaging.

## I) Distribution and Maintainability

1) Target OS
- Q: Which OS must be supported day 1: Linux, macOS, Windows?
- Rationale: File watching and path normalization differ.

2) Packaging
- Q: Preferred packaging: single binary, Python package, Docker optional, or “bring your own runtime”?
- Rationale: Impacts adoption and deterministic runtime pinning.

3) Upgrade strategy
- Q: Are migrations allowed to rewrite derived artifacts, or must old outputs remain immutable with side-by-side versions?
- Rationale: Determines compatibility and rollback semantics.

4) Performance budgets
- Q: Max acceptable disk footprint for indexes relative to source text (e.g., 1x, 2x, 5x)?
- Rationale: Influences whether to store embeddings, backlinks, precomputed neighborhoods.

# Solution Space

## 1) Ingestion

Options
- Directory watcher (fs events)
  - Pros: Immediate updates, editor-agnostic.
  - Cons: OS-specific semantics; missed events; requires robust rescan logic.
- Git-based ingestion (polling or hooks)
  - Pros: Natural for engineers; aligns with commits; deterministic diffs.
  - Cons: Doesn’t cover ad-hoc notes unless in repo; hooks are per-repo config.
- Editor plugins (VS Code/Neovim/JetBrains)
  - Pros: Best capture UX, context (file, symbol, cursor).
  - Cons: Higher maintenance; multiplies surface area.
- Manual import (CLI)
  - Pros: Simple, deterministic, explicit.
  - Cons: More user friction; less “automatic”.

Change detection tradeoffs
- Hashing file contents (sha256)
  - Pros: Deterministic; robust; good provenance.
  - Cons: Requires reading full file; mitigated via mtime/size precheck.
- Git diffs (blob hashes)
  - Pros: Efficient; deterministic; incremental extraction on changed hunks.
  - Cons: Depends on Git availability and correct repo state.

Parsers by format
- Markdown/org/plain text: deterministic parsing (frontmatter + headings).
- Code: AST extraction (best), fallback to regex for quick wins.
- PDF/DOCX: deterministic text extraction for born-digital; scanned PDFs introduce OCR variance.

Rejected as core
- Cloud-only ingestion, proprietary note formats, closed sync agents (violates constraints).

## 2) Extraction

Deterministic pipelines
- Regex + heuristics
  - Pros: Fast; explainable; stable.
  - Cons: Limited recall; brittle across styles.
- AST extraction (code symbols, imports, call graphs)
  - Pros: High precision for code concepts.
  - Cons: Language-specific; requires parsers; more engineering effort.
- Schema mapping (frontmatter + templates)
  - Pros: High determinism; user-controllable.
  - Cons: Requires buy-in to conventions.

Optional LLM step (still reproducible)
- Pin model version + temperature=0 + store prompts + store outputs + store toolchain version.
- Record an “LLM transcript artifact” used to generate derived claims.
- Treat LLM outputs as “proposed claims” requiring explicit acceptance, OR accept automatically but mark provenance and replayability.

Alternatives rejected as core
- “Auto-summarize everything” with non-pinned models or variable decoding (breaks determinism).
- Opaque embeddings-only extraction (not inspectable).

## 3) Linking

Deterministic linking
- Exact match on normalized identifiers (casefold, Unicode normalization, slugging).
- Symbol tables from code (fully qualified names, file paths).
- Repo graph edges: imports, dependencies, references.

Probabilistic linking (optional)
- Embedding similarity
  - Pros: Finds “related” items across vocab mismatch.
  - Cons: Requires model + numerical stability; must store vectors and scores; still explainable if logged.

Typed links
- Store link type, rule id, evidence snippet (or pointer), confidence (rule-based).

Rejected as default
- Fully automatic “related notes” without explanation.

## 4) Indexing and Search

Hybrid search
- BM25 / inverted index for exact terms
  - Pros: Deterministic; fast; excellent for code identifiers.
- Embeddings for semantic recall
  - Pros: Captures paraphrases; cross-language synonyms.
  - Cons: Requires local model; storage overhead.
- Graph-aware rerank
  - Pros: Uses neighborhood signals, recency, project scope.
  - Cons: Complexity; must remain deterministic (fixed weights, stable tie-break).

Local vector store choices (file-backed)
- Store vectors as plain binary blobs alongside JSON manifests, OR as JSONL (larger).
- Use an embedded index format only for derived caches, with a guaranteed reproducible rebuild and an exported plain-text manifest.

Query explanation
- For each result: term hits, BM25 score, embedding score, graph boosts, tie-break keys, top matching snippets.

Rejected as primary
- Proprietary vector DBs as the source of truth (lock-in).

## 5) Visualization

Patterns
- Neighborhood view (1-2 hops) with filters by link type.
- Breadcrumb trails (path from A to B).
- Timeline view for decisions/events.
- “Why connected?” panel for any edge.

MVP UI options
- CLI + TUI
  - Pros: Local-first, fast to ship, engineer-friendly.
  - Cons: Graph visualization limited.
- Local web UI (localhost server)
  - Pros: Better graph viz, richer interactions.
  - Cons: More components; must keep offline and local.

Exports
- GraphML, JSON, DOT for interoperability.

## 6) Automation

Deterministic jobs
- Nightly rebuild, changed-files digest, stale-link detector, extraction regression report.

Human-in-the-loop
- Review queue for low-confidence links/claims.
- “Accept/reject” stored as plain-text decisions.

Policy as config
- YAML/JSON configs defining triggers, scopes, thresholds, outputs.

Rejected as default
- Always-on background agents that mutate the graph without logs.

# Specification + Plan

## 1. Executive Summary

A local-first Personal Knowledge Graph (PKG) for engineers that ingests plain-text notes and code, deterministically extracts entities and claims, creates explainable typed links, builds hybrid search indexes, and provides CLI-first navigation with optional local UI. The source of truth is a plain-text repository; all derived artifacts are reproducible, diffable, and re-runnable from inputs plus pinned configuration. Optional LLM-assisted extraction is supported only as a replayable, fully logged pipeline step.

## 2. Goals

1) Local-first, offline-capable PKG for engineers.
2) Plain-text store as source of truth; derived artifacts are rebuildable.
3) Deterministic extraction, linking, and indexing.
4) Inspectable provenance for every derived fact and link.
5) Fast hybrid search (keyword + optional semantic) and graph navigation.
6) Extensible ingestion and extraction via plugins without compromising determinism.

## 3. Non-Goals

1) Cloud-first operation or mandatory sync services.
2) Replacing an engineer’s editor, VCS, or note-taking tool.
3) “Magic” auto-tagging that cannot be explained or reproduced.
4) Proprietary databases as primary storage (embedded caches permitted only as rebuildable accelerators).
5) Automatic deletion or rewriting of user-authored notes.
6) Fully autonomous agents that make irreversible changes without audit logs.

## 4. User Stories (engineer-centric)

1) As an engineer, I can point the PKG at a workspace folder and it indexes Markdown notes and Git repos without internet access.
2) As an engineer, I can search for a symbol name and find where it is defined, referenced, and discussed in notes.
3) As an engineer, I can open a “node” and see the exact sources and snippets that created each claim.
4) As an engineer, I can see a neighborhood graph of a concept (1-2 hops) filtered by link types.
5) As an engineer, I can capture an ADR note template and have decisions extracted into a decision index deterministically.
6) As an engineer, I can ingest debugging logs and extract error signatures, stack traces, and implicated modules.
7) As an engineer, I can run “rebuild” and get identical derived outputs given the same inputs and config.
8) As an engineer, I can diff two runs and see exactly what changed (inputs, pipeline versions, derived artifacts).
9) As an engineer, I can maintain separate profiles (work/personal) with no cross-contamination.
10) As an engineer, I can export a subgraph (project-scoped) to JSON/DOT/GraphML for sharing.
11) As an engineer, I can add a custom deterministic extraction rule (regex/AST mapping) as a plugin.
12) As an engineer, I can request optional semantic search and still keep outputs reproducible and explainable.
13) As an engineer, I can ask “why is note A linked to note B?” and see the rule and evidence.
14) As an engineer, I can run a daily digest of changes since yesterday and store it as a plain-text artifact.

## 5. Functional Requirements (numbered; testable)

FR-1 Ingestion
1. FR-1.1 The system SHALL ingest files from one or more configured root directories.
2. FR-1.2 The system SHALL support Markdown and plain text on day 1.
3. FR-1.3 The system SHALL support Git repo ingestion on day 1 by scanning working trees and recording commit metadata if available.
4. FR-1.4 The system SHALL implement incremental ingestion using content hashing (sha256) for each ingested file.
5. FR-1.5 The system SHALL record a per-run ingestion manifest listing each file path, size, mtime, content hash, and parse status.

FR-2 Normalization
6. FR-2.1 The system SHALL normalize text using a specified Unicode normalization form (configurable, default NFC).
7. FR-2.2 The system SHALL canonicalize paths (OS-independent) using a defined path normalization policy (POSIX-style internal paths).

FR-3 Extraction
8. FR-3.1 The system SHALL extract entities from Markdown frontmatter and headings deterministically.
9. FR-3.2 The system SHALL extract code entities (files, modules, symbols) using deterministic parsers or deterministic fallback heuristics.
10. FR-3.3 The system SHALL output extracted claims as plain-text JSON files with stable IDs.
11. FR-3.4 The system SHALL store provenance for each claim: source file, byte ranges or line ranges, extraction rule id, pipeline version, and input hash.
12. FR-3.5 The system SHALL support a plugin mechanism for adding extraction rules without modifying core code.

FR-4 Linking
13. FR-4.1 The system SHALL create deterministic links using configured link rules (exact match, normalized match, symbol reference match).
14. FR-4.2 The system SHALL store each link as a plain-text artifact containing: from_id, to_id, type, rule_id, evidence pointers, and confidence.
15. FR-4.3 The system SHALL support backlinks (either precomputed artifacts or deterministic on-demand computation) with identical results.

FR-5 Indexing and Search
16. FR-5.1 The system SHALL provide keyword search over all ingested text and extracted entities/claims.
17. FR-5.2 The system SHALL provide hybrid search combining keyword and optional semantic scores with deterministic ranking.
18. FR-5.3 The system SHALL provide an explanation object per result including scoring components and evidence snippets.
19. FR-5.4 The system SHALL provide graph traversal queries: neighbors, paths (bounded length), and “why connected”.

FR-6 Interfaces
20. FR-6.1 The system SHALL provide a CLI to run: ingest, extract, link, index, query, and rebuild.
21. FR-6.2 The system SHALL provide machine-readable outputs (JSON) for query responses for integration with other tools.
22. FR-6.3 The system SHALL optionally provide a local web UI (localhost) without requiring internet access.

FR-7 Automation
23. FR-7.1 The system SHALL support scheduled jobs defined in plain-text config.
24. FR-7.2 The system SHALL produce job outputs as stored artifacts in the repository (digests, reports).
25. FR-7.3 The system SHALL support a review queue for “proposed” links/claims with accept/reject decisions stored as plain text.

FR-8 Optional LLM Step (reproducible)
26. FR-8.1 If enabled, the system SHALL run LLM extraction with temperature=0 and pinned model identifier.
27. FR-8.2 The system SHALL store prompts, model identifiers, inputs, and outputs as replay logs.
28. FR-8.3 The system SHALL mark LLM-derived artifacts with provenance and allow replays producing identical outputs given the same model/toolchain.

## 6. Non-Functional Requirements

NFR-1 Determinism
- NFR-1.1 Given identical inputs, config, and pipeline version, derived artifacts SHALL be byte-for-byte identical.
- NFR-1.2 All sorts SHALL use stable tie-break keys (stable_id, path, then hash) to ensure consistent ordering.

NFR-2 Performance targets (assumptions: SSD, modern laptop CPU)
- Dataset assumptions:
  - Small: 10k documents, 1-5 repos, 100k entities/claims.
  - Medium: 100k documents, 20 repos, 1M entities/claims.
  - Large: 1M documents, 200 repos, 10M entities/claims (stretch).
- NFR-2.1 Keyword search p50/p95:
  - Small: p50 < 50ms, p95 < 200ms
  - Medium: p50 < 150ms, p95 < 600ms
  - Large: p50 < 400ms, p95 < 1500ms
- NFR-2.2 Incremental ingest+extract for 100 changed files SHALL complete in <10s (small) and <60s (medium).

NFR-3 Portability
- NFR-3.1 The plain-text store SHALL be readable/editable without the tool.
- NFR-3.2 The tool SHALL run on at least Linux and macOS for MVP; Windows support is a planned milestone.

NFR-4 Privacy
- NFR-4.1 No network access SHALL be required for core operation.
- NFR-4.2 All exports SHALL support redaction rules.

NFR-5 Reliability
- NFR-5.1 Crashes SHALL not corrupt the source store; partial derived outputs MUST be recoverable via rebuild.

## 7. Data Model

### 7.1 Core Concepts

Entity
- A canonical node representing a thing: symbol, file, concept, person, project, decision, error signature.

Claim (Fact)
- An atomic assertion derived from a source with provenance.
- May be typed (decision, definition, observation, task, relationship assertion).

Source
- A reference to an ingested artifact (file), including stable content hash and parse metadata.

Link
- A directed edge between two entities or claims with a type and provenance.

Indexes
- Derived structures for search and traversal. Must be rebuildable.

### 7.2 Stable IDs

Stable ID rules (deterministic)
- entity_id = "ent_" + sha256(namespace + ":" + canonical_key)
- claim_id = "clm_" + sha256(source_hash + ":" + extractor_rule_id + ":" + canonical_claim_text_or_struct)
- link_id = "lnk_" + sha256(from_id + ":" + to_id + ":" + type + ":" + rule_id + ":" + evidence_ptrs)

### 7.3 Required Fields

Entity fields
- id, type, name, canonical_key
- aliases (optional)
- created_at (derived run timestamp), updated_at (derived run timestamp)
- provenance: created_by_rule, input_hash, pipeline_version
- refs: list of source pointers (file + range) where defined/mentioned

Claim fields
- id, type, subject_id (optional), predicate, object (string or structured)
- qualifiers: time_start, time_end, confidence (rule-based), status (proposed/accepted)
- provenance: source_file, source_hash, ranges, extractor_rule_id, pipeline_version, run_id

Source fields
- path, source_hash, size, mtime, parser_id, parse_status
- repo metadata if applicable: repo_root, commit_hash (if available), branch

Link fields
- id, from_id, to_id, type
- rule_id, confidence, evidence (source pointers), pipeline_version, run_id
- explanation: machine-readable reason payload (rule name, match tokens, similarity score if applicable)

Index manifest fields
- index_id, type (bm25, embeddings, graph)
- build_config_hash, pipeline_version, built_at, inputs_manifest_hash
- file pointers to index shards

## 8. Architecture

### 8.1 High-level components and boundaries

1) Ingestor
- Scans configured roots, detects changes, parses supported formats into normalized text and metadata.

2) Normalizer
- Canonicalizes text, paths, line endings, encodings.

3) Extractor
- Runs deterministic rule sets and optional AST extractors to produce entities and claims.

4) Linker
- Applies deterministic link rules; optionally runs semantic similarity linking (flagged and explainable).

5) Indexer
- Builds keyword and optional vector indexes; builds graph adjacency maps.

6) Query Engine
- Executes hybrid search and graph traversal; produces result explanations.

7) UI Layer
- CLI (required)
- Optional local UI (localhost server) and/or TUI

8) Automation Runner
- Scheduler and job execution; policies as config; stores outputs as artifacts.

### 8.2 Local storage layout (plain-text directory structure)

Proposed layout (single “PKG root”)
- pkg-root/
  - notes/                      (user-authored)
  - repos/                      (optional mirrors or pointers; not required)
  - inbox/                      (drop zone for imports)
  - config/
    - pkg.yaml
    - extractors/
    - link_rules/
    - profiles/
  - .pkg/
    - runs/
      - 2026-02-05T19-00-00Z_run_<hash>/
        - ingest-manifest.json
        - normalize-manifest.json
        - extract-manifest.json
        - link-manifest.json
        - index-manifest.json
        - replay-log.jsonl
    - sources/
      - <source_hash>.json       (source metadata)
    - entities/
      - ent_<prefix>/
        - ent_<id>.json
    - claims/
      - clm_<prefix>/
        - clm_<id>.json
    - links/
      - lnk_<prefix>/
        - lnk_<id>.json
    - indexes/
      - bm25/
        - manifest.json
        - shards/
      - vectors/
        - manifest.json
        - shards/
      - graph/
        - adjacency.jsonl
        - reverse_adjacency.jsonl
    - cache/                     (rebuildable, may be cleared)
  - exports/
    - subgraphs/
    - reports/

Notes
- User-authored content stays outside .pkg/.
- .pkg/ is derived and reproducible; safe to rebuild.
- All manifests and artifacts are plain-text JSON/JSONL for diffability.

### 8.3 Pipeline stages

1) ingest
- Enumerate files, compute hashes, parse to normalized intermediate text.

2) normalize
- Normalize encoding, line endings, path keys, and create canonical text representations.

3) extract
- Produce entities and claims.

4) link
- Produce typed links with evidence and explanations.

5) index
- Build keyword index, optional vectors, and graph adjacency.

6) serve
- CLI query and optional UI query endpoints reading derived artifacts.

## 9. Determinism Strategy

1) Hash everything
- Content hashes for sources (sha256 over bytes).
- Config hash (sha256 over canonicalized config files).
- Pipeline version hash (git commit hash of tool, or release version string).
- Run ID = sha256(inputs_manifest_hash + config_hash + pipeline_version).

2) Stable IDs
- Entity/claim/link IDs computed from canonical keys as defined in Data Model.
- Canonicalization rules are fixed and versioned.

3) Idempotency rules
- Re-running a stage with same inputs MUST produce identical outputs.
- Stage outputs write to a temporary folder then atomically move into place.

4) Stable sorting and numeric determinism
- Always sort by stable keys; never rely on map iteration order.
- If using floating scores (embeddings), store computed scores and apply deterministic rounding (e.g., round to 1e-6) before ranking.
- Tie-break order: final_score desc, bm25 desc, semantic desc, graph_boost desc, stable_id asc.

5) Replay logs
- Every run stores replay-log.jsonl:
  - stage start/end, inputs hashes, outputs hashes, rule versions.
- A “replay” command re-executes using recorded manifests.

6) Handling optional LLM without breaking reproducibility

Core rule: LLM outputs are treated as recorded deterministic artifacts, not as ephemeral computations.
- Requirements:
  - Temperature=0
  - Model identifier pinned (and ideally local model)
  - Prompt template versioned and stored
  - Inputs canonicalized and hashed
  - Output stored verbatim as an artifact and referenced by derived claims
- Two modes:
  - Mode A (conservative): LLM emits “proposed claims” requiring accept/reject.
  - Mode B (aggressive): LLM claims auto-accepted but clearly flagged by provenance.
- Alternative rejected:
  - Calling a hosted model without a stable model version guarantee or without storing full transcripts (cannot replay).

## 10. Search & Retrieval Design

### 10.1 Hybrid ranking approach

Components
- Keyword score: BM25 on:
  - note bodies
  - entity names/aliases
  - claim predicate/object text
  - code symbol tables
- Semantic score (optional): cosine similarity between query embedding and document/entity embeddings.
- Graph boosts (deterministic): small additive weights for:
  - same project scope
  - direct neighbors to high-scoring nodes
  - recency buckets (deterministic from timestamps)

Ranking formula (example, deterministic weights in config)
- score = w_kw * bm25 + w_sem * sem + w_graph * graph_boost
- All weights fixed per profile; stored in config.

Alternatives and why rejected
- ML rerankers as default: difficult to keep deterministic and explainable.
- Pure embedding search: poor for exact code identifiers and diffability.

### 10.2 Explainability (“why”)

For each result, return:
- matched_terms: list of tokens and fields (title/body/entity/claim)
- bm25_score and top contributing fields
- semantic_score (if enabled) and embedding model id
- graph_boost explanation (which edges contributed)
- evidence snippets with source pointers and line ranges
- final tie-break keys

## 11. Graph Navigation & Visualization

### 11.1 UI concepts and minimum viable screens

Minimum viable (CLI)
1) Node view
- Shows entity fields, key claims, sources, incoming/outgoing links.
2) Neighborhood
- 1-hop and 2-hop expansions with filters by link type.
3) Why-connected
- For a chosen edge: rule id, evidence pointers, match tokens/scores.
4) Path finder (bounded)
- Finds shortest paths up to N hops using typed edges.

Optional local UI (localhost)
- Search page with filters and result explanations.
- Graph neighborhood visualization with collapsible groups.
- Node detail panel with provenance.
- Timeline view for decisions/events.

Alternatives and why rejected
- Heavyweight desktop app as MVP: more surface area; slower iteration.
- Cloud-hosted UI: violates local-first expectation.

### 11.2 Export formats

- DOT: quick visualization and tooling compatibility.
- GraphML: interop with graph tools.
- JSON: programmatic use and stable diffing.

## 12. Automation Framework

### 12.1 Job scheduler model

- Jobs defined in config/jobs.yaml
- Triggers:
  - schedule (cron-like)
  - on-change (when ingest detects changes)
  - manual
- Each job runs a pipeline stage or query and writes outputs to exports/reports/.

### 12.2 Policies as config

- Deterministic policy rules:
  - which directories to include
  - which extractors/link rules enabled
  - thresholds (confidence)
  - redaction policy for exports

### 12.3 Human-in-the-loop review queue

- Proposed claims/links stored under .pkg/review/
- Decisions stored as:
  - accept/<id>.json
  - reject/<id>.json
- Accepted items become part of stable graph; rejected are retained for audit.

Alternatives and why rejected
- Auto-accept everything: undermines trust for noisy sources (logs, PDFs).
- GUI-only review: excludes CLI-first workflows.

## 13. Security & Privacy

1) Offline by default
- No network calls required.

2) Secrets and redaction
- Configurable redaction regexes (API keys, tokens, emails).
- Redaction applied to:
  - exports
  - optional LLM transcripts
  - search snippet rendering (optional)

3) Encryption at rest (optional)
- Option A: full-store encryption
  - Rejected for default because it harms diffability and interoperability.
- Option B: encrypt only sensitive subtrees (exports, profiles)
  - Preferred: keep source-of-truth text readable; protect shareable artifacts.

4) Multi-profile separation
- Separate pkg roots or separate profile directories with explicit “no cross-profile links” policy.

## 14. Testing Strategy

1) Unit tests
- Canonicalization functions (unicode, path normalization).
- Stable ID generation.
- Extractor rule correctness on fixtures.

2) Integration tests
- End-to-end pipeline on a small fixture repository producing fixed outputs.

3) Golden (snapshot) tests for determinism
- Given fixture inputs + config + pipeline version, outputs MUST match golden files byte-for-byte.
- Include:
  - entities
  - claims
  - links
  - index manifests
  - query explanations for fixed queries

4) Regression suite for extractor/linker changes
- Any change to rules requires updating a versioned “rule pack”.
- Run diff report:
  - counts of entities/claims/links changed
  - which rules caused changes
  - top changed nodes by degree

5) Performance tests
- Synthetic corpus generator to hit 10k/100k/1M scale assumptions.
- Measure ingest, extract, query p50/p95.

## 15. Milestones / Phased Plan

### Phase 0: repo + scaffolding
- Initialize repo with:
  - CLI skeleton
  - config loader
  - canonicalization utilities
  - run manifest structure
- Deliverable: “pkg init”, “pkg version”, “pkg config validate”

### Phase 1: ingestion + hashing
- Directory scan + hashing + ingest manifest
- Markdown/plain text parser (frontmatter + headings)
- Deliverable: “pkg ingest” produces .pkg/sources and run manifest

### Phase 2: deterministic extraction
- Extract entities from:
  - note titles/headings/frontmatter
  - basic code file entities (file/module)
- Deterministic claim extraction from ADR templates and checklist patterns
- Plugin interface for extractors
- Deliverable: “pkg extract” creates entity/claim artifacts

### Phase 3: linking
- Deterministic link rules:
  - mentions (normalized string match)
  - defines (frontmatter-based)
  - code refs (path/module linkage)
- “why” explanations for each link
- Deliverable: “pkg link” creates link artifacts and adjacency JSONL

### Phase 4: hybrid search
- Build BM25 index (derived, rebuildable) + query explanation
- Optional local embeddings pipeline (behind a feature flag)
- Deterministic hybrid ranking and tie-break
- Deliverable: “pkg query” returns JSON with explanations

### Phase 5: UI graph nav
- CLI UX polish (node view, neighbors, why-connected, path)
- Optional local web UI (read-only first)
- Deliverable: minimal graph navigation and search UI

### Phase 6: automation + plugins
- Job scheduler and policy config
- Review queue for proposed links/claims
- Plugin registry (extractors, linkers, importers)
- Deliverable: scheduled digests, stale-link checks, plugin SDK docs

## 16. Risks and Mitigations

1) PDF/DOCX ingestion quality
- Risk: nondeterministic parsing across libraries and versions.
- Mitigation: pin parser versions; store extracted text as an intermediate artifact with hash; treat that intermediate as the deterministic input for later stages.

2) Numeric instability in embeddings
- Risk: platform differences cause tiny score changes affecting rank.
- Mitigation: store embeddings and similarity scores; apply deterministic rounding; stable tie-break; allow “embeddings disabled” core mode.

3) Rule explosion / maintainability
- Risk: too many heuristics become fragile.
- Mitigation: versioned “rule packs”; require tests per rule; keep extraction schema small and extensible.

4) Performance at scale
- Risk: pure-file adjacency and indexes become slow at 1M+ nodes.
- Mitigation: allow rebuildable embedded caches (still reproducible) with manifest exports; shard artifacts by prefix; incremental indexing.

5) User trust erosion from noisy links
- Risk: too many weak “related_to” links.
- Mitigation: conservative defaults; confidence thresholds; review queue; typed links prioritized.

6) Cross-platform file watching
- Risk: missed events or inconsistent behavior.
- Mitigation: watcher is optional; always support periodic rescan; ingest correctness based on hashes.

## 17. Open Questions

1) Exact day-1 formats beyond Markdown/plain text and Git repos.
2) Required code languages and depth of AST extraction.
3) Whether semantic search is required in MVP or optional later.
4) Preferred interface: CLI-only vs CLI + local web UI.
5) Encryption at rest requirements and acceptable impact on diffability.
6) Required latency targets and expected dataset sizes.
7) Contradiction handling: how explicit should it be in the model/UI.

## 18. Appendix

### 18.1 Example configs

pkg.yaml
---
pkg_root: "."
profiles:
  default:
    include_paths:
      - "notes"
      - "repos"
    exclude_globs:
      - "**/node_modules/**"
      - "**/.git/**"
    normalization:
      unicode: "NFC"
      line_endings: "LF"
      path_style: "posix"
    extraction:
      rule_packs:
        - "config/extractors/core.yaml"
      llm:
        enabled: false
    linking:
      rule_packs:
        - "config/link_rules/core.yaml"
    search:
      keyword:
        enabled: true
      semantic:
        enabled: false
      ranking:
        w_kw: 1.0
        w_sem: 0.3
        w_graph: 0.1
        score_rounding: 0.000001
---

jobs.yaml
---
jobs:
  daily_digest:
    trigger:
      schedule: "0 7 * * *"
    action:
      type: "report.changed_since"
      args:
        since: "24h"
    output:
      path: "exports/reports/daily-digest.md"
  stale_links:
    trigger:
      schedule: "0 2 * * 0"
    action:
      type: "report.stale_links"
      args:
        max_age_days: 30
    output:
      path: "exports/reports/stale-links.json"
---

### 18.2 Example storage layouts (concrete artifacts)

Example: run manifest
---
{
  "run_id": "run_8f3c...d1",
  "pipeline_version": "v0.1.0",
  "config_hash": "cfg_12ab...9e",
  "started_at": "2026-02-05T19:00:00Z",
  "stages": [
    {
      "name": "ingest",
      "inputs_hash": "in_...",
      "outputs_hash": "out_...",
      "artifact": ".pkg/runs/2026-02-05T19-00-00Z_run_8f3c/ingest-manifest.json"
    }
  ]
}
---

Example: entity file
---
{
  "id": "ent_3a9b...f2",
  "type": "code_symbol",
  "name": "SearchResults",
  "canonical_key": "repo:myapp/src/components/SearchResults.tsx#SearchResults",
  "aliases": ["SearchResultsComponent"],
  "provenance": {
    "created_by_rule": "ast.ts.react_component",
    "input_hash": "sha256:aa12...ff",
    "pipeline_version": "v0.1.0",
    "run_id": "run_8f3c...d1"
  },
  "refs": [
    {
      "source_path": "repos/myapp/src/components/SearchResults.tsx",
      "source_hash": "sha256:aa12...ff",
      "range": { "start_line": 1, "end_line": 42 }
    }
  ]
}
---

Example: claim file
---
{
  "id": "clm_91d2...0a",
  "type": "decision",
  "subject_id": "ent_77c1...b8",
  "predicate": "decided",
  "object": {
    "decision": "Use sha256 content hashes as the ingestion change detector",
    "context": "Need deterministic incremental updates across platforms",
    "consequences": ["Full file read required on first scan"]
  },
  "qualifiers": {
    "status": "accepted",
    "confidence": 1.0
  },
  "provenance": {
    "source_file": "notes/adr/0003-hashing.md",
    "source_hash": "sha256:bb34...aa",
    "ranges": [{ "start_line": 1, "end_line": 60 }],
    "extractor_rule_id": "md.adr.v1",
    "pipeline_version": "v0.1.0",
    "run_id": "run_8f3c...d1"
  }
}
---

Example: link file
---
{
  "id": "lnk_5e10...7c",
  "from_id": "ent_3a9b...f2",
  "to_id": "clm_91d2...0a",
  "type": "mentions",
  "rule_id": "link.mentions.normalized_exact",
  "confidence": 0.9,
  "evidence": [
    {
      "source_path": "notes/adr/0003-hashing.md",
      "source_hash": "sha256:bb34...aa",
      "range": { "start_line": 10, "end_line": 12 }
    }
  ],
  "explanation": {
    "match": "sha256",
    "normalization": "casefold+unicode_nfc",
    "tokens": ["sha256"]
  },
  "pipeline_version": "v0.1.0",
  "run_id": "run_8f3c...d1"
}
---

### 18.3 Example index manifest

---
{
  "index_id": "bm25_default",
  "type": "bm25",
  "build_config_hash": "cfg_12ab...9e",
  "pipeline_version": "v0.1.0",
  "built_at": "2026-02-05T19:02:10Z",
  "inputs_manifest_hash": "in_77aa...11",
  "shards": [
    { "path": ".pkg/indexes/bm25/shards/0000.jsonl", "hash": "sha256:cc..." },
    { "path": ".pkg/indexes/bm25/shards/0001.jsonl", "hash": "sha256:dd..." }
  ],
  "explainability": {
    "stores_term_stats": true,
    "stores_field_weights": true
  }
}
---
