# Quickstart: Remove Code Extraction (Spec 025)

This is a brief operator-facing guide to what changes after this spec ships and how to use the new behavior. For the design rationale see [spec.md](spec.md), [plan.md](plan.md), and [research.md](research.md).

## What changes for users

### Before this spec

```bash
# Default config tries to ingest .py .js .ts .tsx .jsx
auditgraph rebuild
# → "Extracts code symbols from supported source files"
# → 1 file entity per code file (no functions, no classes, just file metadata)
# → modifies links to non-code files (markdown, yaml, README) point at nothing
```

Querying neighbors of a commit on a mixed-content repo:

```bash
auditgraph neighbors <commit_id> --edge-type modifies
# → returns only modified .py / .js / .ts files
# → silently omits modified .md, .yaml, README, .pdf files
# → users assume the commit only touched code (it didn't)
```

### After this spec

```bash
# Default config no longer ingests code files at all
auditgraph rebuild
# → 0 entities from extract_code_symbols (it has been deleted)
# → file entities created by git provenance, one per distinct path in commit history
# → modifies links resolve for ALL file types
```

Querying neighbors:

```bash
auditgraph neighbors <commit_id> --edge-type modifies
# → returns every file the commit touched, regardless of extension
# → includes .md, .yaml, README, .pdf, AND .py if any
```

## Verification on the auditgraph repo itself

After the spec ships, run a clean rebuild to verify the new behavior:

```bash
rm -rf .pkg
auditgraph init --root .

# Use a config with git_provenance enabled
cat > /tmp/test-025.yaml <<EOF
pkg_root: "."
active_profile: "default"
profiles:
  default:
    include_paths:
      - "auditgraph"
      - "docs"
    exclude_globs: []
    ingestion:
      allowed_extensions: [".md", ".markdown", ".txt", ".pdf", ".docx"]
      ocr_mode: "off"
      chunk_tokens: 200
      chunk_overlap_tokens: 40
      max_file_size_bytes: 209715200
    git_provenance:
      enabled: true
      max_tier2_commits: 1000
    extraction:
      ner:
        enabled: false
EOF

auditgraph rebuild --root . --config /tmp/test-025.yaml
```

Expected results:

```bash
# Entity counts by type — file entities now come from git provenance
auditgraph list --root . --config /tmp/test-025.yaml --group-by type --count

# Sample output (real numbers depend on commit history):
# {
#   "groups": {
#     "commit": 118,
#     "file": 142,            ← was previously ~104 (code files only). Now covers ALL files in git history.
#     "ag:note": 22,
#     "ref": 26,
#     "author_identity": 2,
#     "repository": 1
#   },
#   "total_count": 311
# }
```

```bash
# Pick a commit that modified a markdown file (any recent merge commit will do)
COMMIT_ID=$(auditgraph list --root . --config /tmp/test-025.yaml --type commit --sort authored_at --desc --limit 1 2>&1 | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d['results'][0]['id'])")

# List its neighbors via modifies — should include .md files now, not just .py
auditgraph neighbors --root . --config /tmp/test-025.yaml "$COMMIT_ID" --edge-type modifies
```

Expected: every file the commit touched is reachable, regardless of extension.

## What you lose (honest disclosure)

This spec narrows scope intentionally. You lose three things:

1. **`.py .js .ts .tsx .jsx` files are no longer ingested as documents.** They are skipped at ingest with `skip_reason: unsupported_extension`. If you had `auditgraph list --type file` in your workflow on a non-git workspace, you get an empty result.
2. **The `chunk_code.enabled` config flag is removed.** It was added briefly during the quality sweep as an opt-in for token-based code chunking. The capability it gated is gone.
3. **Code-symbol-style queries are explicitly out of scope.** No "find all functions named X". For code structure navigation, use a language-aware tool like `tldr`, `ctags`, ripgrep, or your IDE's LSP.

## What you gain

1. **`modifies` links resolve for every file type.** A commit that touched a PDF, a YAML, and a README produces 3 reachable file entities, not "the PDF and YAML are missing because they're not code."
2. **`succeeded_from` (rename detection) links resolve at both endpoints.** Previously the old-path side was usually dangling.
3. **Honest documentation.** README, QUICKSTART, and CLAUDE.md no longer claim the project does code symbol extraction (which it never actually did).
4. **Simpler codebase to maintain.** One fewer extractor module, no parser routing for `text/code`, no opt-in flag for an unwanted feature.

## Migration for existing workspaces

| Your situation | What happens on next `auditgraph rebuild` |
|---|---|
| Workspace with no git history | File entities are no longer produced (no source). All other features unchanged. If you queried `--type file`, results are now empty. |
| Workspace with git history, no code files | File entities are created for every file in commit history (markdown, PDF, etc.). This is new — you previously had zero file entities for these. |
| Workspace with git history and code files | File entities are created for every file in commit history (including the code files). The IDs are byte-identical to the pre-change ones for the same paths, so existing `modifies` links still resolve. Plus, you now also see file entities for non-code committed files. |
| Workspace with code files NOT in git history | Those code files no longer appear as `file` entities anywhere. There is no replacement. The CHANGELOG documents this. |
| You added `.py` to a custom `allowed_extensions` config | Ingest still touches the file but now skips it with `unsupported_extension`. Effectively a no-op. Update your config to remove `.py` if you want it to be cleaner. |
| You used the `chunk_code.enabled: true` flag | Remove the flag from your config — it's no longer recognized. The capability it gated is gone. |

## Rollback

If for any reason this spec causes a regression, the rollback is straightforward:

```bash
# Two commits, two reverts
git revert <commit-B-sha>  # the deletions
git revert <commit-A-sha>  # the file entity migration
```

After the revert, `extract_code_symbols` is restored, the `text/code` parser routing is restored, and behavior matches pre-spec state including the dangling-reference bug. Phase A's bug fix is rolled back along with Phase B's deletions; if you wanted to keep the Phase A fix and only revert Phase B, you would revert only the second commit.

## Where to look in the code

- File entity creator (NEW): `auditgraph/git/materializer.py:build_file_nodes`
- File entity creator (DELETED): `auditgraph/extract/code_symbols.py` (file no longer exists)
- Parser routing table (MODIFIED): `auditgraph/ingest/policy.py:PARSER_BY_SUFFIX`, `DEFAULT_ALLOWED_EXTENSIONS`
- Stage entry point (MODIFIED): `auditgraph/pipeline/runner.py:run_git_provenance` (now calls `build_file_nodes`), `run_extract` (no longer calls `extract_code_symbols`)
- Default config (MODIFIED): `auditgraph/config.py:DEFAULT_CONFIG`, `config/pkg.yaml`
- Documentation (MODIFIED): `README.md`, `QUICKSTART.md`, `CLAUDE.md`, `CHANGELOG.md`
- Future spec stash (UPDATED): `specs/024-document-classification-and-model-selection/NOTES.md` § 4 → tombstone
