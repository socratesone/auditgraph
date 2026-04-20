# Feature Specification: Navigation Layer with Graph Search and Filters

**Feature Branch**: `022-navigation-layer`
**Created**: 2026-04-03
**Status**: Deferred (2026-04-06)
**Input**: User description: "Add a front-end navigation system for graph navigation under 022, including a search mechanism built from graph data to query and filter navigable graph data."

> **Deferral note (2026-04-06)**: Work on this spec is paused. During clarification it became clear that a meaningful navigation layer would need to either invent a sharded snapshot/server architecture (to preserve the project's local-first principle on a 100K+ entity graph) or relax the local-first constraint and back the UI with a live Neo4j server. Both directions are substantial new architecture surfaces, and the higher priority right now is validating that the existing CLI/local-first approach delivers value on a clean dataset. This spec is preserved as a research record — the user stories, acceptance scenarios, requirements, and the architectural exploration in the open clarifications below are still useful starting points if and when this work resumes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find and Focus a Node Quickly (Priority: P1)

A user opens the navigation interface, types a search term, sees a deterministic ranked list of matching graph nodes, selects one, and the graph view centers on that node and shows its details — all without manually expanding the graph step by step.

**Why this priority**: Search-first discovery is the primary missing capability today. Without it, exploring a workspace with thousands of nodes requires either knowing entity IDs in advance or expanding the graph hop-by-hop. This is the smallest standalone increment that delivers real navigation value.

**Independent Test**: Open the navigation view against a populated workspace, type a search term, select a result from the dropdown, and verify the graph view centers on that node with its details visible in a side panel.

**Acceptance Scenarios**:

1. **Given** a workspace with indexed entity names and aliases, **When** the user enters a search query, **Then** the system returns a deterministic, ranked list of matching nodes within 2 seconds.
2. **Given** visible search results, **When** the user selects a result, **Then** the graph view centers on that node, marks it as the active focus, and opens a details panel showing the node's name, type, and properties.
3. **Given** no matches for a query, **When** the user submits the query, **Then** the system shows an explicit "no results" state with suggestions to refine the search.
4. **Given** identical query input across two sessions, **When** the user submits the query, **Then** the result ordering is identical in both sessions (determinism guarantee).

---

### User Story 2 - Filter the Navigable Graph to Relevant Scope (Priority: P1)

A user applies structured filters (entity type, field predicates, edge type, confidence threshold) so the graph view, search results, and traversal expansion are constrained to the relevant subset of the graph.

**Why this priority**: Filtering is mandatory for practical navigation of real datasets. Without it, the graph view becomes unreadable on workspaces with tens of thousands of entities. This story is independent of Story 1 in that filters can also be applied without an active search query.

**Independent Test**: Apply a type filter (e.g., "commit only") and an edge-type filter (e.g., "authored_by only"), verify the graph view shows only matching nodes and edges, then run a search and verify the results respect the active filters.

**Acceptance Scenarios**:

1. **Given** a populated graph view, **When** the user applies a type filter, **Then** only entities of the selected type(s) remain visible in the graph and in search results.
2. **Given** a focused node with multiple edge types, **When** the user applies an edge-type filter, **Then** only matching edges and their connected nodes are shown when expanding neighbors.
3. **Given** an edge confidence threshold is set, **When** neighbors are expanded, **Then** only edges meeting or exceeding the threshold are followed.
4. **Given** a field-level predicate (e.g., "author equals X"), **When** the user applies it, **Then** only nodes whose field value matches the predicate are shown.
5. **Given** active filters, **When** the user clicks the reset control, **Then** all filters clear and the graph and results return to the unfiltered state.

---

### User Story 3 - Traverse with Context and Path Awareness (Priority: P2)

A user navigates the graph by clicking through related nodes while the system preserves traversal context: a breadcrumb path of visited nodes, the active focus, and the ability to backtrack to any earlier node in the path.

**Why this priority**: Context-preserving traversal turns isolated node hops into coherent exploration sessions. It is essential for reasoning about relationships but is secondary to the search/filter capability that enables initial discovery.

**Independent Test**: Search for a node, select it, expand a neighbor, expand a second-hop neighbor, then click an earlier breadcrumb segment and verify the focus returns to that node with the path correctly truncated.

**Acceptance Scenarios**:

1. **Given** a selected node, **When** the user expands a neighbor and selects it, **Then** the breadcrumb path appends the new node and the focus updates deterministically.
2. **Given** an existing breadcrumb path of three or more nodes, **When** the user clicks an earlier segment, **Then** the focus returns to that node and the path truncates to that point.
3. **Given** two nodes selected for relationship explanation, **When** the user requests the explanation, **Then** the system displays a valid connection path between them or shows an explicit "no path" outcome.
4. **Given** a traversal in progress, **When** the user clicks the reset control, **Then** the path, focus, and details panel all clear together.

---

### User Story 4 - Resume and Share Exploration State (Priority: P3)

A user saves the current navigation state (search query, active filters, focused node, breadcrumb path) so an exploration session can be resumed later or shared with another user.

**Why this priority**: Session reproducibility extends the project's core values of determinism and explainability into the UI workflow, but it is not blocking on initial usability of search, filter, and traversal.

**Independent Test**: Build up a navigation state (apply filters, search, select a result, expand a neighbor), trigger save, close and reopen the interface, and verify the same query, filters, focus, and breadcrumb path are restored.

**Acceptance Scenarios**:

1. **Given** an active navigation session, **When** the user saves state, **Then** the query text, all active filters, the focused node ID, and the breadcrumb path are persisted in a form the user can reload.
2. **Given** a previously saved state, **When** the user reloads it, **Then** the same query, filters, focus, and path are restored exactly.
3. **Given** a shared state and a recipient with access to the same workspace, **When** the recipient opens it, **Then** they see the same focus and context as the sender.

---

### Edge Cases

- **Empty workspace**: When the graph dataset has no entities or no built indexes, the UI shows an explicit empty-state message and disables search and filter controls until a workspace is loaded.
- **Very broad query**: When a query matches more results than can be shown at once, the UI paginates or progressively reveals results while keeping ordering stable across pages.
- **Stale focus reference**: When a previously focused or saved node no longer exists after a workspace refresh, the UI shows a stale-reference message and returns to a valid empty state.
- **Contradictory filters**: When the active filter combination yields zero results, the UI indicates that filters caused the empty state and provides a one-click reset.
- **Workspace switch mid-session**: When the user switches to a different workspace profile, all navigation state (query, filters, focus, path) clears.
- **Long node labels**: Node labels that exceed the visual node width are truncated with an ellipsis; the full label is available on hover or in the details panel.

## Constraints

- **Local-first**: The navigation layer MUST consume only the existing local `.pkg` storage and the existing query/traversal commands. No new external runtime dependencies (database, web service, cloud API) may be introduced.
- **Deterministic**: Identical input (query + filters) MUST produce identical output (result ordering, focus, traversal) across runs and across users on the same workspace.
- **Backwards-compatible**: The navigation layer MUST NOT modify the data model, the existing CLI commands, or the existing MCP tool surface. Any new commands or flags MUST be additive.
- **No write operations**: The navigation layer is read-only with respect to graph data. It MUST NOT mutate entities, links, or indexes.
- **Single-user, single-workspace per session**: Navigation operates against one workspace profile at a time.

## Out of Scope (v1)

- Multi-user collaboration features (concurrent editing, presence indicators, real-time sync).
- Authentication, authorization, or access control. The navigation layer assumes the user already has filesystem access to the workspace.
- Editing or annotating graph data via the UI. Navigation is read-only.
- Visual graph layout algorithms beyond a simple force-directed or hierarchical default. Custom layouts, manual node positioning, and saved layouts are deferred.
- Cross-workspace navigation. Each session targets one workspace.
- Mobile or touch-optimized layouts. Desktop browser only in v1.
- Full WCAG AAA accessibility compliance. v1 targets keyboard accessibility for the core flow only.
- Internationalization and localization. v1 ships in English only.
- Server-side rendering, SSR, or any deployment mode that requires hosting infrastructure.

## Requirements *(mandatory)*

### Functional Requirements

#### Search

- **FR-001**: System MUST provide a search input that accepts free-text queries and returns matching graph nodes built from existing indexed graph data (entity names, aliases, and related searchable fields).
- **FR-002**: System MUST return deterministic, stably ordered results for identical query and filter input.
- **FR-003**: System MUST display each search result with at least the entity name, entity type, and a way to identify the entity uniquely.
- **FR-004**: System MUST handle the empty-result case by showing an explicit no-results state, not a blank panel.
- **FR-005**: System MUST paginate or progressively reveal results when the match count exceeds a single visible page, preserving stable ordering across pages.

#### Filters

- **FR-010**: Users MUST be able to filter by one or more entity types simultaneously (multiple selections combined with OR logic).
- **FR-011**: Users MUST be able to apply field-level predicates (field, operator, value) to narrow results.
- **FR-012**: Users MUST be able to constrain graph traversal to specific edge types.
- **FR-013**: Users MUST be able to constrain traversal by a minimum edge confidence threshold where confidence values exist on edges.
- **FR-014**: System MUST keep the search results panel, the visible graph view, and the details panel synchronized after any filter change.
- **FR-015**: System MUST provide a single reset control that clears all filters and returns the view to the unfiltered state.

#### Navigation and Traversal

- **FR-020**: System MUST provide a graph view with selectable nodes and the ability to expand neighbors of any focused node.
- **FR-021**: Users MUST be able to select a search result and have the graph view focus on that node, with details visible in a panel.
- **FR-022**: System MUST maintain a breadcrumb path that reflects the active traversal sequence.
- **FR-023**: Users MUST be able to click any segment of the breadcrumb path to return focus to that node, truncating the path to that point.
- **FR-024**: System MUST provide a relationship explanation feature that, given two selected nodes, returns and displays a valid connection path or an explicit no-path outcome.
- **FR-025**: System MUST provide a reset control that clears the focused node, breadcrumb path, query text, and filters together.

#### State Management

- **FR-030**: System MUST persist navigation state (query text, active filters, focused node, breadcrumb path) in a form the user can save and reload.
- **FR-031**: System MUST restore saved state exactly: same query, same filters, same focus, same breadcrumb path.
- **FR-032**: System MUST handle stale references in saved state (e.g., the focused node no longer exists in the workspace) by showing an explicit stale-reference message and returning to a valid state.

#### Feedback and Accessibility

- **FR-040**: System MUST show clear UI states for: loading, empty results, invalid input, and recoverable query failures.
- **FR-041**: System MUST keep all primary controls (search input, result selection, filter controls, breadcrumb navigation, reset) keyboard-accessible.
- **FR-042**: System MUST provide focus indicators on all interactive elements when navigating via keyboard.

### Key Entities

- **Graph Node**: A navigable entity with a stable identifier, display label, type, optional metadata fields, and references to source artifacts. Maps directly to the entity records already produced by the existing pipeline.
- **Graph Edge**: A directed or undirected relationship between two graph nodes, including a relationship type and optional confidence and provenance attributes. Maps directly to the link records already produced by the existing pipeline.
- **Search Query**: User-provided text used to retrieve candidate nodes from indexed graph data.
- **Filter Set**: A structured set of constraints — entity types (OR), field predicates (AND), edge types (OR), and confidence threshold — applied to both search results and traversal expansion.
- **Navigation Session**: The user's current exploration state, comprising the search query, the filter set, the focused node, the breadcrumb path, and the visible viewport context.
- **Result Set**: A deterministically ordered collection of graph nodes returned by a search, including pagination metadata (total count, current offset, page size).
- **Relationship Explanation**: A structured response describing the connection (or absence of connection) between two graph nodes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of users in usability testing can locate a known target node using search and focus it in the graph within 30 seconds, on a workspace containing at least 1,000 entities.
- **SC-002**: At least 95% of search and filter interactions return visible results — or an explicit empty-state message — within 2 seconds on a workspace containing at least 1,000 entities.
- **SC-003**: 100% of repeated query and filter inputs produce identical result ordering across runs (determinism check).
- **SC-004**: At least 90% of saved navigation sessions can be reloaded with the query, filters, focus, and breadcrumb path restored exactly.
- **SC-005**: At least 95% of users in usability testing can complete a three-step traversal task (search → select → breadcrumb backtrack) without external guidance.
- **SC-006**: 100% of mandatory controls (search input, result selection, filter controls, focus selection, breadcrumb navigation, reset) are completable using only keyboard input.
- **SC-007**: When the workspace has no entities or no built indexes, the UI shows an explicit empty-state message in 100% of cases (no blank panels, no errors).

## Assumptions

- The navigation layer reads from the same local workspace storage that the existing CLI commands operate on. Entity, link, and index data is already available on disk after a normal pipeline run.
- The workspace is local to the user. No remote or cloud workspace is in scope.
- The navigation layer can rely on the existing search, filter, sort, pagination, and traversal capabilities exposed by the auditgraph CLI and MCP surface (notably the `query`, `list`, `neighbors`, and `why-connected` commands and their filter parameters).
- The user has filesystem read access to the workspace directory; no separate authentication is required.
- The default browser environment is a modern desktop browser supporting standard web platform features.
- Determinism in the underlying graph and query layer is preserved up to the UI layer; the navigation layer adds no nondeterministic behavior of its own.

## Open Questions

The following questions should be resolved during `/speckit.clarify` before planning. They have a material impact on scope and architecture.

- **[NEEDS CLARIFICATION]**: What is the navigation layer's runtime model? A fully static HTML+JS file that reads a pre-exported graph snapshot? A locally-hosted desktop application (e.g., Electron)? A locally-hosted web server (e.g., the auditgraph CLI launches a local HTTP server and the user opens a browser tab)? Each option has very different scope, dependency, and lifecycle implications.
- **[NEEDS CLARIFICATION]**: How does the navigation layer obtain graph data? A new export command (e.g., `auditgraph export-graph --format json`) that dumps a snapshot the UI loads? Direct subprocess calls to the existing CLI? An in-process Python adapter? A new HTTP API on top of the existing query layer?
- **[NEEDS CLARIFICATION]**: How is saved session state stored and shared? A JSON file on disk? Browser localStorage? A shareable URL that encodes the state? A new file under the workspace `.pkg/` directory? The choice affects whether sessions can be shared between users and whether they survive workspace re-builds.

## Notes

- A working visual prototype exists at `nav-example.html` in this directory. It demonstrates the intended look-and-feel, node layout, breadcrumb behavior, and details panel using portfolio data as the demo dataset. The prototype is a useful visual reference but is not a binding implementation choice — the runtime model question above is still open.
- This feature builds on the local query filter and aggregation work delivered in Spec 023. The required search, type filtering, field predicates, edge-type filtering, confidence thresholds, and deterministic ordering all already exist in the CLI and MCP surface. The remaining work for this spec is the navigation UI and the bridge between the UI and the existing query layer.
