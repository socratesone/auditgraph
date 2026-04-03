# Feature Specification: Git Provenance Ingestion

**Feature Branch**: `020-git-provenance-ingestion`
**Created**: 2026-04-02
**Status**: Draft
**Input**: User description: "Add deterministic local Git provenance ingestion to AuditGraph so that repository history becomes queryable as compact, high-value provenance relationships in the graph"

## Clarifications

### Session 2026-04-02

- Q: Which Git library should be used? → Open design decision. Implementation must use local repository only, no hosted-service dependency.
- Q: Should commit messages be stored in full or truncated? → Commit subject/summary only. Full message body is not required for v1.
- Q: How should identity normalization work? → Repo-local only. No remote resolution. Normalization rules (if any) are implementation-defined and must be deterministic.
- Q: What constitutes a unique AuthorIdentity? → Email is the canonical identity key. Each unique email produces one AuthorIdentity node. Name variants observed for the same email are stored as aliases on that node. This reduces duplicate identity nodes while preserving all observed name forms.
- Q: What are the bounded processing defaults? → Tiered ingestion with commit budget of 1,000. Tier 1 (always ingested, no limit): tagged commits, root commits, merge branch points, branch heads. Tier 2 (budget-filled): scored by `files_changed + (lines_changed / 400)`, sorted descending; always includes most recent and earliest commit for diff-ability. Hot/cold path lists control priority: hot paths (`git_provenance.hot_paths`) promote any touching commit to Tier 1; cold paths (`git_provenance.cold_paths`, default: `*.lock`, `*-lock.json`, `*.generated.*`) contribute 0 to scoring. Tags are first-class nodes always ingested with metadata (name, type, target commit, tagger identity if annotated).
- Q: How does the new stage integrate with replay log and observability? → Follows existing conventions: writes one replay log entry per run with `stage: "git_provenance"`, `duration_ms`, `inputs_hash` (derived from HEAD commit + config), `outputs_hash` (derived from produced artifacts). Writes `git-provenance-manifest.json` following existing manifest pattern.
- Q: Should this be a new pipeline stage or part of extract? → Dedicated new pipeline stage (`run_git_provenance`) inserted after `run_ingest` in the rebuild chain. Gets its own manifest and replay log entry. Creates new node types (Commit, AuthorIdentity, Repository) and links them to existing file entity IDs produced by `run_ingest`. Scoped to files matching `include_paths`. Skipped during `run_import`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest Git commit history for a repository (Priority: P1)

As a developer, I can run AuditGraph ingestion on a repository and have Git commit metadata automatically captured as graph nodes, so that repository history becomes queryable through the knowledge graph.

**Why this priority**: Without commit ingestion, no other Git provenance features are possible. This is the foundational data collection step.

**Independent Test**: Ingest a fixture Git repository with known commits, verify commit nodes are created with correct metadata (hash, author, timestamp, subject, parent references).

**Acceptance Scenarios**:

1. **Given** a local Git repository with commits, **When** the Git provenance ingestion runs, **Then** commit nodes are created with hash, author name, author email, authored timestamp, and commit subject.
2. **Given** a commit with distinct author and committer identities, **When** ingestion completes, **Then** both identities are captured if retained by implementation.
3. **Given** the same repository state and same AuditGraph configuration, **When** ingestion runs twice, **Then** the output is identical (deterministic).
4. **Given** a repository exceeding configured processing limits, **When** ingestion runs, **Then** processing stops at the configured bound and produces deterministic output.

---

### User Story 2 - File-to-commit provenance relationships (Priority: P1)

As a developer, I can see which commits touched a given file and which files a given commit touched, so that I can trace code provenance through history.

**Why this priority**: File-commit relationships are the primary value of Git provenance for developers. Without them, commit nodes are isolated metadata.

**Independent Test**: Ingest a fixture repository where known files are touched by known commits, verify file-touch relationships are materialized with correct directionality.

**Acceptance Scenarios**:

1. **Given** a commit that modifies files A and B, **When** ingestion completes, **Then** the commit node has "touches" relationships to both file nodes.
2. **Given** file A modified by commits C1, C2, and C3, **When** a user queries "what commits touched file A", **Then** all three commits are returned.
3. **Given** commit C1 touching files A and B, **When** a user queries "what files did commit C1 touch", **Then** both files are returned.

---

### User Story 3 - Author identity capture and file-author provenance (Priority: P1)

