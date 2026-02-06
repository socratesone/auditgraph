# Open Questions Resolution Log

## Purpose
Track outstanding questions and their final decisions.

## Source material
- [SPEC.md](SPEC.md) Open Questions and Clarifying Questions A–I

## Open Questions
1) Day-1 formats beyond Markdown/plain text and Git repos.
2) Required code languages and AST extraction depth.
3) Whether semantic search is required in MVP.
4) Preferred interface: CLI-only vs CLI + local web UI.
5) Encryption at rest requirements.
6) Latency targets and expected dataset sizes.
7) Contradiction handling model/UI.

## Resolution Log
| ID | Question | Decision | Rationale | Date | Owner |
| --- | --- | --- | --- | --- | --- |
| 1 | Day-1 formats beyond Markdown/plain text and Git repos | Day-1 sources are Markdown, plain text, and Git repos only | Determinism and parser stability | 2026-02-05 | spec |
| 2 | Required code languages and AST extraction depth | Python, JS/TS, Go with file-level symbols only | Keep extraction deterministic in MVP | 2026-02-05 | spec |
| 3 | Semantic search required in MVP | Optional, offline only | Preserve offline-first and determinism | 2026-02-05 | spec |
| 4 | Preferred interface | CLI-first, optional local web UI later | Align with MVP scope | 2026-02-05 | spec |
| 5 | Encryption at rest requirements | Not required for source store; optional for exports | Reduce complexity while enabling sharing | 2026-02-05 | spec |
| 6 | Latency targets and dataset sizes | Search p50 < 200ms, p95 < 1s; 10k notes/50 repos/1M symbols | Matches usability targets | 2026-02-05 | spec |
| 7 | Contradiction handling model/UI | Record both and flag contradictions | Preserve auditability | 2026-02-05 | spec |
