# auditgraph — Claude Code Guide

Local-first, deterministic personal knowledge graph CLI for engineers. Ingests notes, code, PDFs, and DOCX into a sharded JSON store; extracts entities and claims; builds explainable links; and exposes the result via CLI and MCP.

This file is the working agreement between Claude Code and this codebase. Read it before doing nontrivial work.

## Active Technologies
- Python 3.10+ (existing constraint, no change) + stdlib only for the new `build_file_nodes` function. No new dependencies. (025-remove-code-extraction)
- Sharded JSON files under `.pkg/profiles/<profile>/` (existing `entities/<shard>/<id>.json` layout, no change) (025-remove-code-extraction)

- Python 3.10+
- argparse (CLI), PyYAML (config), stdlib `json` (storage I/O)
- pypdf, python-docx (document parsers)
- spaCy (optional NER, off by default)
- dulwich (pure-Python git)
- neo4j driver (optional export target)
- pytest (with `--strict-markers`)

## Project Structure

```text
auditgraph/                 # main package
  cli.py                    # argparse CLI; _build_parser() + main() dispatch
  config.py                 # workspace + profile config loader
  pipeline/runner.py        # PipelineRunner: ingest → git_provenance → normalize → extract → link → index
  ingest/                   # file scanning, parsing, frontmatter, manifests
  extract/                  # note entities, NER, ADR, content extractors, document parsers
  normalize/                # path & text normalization
  link/                     # co-occurrence + adjacency builders
  index/                    # bm25, type_index, adjacency_builder
  query/                    # keyword, list_entities, neighbors, filters, why_connected, git_*
  storage/                  # loaders, artifacts, sharding, hashing
  neo4j/                    # optional export & sync
  git/                      # dulwich-based provenance reader
  jobs/                     # YAML automation runner
  llm/                      # LLM provider interface (NullProvider only for now)

llm-tooling/                # MCP tool manifest + generated artifacts
  tool.manifest.json        # SOURCE OF TRUTH for MCP tools
  skill.md                  # generated; do not hand-edit
  adapters/openai.functions.json  # generated; do not hand-edit
  generate_skill_doc.py     # regenerator
  generate_adapters.py      # regenerator
  mcp/                      # MCP server entrypoint + adapters

tests/                      # flat directory (no unit/integration split)
  test_spec<NNN>_*.py       # spec-numbered tests
  test_user_story_*.py      # user story tests
  fixtures/                 # per-spec test fixtures (sharded JSON)

specs/                      # spec-kit driven development
  <NNN>-<name>/             # one folder per feature
    spec.md plan.md tasks.md research.md data-model.md
    contracts/ checklists/ quickstart.md

config/                     # default workspace configs (pkg.yaml, jobs.yaml)
docs/                       # integration guides (neo4j, mcp, env setup)
```

## Storage Layout (`pkg_root` = `.pkg/profiles/<profile>/`)

```
entities/<shard>/<entity_id>.json    # one file per entity, 2-char shard from id
links/<shard>/<link_id>.json         # one file per link
chunks/<shard>/<chunk_id>.json
documents/<doc_id>.json
sources/<source_hash>.json
indexes/bm25/index.json              # inverted index
indexes/types/<type>.json            # per-type entity ID lists (Spec 023)
indexes/link-types/<type>.json       # per-type link ID lists (Spec 023)
indexes/graph/adjacency.json         # forward adjacency (rebuilt by Spec 023)
indexes/git-provenance/file-commits.json
runs/<run_id>/<stage>-manifest.json
runs/<run_id>/replay-log.jsonl
```

The shard is the first 2 characters of the part after the first `_` in the ID. Use `auditgraph.storage.sharding.shard_dir` — never recompute by hand.

## Commands

```bash
make dev                     # create venv, install dev deps
make test                    # run full test suite
pytest                       # direct pytest (after make dev)
pytest tests/test_spec023_*.py -v   # run a single spec's tests
ruff check .                 # lint
auditgraph rebuild           # full pipeline rebuild from sources
auditgraph list --type commit          # browse entities (Spec 023)
auditgraph query --q "term" --type X   # extended search with filters
```

## Code Style

- Python 3.10+. Use `from __future__ import annotations` in new modules.
- Type hints on all public functions. `pkg_root: Path` is the canonical first arg for query/storage functions.
- Pure stdlib `json` for read/write. No external JSON libs.
- Use `auditgraph.storage.artifacts.read_json` / `write_json` for file I/O — they apply consistent serialization (sort_keys, indent).
- Line length: 120 (black/ruff configured in pyproject.toml).
- No print() in library code; CLI output goes through `cli._emit()`.