As a developer, I can see which authors have touched a file and which files an author has worked on, so that I can identify code ownership and expertise.

**Why this priority**: Author provenance answers "who changed this?" which is one of the most common developer questions.

**Independent Test**: Ingest a fixture repository with multiple authors, verify author identity nodes are created and linked to commits.

**Acceptance Scenarios**:

1. **Given** commits from multiple authors, **When** ingestion completes, **Then** distinct AuthorIdentity nodes are created for each unique author email.
2. **Given** an author who committed multiple times, **When** a user queries "who changed file X", **Then** the author appears in results with their identity metadata.
3. **Given** author identities are repo-local only, **When** the same email appears with different names, **Then** a single identity node exists for that email with all observed name variants stored as aliases.

---

### User Story 4 - Commit parent and merge structure (Priority: P2)

As a developer, I can traverse commit parent relationships and identify merge commits, so that I can understand the branching and integration history of the codebase.

**Why this priority**: Parent/merge structure enables history-aware queries but is less frequently needed than basic file/author provenance.

**Independent Test**: Ingest a fixture repository with merge commits, verify parent relationships and merge indicators are captured.

**Acceptance Scenarios**:

1. **Given** a linear commit history A -> B -> C, **When** ingestion completes, **Then** each commit has a parent relationship to its predecessor.
2. **Given** a merge commit M with parents P1 and P2, **When** ingestion completes, **Then** M has parent relationships to both P1 and P2 and is identifiable as a merge commit.
3. **Given** merge history, **When** a user queries merge context for a file, **Then** the system can trace through merge commits associated with that file's history.

---

### User Story 5 - Branch/ref context capture (Priority: P2)

As a developer, I can see branch or ref context associated with commits where deterministically available, so that I can understand the development context of changes.

**Why this priority**: Branch context adds useful metadata but is inherently ambiguous in Git (commits can belong to multiple branches). Correct omission is more valuable than speculative attribution.

**Independent Test**: Ingest a fixture repository with tagged refs, verify ref context is captured where unambiguous.

**Acceptance Scenarios**:

1. **Given** a commit reachable from a named ref, **When** ref context is deterministically available at ingestion time, **Then** the commit is associated with that ref.
2. **Given** a commit reachable from multiple branches, **When** ref attribution is ambiguous, **Then** the system omits ref context rather than guessing.

---

### User Story 6 - File lineage detection for renames and moves (Priority: P2)

As a developer, I can see file rename/move lineage so that provenance survives file reorganization.

**Why this priority**: Renames break naive file-path tracking. Lineage detection preserves provenance continuity, but is heuristic in nature and less critical than exact commit/file/author provenance.

**Independent Test**: Ingest a fixture repository with a known file rename, verify lineage relationship is created with confidence metadata.

**Acceptance Scenarios**:

1. **Given** a commit that renames file A to file B, **When** lineage heuristics detect the rename, **Then** a lineage relationship connects file B to file A.
2. **Given** a delete-then-add pattern that strongly indicates lineage, **When** heuristics detect the pattern, **Then** a lineage relationship is created with appropriate confidence metadata.
3. **Given** a lineage relationship established by heuristic, **When** the relationship is queried, **Then** confidence metadata is included in the result.

---

### User Story 7 - Provenance queries via CLI (Priority: P1)

As a developer, I can query Git provenance through the AuditGraph CLI to answer practical questions about code history.

**Why this priority**: CLI is the primary interface for developers. Without query exposure, the ingested data has no user-facing value.

**Independent Test**: After ingesting a fixture repository, run CLI provenance queries and verify correct results.

**Acceptance Scenarios**:

1. **Given** ingested Git provenance, **When** the user runs a "who changed this file" query, **Then** the CLI returns author identities with timestamps.
2. **Given** ingested Git provenance, **When** the user runs a "what commits touched this file" query, **Then** the CLI returns commit metadata.
3. **Given** ingested Git provenance, **When** the user runs a "when was this file introduced" query, **Then** the CLI returns the earliest commit touching that file.

---

### User Story 8 - Provenance queries via MCP (Priority: P2)

As an AI agent, I can discover and invoke Git provenance queries as MCP tools, so that automated workflows can leverage code history.

**Why this priority**: MCP support extends value to agent workflows but depends on CLI query logic being implemented first.

