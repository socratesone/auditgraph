# Determinism & Audit Contract

## Purpose
Specify determinism boundaries, failure handling, audit artifacts, config immutability, and ranking stability.

## Source material
- [SPEC.md](SPEC.md) C) Determinism and Trust
- [SPEC.md](SPEC.md) Determinism Strategy

## Decisions Required
- Determinism boundaries (extraction, linking, ranking, summaries, QA responses).
- Failure modes (skip, unknown, queue review, fallback heuristics).
- Required audit artifacts (hashes, manifests, provenance edges, pipeline versioning, prompt logs, model pinning).
- Config immutability (snapshot profiles vs evolving in place).
- Ranking determinism (stable ordering across OS/hardware).

## Decisions (to fill)
- Deterministic components: Extraction outputs, link creation, ranking order, and manifests are deterministic. Summaries/QA are deterministic only if model/prompt are pinned and logged.
- Failure mode policy: Failures are recorded as skipped with explicit reasons; no silent drops.
- Audit artifacts required: Per-run manifests, config snapshot hash, pipeline version, provenance records, replay log.
- Config immutability policy: Snapshot config per run (hash + stored copy) even if configs evolve later.
- Ranking determinism policy: Stable sorting with deterministic tie-break keys across OS/hardware.

## Resolved
- Deterministic components
- Failure mode policy
- Audit artifacts required
- Config immutability policy
- Ranking determinism policy

## Assumptions
- LLM steps are optional and only deterministic when pinned and replay-logged.
- Sorting tie-breaks use stable IDs and normalized paths as deterministic keys.