## Recent Changes
- 025-remove-code-extraction: Added Python 3.10+ (existing constraint, no change) + stdlib only for the new `build_file_nodes` function. No new dependencies.

- 023-local-query-filters: Added local query filters & aggregation. New `auditgraph list` command, extended `query`/`neighbors` with `--type`/`--where`/`--sort`/`--limit`/`--count`/`--group-by`/`--edge-type`/`--min-confidence`. New per-type indexes and filter engine. Forward adjacency now rebuilt from all link files (was empty for git-provenance links). New MCP tool `ag_list` with response envelope. 161 new tests.
- 020-git-provenance-ingestion: Git provenance entities & links via dulwich. Commit/author/file/ref/tag entities; modifies/authored_by/parent_of/contains/tags/on_branch links. Git query commands.

<!-- MANUAL ADDITIONS START -->

## Non-Negotiables

1. **Determinism**: Identical inputs MUST produce identical outputs, including ordering. Sort with stable tiebreakers (typically `entity.id`). No iteration over `set` without sorting.
2. **Local-first**: No network calls in the core pipeline or query path. Neo4j is an *optional export target*, not a runtime dependency.
3. **Backwards compatibility**: New CLI flags and MCP parameters MUST be additive. Existing commands without new params MUST behave identically.
4. **Manifest is source of truth**: `llm-tooling/tool.manifest.json` is hand-edited. `llm-tooling/skill.md` and `llm-tooling/adapters/openai.functions.json` are generated — re-run the generators after manifest edits.
5. **Test before committing**: `pytest tests/test_spec<NNN>_*.py -v` for the spec you're working on, then `pytest tests/ -v` for regressions. Pre-existing failures (NER model unavailable, spec011 redaction) are tracked separately — don't conflate them with regressions.
6. **No co-author trailers**: Never add `Co-Authored-By: Claude` to commits in this repo.

## Adding a New CLI Subcommand

End-to-end checklist for adding `auditgraph foo`:

1. **Implement** the query function: `auditgraph/query/foo.py` exposing `def foo(pkg_root: Path, ...) -> dict`.
2. **Register parser**: in `auditgraph/cli.py` `_build_parser()`, add `foo_parser = subparsers.add_parser("foo", help="...")` with `--root`/`--config` and any specific args.
3. **Dispatch**: in `main()`, add `if args.command == "foo": ...` block. Resolve config via `_resolve_config`, get `pkg_root` via `profile_pkg_root(root, config)`, call the function, emit with `_emit(payload)`.
4. **MCP exposure** (if it should be callable from LLMs):
   - Add the command name to `auditgraph/utils/mcp_inventory.py` (`READ_TOOLS` for read-only, otherwise the appropriate set).
   - Add a tool entry to `llm-tooling/tool.manifest.json` with `name`, `title`, `description`, `risk` (low/medium/high), `idempotency`, `timeout_ms` (≤5000 for read tools), `command`, `input_schema`, `output_schema`, `error_schema`, `examples` (≥1 required), and `constraints.read_only_safe`.
   - Run `python llm-tooling/generate_skill_doc.py && python llm-tooling/generate_adapters.py`.
   - Run `pytest llm-tooling/tests -q` to verify contract tests.
5. **Tests**: add `tests/test_spec<NNN>_<topic>.py` covering the function and a CLI integration test.
6. **Docs**: add the command to `README.md` CLI Reference and (if user-facing) `QUICKSTART.md`. Add an entry to `CHANGELOG.md` under `## Unreleased`.

## Adding a New Pipeline Stage Output

The `index` stage is the canonical place to build derived structures from materialized entities. To add a new index:

1. Implement `build_<thing>(pkg_root, entities)` in `auditgraph/index/<thing>.py`.
2. Wire it into `PipelineRunner.run_index` in `auditgraph/pipeline/runner.py` after `build_bm25_index`. Add the path to `outputs_hash` and `artifacts`.
3. Add a corresponding loader function in `auditgraph/storage/loaders.py` if query code needs to read it.
4. The runner already loads entities once (`load_entities(pkg_root)`) — reuse that materialized list, don't reload.

## Spec-Kit Workflow