**Independent Test**: Query the MCP tool manifest, verify Git provenance tools are listed with correct schemas, invoke a tool and verify correct results.

**Acceptance Scenarios**:

1. **Given** the MCP server is running, **When** an agent lists available tools, **Then** Git provenance query tools appear in the manifest.
2. **Given** ingested Git provenance, **When** an agent invokes a provenance tool, **Then** the response matches the equivalent CLI query result.

---

### Edge Cases

- What happens when the repository has no commits? System must handle gracefully with empty provenance output.
- What happens when a commit has no parent (root commit)? Must be handled as a valid commit with no parent relationship.
- What happens when Git history contains non-UTF-8 author names or commit messages? Must handle encoding gracefully without crashing.
- What happens when a repository has an extremely large history (100k+ commits)? Bounded processing limits must apply deterministically.
- What happens when .git directory is missing or corrupted? Must fail gracefully with a machine-readable error.
- What happens when a file is deleted and never re-added? The file node should still exist with its historical commit relationships.
- What happens when the same file path is deleted and re-created (not a rename)? These are distinct lineage chains; no lineage relationship should be inferred.

## Constraints

- **Local-first**: Core functionality must not depend on hosted services.
- **Determinism**: Same repository state + same configuration = identical output.
- **Auditability**: Every graph artifact must trace to specific Git source facts.
- **Compact graph**: Summary provenance only; no raw patch text, blame text, or full message bodies in graph storage.
- **Bounded processing**: Must include configurable limits for pathological repositories.
- **Backward compatibility**: Existing entity types and pipeline stages must not be affected.
- **No remote identity resolution**: AuthorIdentity is repo-local only in v1.

## Out of Scope (v1)

- Raw patch text storage in graph
- Full blame text storage in graph
- PR/review/comment/discussion ingestion
- Symbol-level historical provenance
- Semantic diffing across revisions
- Remote identity resolution
- Hosted-service dependency for core behavior
- Cross-repository identity merging
- Real-time/streaming ingestion

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST ingest local Git history and materialize commit nodes in the graph with hash, parent hashes, author name, author email, authored timestamp, and commit subject.
- **FR-002**: System MUST capture committer name, email, and timestamp as non-null fields on the Commit node when the committer identity differs from the author identity.
- **FR-003**: System MUST materialize file-to-commit provenance relationships recording which files each commit touches.
- **FR-004**: System MUST capture repo-local author identities as graph nodes based on local Git metadata.
- **FR-005**: System MUST represent commit parent structure in the graph, including multi-parent (merge) commits.
- **FR-006**: System MUST materialize Ref/Branch nodes for named branches with head_sha at ingestion time. All branch HEADs MUST be included in the stage's `inputs_hash` so that branch advancement produces a new `run_id`, preserving determinism (FR-010). System SHOULD prefer omission over speculative attribution when ref-to-commit mapping is ambiguous.
- **FR-007**: System MUST detect file lineage for rename/move scenarios using deterministic heuristics, with confidence metadata where lineage is not exact.
- **FR-008**: System MUST expose provenance queries through the CLI: who changed a file, what commits touched a file, when a file was introduced, what authors touched a file. Merge history for a file is satisfied by the `git-history` command, which returns commit objects containing `is_merge` and `parent_shas` fields — callers filter for merge commits and traverse parent chains.
- **FR-009**: System MUST expose provenance queries through the MCP layer as discoverable tools.
- **FR-010**: System MUST produce deterministic output given the same repository state and configuration.
- **FR-011**: System MUST enforce bounded processing via tiered ingestion: Tier 1 structural anchors (tags, root, merge points, branch heads, hot-path commits) are always ingested; Tier 2 fills a configurable commit budget (default 1,000, named `max_tier2_commits`) scored by `files_changed + (lines_changed / 400)`, always including the most recent and earliest commits. Total ingested commits may exceed this budget when Tier 1 is large. Output must be deterministic when limits apply.
- **FR-012**: System MUST support configurable hot-path (`git_provenance.hot_paths`) and cold-path (`git_provenance.cold_paths`) glob lists. Hot-path commits are promoted to Tier 1. Cold paths contribute zero to Tier 2 scoring. Defaults: hot empty, cold `*.lock`, `*-lock.json`, `*.generated.*`.
- **FR-013**: System MUST ingest Git tags as first-class nodes with name, type (lightweight/annotated), target commit, and tagger identity/timestamp for annotated tags.
- **FR-014**: System MUST store summary-level provenance only; raw heavy payloads (patches, blame, full messages) MUST remain outside the graph.
- **FR-015**: System MUST generate deterministic identifiers for all provenance nodes and relationships using full SHA-256 hex digests, consistent with the existing `entity_id()` convention in `storage/hashing.py`.
- **FR-016**: System MUST handle gracefully: empty repositories, root commits, non-UTF-8 metadata, missing/corrupted .git directories, extremely large histories.
- **FR-017**: System MUST write a reverse index (`file_entity_id → [commit_ids]`) during ingestion to enable O(1) query lookup by file path.
- **FR-018**: When `git_provenance.enabled` is false, the stage MUST return `StageResult(status="skipped")` and the rebuild chain MUST continue without failure.

