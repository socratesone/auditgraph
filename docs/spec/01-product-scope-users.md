# Product Scope & Users

## Purpose
Define the primary users, domain scope, top workflows, UX expectations, and operational budgets.

## Source material
- [SPEC.md](SPEC.md) A) Users and Workflows
- [SPEC.md](SPEC.md) Executive Summary, Goals, Non-Goals, User Stories

## Decisions Required
- Primary user profile (solo engineer, team, research-heavy group).
- Knowledge domain scope (software-only vs mixed personal/work/research).
- Ranked top 5 workflows and priority order.
- Query/answer expectations (search/recall vs QA with citations vs graph exploration).
- Ingestion volume targets (daily/weekly files, MB, LOC).
- Latency tolerance per workflow (<50ms, <200ms, <1s) and which workflows require which tier.
- Manual review budget per day (0/5/30 minutes).

## Decisions (to fill)
- Primary user profile: Solo engineers and small engineering teams (1–8 users) as the primary users; larger teams are secondary.
- Knowledge domain scope: Software-engineering knowledge (code, APIs, ADRs, debugging logs, architecture docs) with optional personal notes as secondary.
- Top workflows (ranked):
	1. Codebase comprehension (symbols, definitions, references)
	2. Debugging logs and error signature tracking
	3. ADR capture and decision recall
	4. Search and recall across notes and code
	5. Project planning notes and task context
- Query/answer expectation: Search and recall with explainable citations, plus graph exploration for neighborhood/context.
- Ingestion volume targets: Daily 10–200 files, 1–50 MB, 1–20k LOC; weekly 100–1,000 files, 10–250 MB, 10–100k LOC.
- Latency tolerance by workflow: <200ms for search/recall and symbol lookup; <1s for graph traversal and “why connected”; <1s for ingest status summaries.
- Manual review budget: Up to 5 minutes per day for review of proposed links/claims.

## Resolved
- Primary user profile
- Knowledge domain scope
- Top workflows (ranked)
- Query/answer expectation
- Ingestion volume targets
- Latency tolerance by workflow
- Manual review budget

## Assumptions
- Initial adoption centers on individual engineers or small teams with local-first workflows.
- Performance targets prioritize interactive search and symbol lookup over heavy graph analytics.
- Review budget is intentionally low to preserve deterministic, low-maintenance operation.