This project uses speckit for spec-driven development. Workflow: `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.analyze` → `/speckit.implement`. There is **no** `/speckit.finalize` — common confusion. Specs live in `specs/<NNN>-<name>/`. The plan template is at `.specify/templates/`. Constitution is at `.specify/memory/constitution.md` and is non-negotiable for implementation work.

## Testing Patterns

- **Fixtures**: per-spec under `tests/fixtures/spec<NNN>/`. Use the sharded layout (e.g., `entities/<2-char-shard>/ent_<id>.json`).
- **Workspace fixture**: a `tmp_path`-based pytest fixture that copies entity/link fixtures into a temp directory is the standard pattern (see `tests/test_spec023_type_index.py::spec023_workspace`).
- **Generators**: storage loaders in this codebase return generators (`Iterator[dict]`), not lists — assert with `isinstance(result, types.GeneratorType)` when testing the API contract.
- **Pre-existing failures** (do not treat as regressions): 2 NER tests (spaCy model unavailable), 1 spec011 redaction test.

## When Editing the MCP Manifest

The manifest has contract tests in `llm-tooling/tests/`:
- Every tool MUST have ≥1 example
- Every read-only tool (in `READ_TOOLS`) MUST have `timeout_ms ≤ 5000`
- Every tool MUST have valid `risk` and `idempotency` values
- After any edit, run `pytest llm-tooling/tests -q`
- After any edit, regenerate `skill.md` and `adapters/openai.functions.json`

## Common Pitfalls

- **Type filter case**: Entity types are case-sensitive (`commit`, not `Commit`). NER types use `ner:person` (with colon).
- **Entity ID prefixes vary**: Most entities use `ent_<sha256>`, but commits use `commit_<sha256>`. Don't hard-code `ent_`.
- **Adjacency was empty**: Before Spec 023, `indexes/graph/adjacency.json` only contained co-occurrence links and was effectively empty for most workspaces. It now contains all link types after running the `index` stage.
- **Don't use `git add -A`**: The repo has many unrelated untracked files (specs/021-*, .specify/integrations/, .mcp.json). Always stage explicitly by name.
- **Don't `set NOMATCH`**: tests/fixtures use literal filenames; glob patterns over fixture trees should be ordered (`sorted(rglob(...))`) for determinism.
- **NER is opt-in (off by default)**: `config/pkg.yaml` has `extraction.ner.enabled: false`. NER runs spaCy inference over every chunk and only makes sense on natural-language content. On code-only repos it spends 15+ minutes producing false positives. If a user reports `auditgraph rebuild` "hanging", check whether they enabled NER without realizing it.
- **NER has a natural-language extension allowlist**: Even when `enabled: true`, NER only runs on chunks whose source file extension is in `extraction.ner.natural_language_extensions` (default: `.md .markdown .txt .rst .pdf .docx`). Code files and extensionless files are skipped. Configurable allowlist, not a blocklist — adding new doc formats requires editing config; nothing accidentally pulls in code. See `auditgraph/extract/ner.py:_is_natural_language_source`.
- **NER quality on technical content is poor**: The default `en_core_web_sm` model is trained on news and web text. On research papers, ML literature, or technical documentation it produces ~95% false positives — acronyms classified as ORG, concept words classified as PERSON, citation tokens classified as MONEY. The `quality_threshold` config field is misleadingly named: it filters chunk text quality (alphanumeric ratio), NOT entity confidence. spaCy `sm` models don't expose per-entity confidence at all (`ner_backend.py` hardcodes `score=1.0`). If users have technical content, recommend SciSpaCy's `en_core_sci_sm` via `extraction.ner.model` config. Future work for document classification + dynamic model selection is captured in `specs/024-document-classification-and-model-selection/NOTES.md`.
- **Source code files are not ingested**: Files with `.py`, `.js`, `.ts`, `.tsx`, `.jsx` extensions are skipped at the ingest stage with `skip_reason: unsupported_extension`. Auditgraph is a documents + provenance tool — code intelligence is permanently out of scope (per Spec 025). Do not suggest ingesting code, do not propose adding code chunking, do not propose tree-sitter integration. For code structure navigation, recommend `tldr` (available in global rules) or other language-aware tooling. File entities for paths in git history are produced by `auditgraph/git/materializer.py:build_file_nodes` when git provenance is enabled — they serve as provenance anchors for `modifies` links from commits, not as ingestion sources. The full rationale lives in `specs/025-remove-code-extraction/spec.md`.

<!-- MANUAL ADDITIONS END -->