### Key Entities

- **Repository**: Represents the ingested Git repository. Key attributes: path, name.
- **Commit**: A single Git commit. Key attributes: hash, authored timestamp, commit subject, merge status.
- **File**: A file path touched by commits. Key attributes: path. Relates to existing entity types where file paths overlap with ingested source files.
- **AuthorIdentity**: An observed author identity from local Git metadata. Key attributes: email (canonical key), name aliases (list of all observed name variants for this email).
- **Tag**: A Git tag pointing to a commit. Key attributes: name, type (lightweight/annotated), tagger identity and timestamp (annotated only). Always ingested.
- **Ref/Branch**: A named branch or ref. Key attributes: name, type, head_sha. All branch HEADs included in `inputs_hash` for determinism.

### Core Relationships

Edge types use lowercase snake_case, consistent with existing link conventions (`relates_to`, `mentions`):

- Repository → Commit: `contains` (rule: `link.git_contains.v1`)
- Commit → File: `modifies` (rule: `link.git_modifies.v1`)
- Commit → Commit: `parent_of` (rule: `link.git_parent.v1`)
- Commit → AuthorIdentity: `authored_by` (rule: `link.git_authored_by.v1`)
- Tag → Commit: `tags` (rule: `link.git_tags.v1`)
- Commit → Ref/Branch: `on_branch` (rule: `link.git_branch.v1`)
- File → File: `succeeded_from` (rule: `link.git_lineage.v1`, with confidence metadata)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given a fixture repository with known commits, AuditGraph produces an identical provenance graph on repeated ingestion runs (determinism verified by hash comparison).
- **SC-002**: Users can answer "who changed this file" for any ingested file and receive correct author identities with timestamps.
- **SC-003**: Users can answer "what commits touched this file" for any ingested file and receive correct commit metadata.
- **SC-004**: Users can answer "when was this file introduced" for any ingested file and receive the correct earliest commit.
- **SC-005**: File rename/move lineage is detected for straightforward cases in fixture repositories with confidence metadata present.
- **SC-006**: Merge commits are identifiable through parent relationships in the graph.
- **SC-007**: Graph storage remains compact: no raw patch text, blame text, or full commit message bodies are stored as graph artifacts.
- **SC-008**: Processing of a repository with 10,000+ commits completes within bounded time and resource usage with deterministic output.
- **SC-009**: All provenance queries are available through both CLI and MCP interfaces.
- **SC-010**: Fixture-repo integration tests validate all acceptance scenarios deterministically.

## Assumptions

- Git is available on the system PATH where AuditGraph runs.
- The repository being ingested has a valid .git directory accessible locally.
- Author identity normalization beyond exact string matching is deferred to future versions unless configured.
- The existing pipeline stages (ingest, normalize, extract, link, index) continue to function unchanged.
- Exact edge label names, CLI command names, MCP tool schemas, and processing defaults are implementation decisions resolved during the planning phase.

## Open Design Decisions

All design decisions have been resolved during the planning phase. See [research.md](research.md) and [plan.md](plan.md) for details:

- Edge label naming: lowercase snake_case (`modifies`, `parent_of`, `authored_by`, etc.)
- File lineage confidence: three-tier (1.0 exact rename, 0.8 similarity >= 70%, 0.6 basename match)
- CLI commands: `git-provenance`, `git-who`, `git-log`, `git-introduced`, `git-history`
- MCP tools: `git_who_changed`, `git_commits_for_file`, `git_file_introduced`, `git_file_history`
- Git library: dulwich >= 0.22 (pure Python, no system deps)
