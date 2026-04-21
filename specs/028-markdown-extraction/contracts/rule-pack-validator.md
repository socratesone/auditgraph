# Contract: Rule-pack validator

**Module**: `auditgraph/utils/rule_packs.py` (NEW)
**Consumer**: `auditgraph/config.py` (called at config-load time).

## Public API

```python
@dataclass(frozen=True)
class RulePackError(Exception):
    kind: str   # "missing" | "malformed"
    path: str
    reason: str

    def __str__(self) -> str:
        if self.kind == "missing":
            return f"rule pack missing: {self.path} (reason: {self.reason})"
        if self.kind == "malformed":
            return f"rule pack malformed: {self.path} (reason: {self.reason})"
        return f"rule pack error: {self.path}"


def validate_rule_pack_paths(
    paths: Iterable[str],
    workspace_root: Path,
) -> None:
    """
    Validate every rule-pack path resolves to a readable, parseable YAML file.

    Parameters
    ----------
    paths
        Iterable of string paths as they appear in config (e.g.,
        ``extraction.rule_packs`` or ``linking.rule_packs``).
    workspace_root
        Workspace root directory. Relative paths in ``paths`` are resolved
        against this directory — NOT against the parent of the config
        file. Using the workspace root avoids path doubling when pkg.yaml
        (itself at ``<workspace_root>/config/pkg.yaml``) references
        paths like ``config/extractors/core.yaml``: resolution produces
        ``<workspace_root>/config/extractors/core.yaml``, not the
        doubled ``<workspace_root>/config/config/extractors/…``.

    Raises
    ------
    RulePackError(kind="missing")
        If a path does not resolve to a file either in the workspace or
        in the package-resource fallback.
    RulePackError(kind="malformed")
        If any resolved path exists but yaml.safe_load raises a YAMLError.
    """
```

Path resolution rule (authoritative, fixes adjustments2.md §4):

1. **Absolute paths** — used verbatim; no fallback attempted.
2. **Relative paths** — resolved against `workspace_root` (the directory that contains the `config/` subdirectory, NOT the config file's parent). This means a pkg.yaml entry like `config/extractors/core.yaml` resolves to `<workspace_root>/config/extractors/core.yaml`.
3. **Package-resource fallback** — when a workspace-relative path does not exist, look up the same path under `importlib.resources.files("auditgraph") / "_package_data" / <path>`. This lets shipped wheels provide the stubs even on workspaces where the user has not copied them into `<workspace_root>/config/`.
4. **Error** — if neither the workspace nor the package-resource path exists, raise `RulePackError(kind="missing")`.

Each resolved file is opened, read, and `yaml.safe_load` is called. The loaded structure is NOT schema-validated here — that's future work when rule packs carry real content. Spec-028's scope is "does this exist and parse?"

## `config.py` integration

At the point where `Config.profile()` materializes the profile dict (after applying defaults + overlays), add:

```python
from auditgraph.utils.rule_packs import RulePackError, validate_rule_pack_paths

def _validate_profile_rule_packs(profile: dict, workspace_root: Path) -> None:
    extraction_paths = profile.get("extraction", {}).get("rule_packs", []) or []
    linking_paths = profile.get("linking", {}).get("rule_packs", []) or []
    validate_rule_pack_paths(extraction_paths, workspace_root)
    validate_rule_pack_paths(linking_paths, workspace_root)
```

The caller MUST pass `workspace_root` — the directory containing `config/pkg.yaml`, NOT `config/pkg.yaml`'s parent. This is the same workspace root the pipeline already resolves for ingest (`_resolve_root(args.root)` in `auditgraph/cli.py`). Passing the config file's parent would re-introduce the path doubling documented in adjustments2.md §4.

- Called exactly once per config load.
- `RulePackError` propagates to the CLI, where it is caught and rendered as:

  ```json
  {
    "status": "error",
    "code": "rule_pack_missing" | "rule_pack_malformed",
    "message": "<str(RulePackError)>",
    "path": "<path>",
    "reason": "<reason>"
  }
  ```

  Exit code: 5 (new structured-config-error code; reuses the Spec-027 convention of small integer exit codes per error class).

## Shipped defaults and init behavior

Two stub files ship with the package **inside** the `auditgraph` Python package tree so they travel in every wheel:

- `/home/socratesone/socratesone/auditgraph/auditgraph/_package_data/config/extractors/core.yaml`
- `/home/socratesone/socratesone/auditgraph/auditgraph/_package_data/config/link_rules/core.yaml`

A thin shim at `/home/socratesone/socratesone/auditgraph/config/extractors/core.yaml` and `/home/socratesone/socratesone/auditgraph/config/link_rules/core.yaml` mirrors these so the in-repo layout still works for users running from a git checkout. `pyproject.toml` grows a `[tool.setuptools.package-data]` entry:

```toml
[tool.setuptools.package-data]
auditgraph = ["_package_data/config/**/*.yaml", "_package_data/config/**/*.yml"]
```

`auditgraph init` (in `auditgraph/scaffold.py :: initialize_workspace`) is extended so that, after copying `pkg.yaml`, it also writes the two rule-pack stubs into the user's `<root>/config/extractors/core.yaml` and `<root>/config/link_rules/core.yaml`. Source for the copy is `importlib.resources.files("auditgraph") / "_package_data" / "config" / …` — this works in both wheel-installed and editable-installed environments.

The rule-pack validator's path resolver falls back to the package-resource path when the workspace-local path is absent. Specifically: given a declared path `config/extractors/core.yaml`:

1. Try `<workspace_root> / "config/extractors/core.yaml"` on disk.
2. If absent, try `importlib.resources.files("auditgraph") / "_package_data" / "config" / "extractors" / "core.yaml"`.
3. If both absent, raise `RulePackError(kind="missing")`.

This fallback ensures a user who deleted their local stub still gets validation-green on the shipped content; users who populate their local stub with real rules shadow the package-resource version.

The two shipped stub files contain:

### `config/extractors/core.yaml`

```yaml
version: v1
# Spec-028: ships as a schema-valid empty stub so default config does not
# reference an orphan path. Future specs populate `extractors:` with real
# rule definitions; spec-028 itself does not require any content here.
extractors: []
```

### `config/link_rules/core.yaml`

```yaml
version: v1
# Spec-028: ships as a schema-valid empty stub. Future specs populate
# `link_rules:` with real rule definitions.
link_rules: []
```

Both files ship as **package data** — NOT as a top-level directory handled by `setuptools.packages.find`. The authoritative packaging design (fixes adjustments3.md §11):

- Package resources live under `auditgraph/_package_data/config/extractors/core.yaml` and `auditgraph/_package_data/config/link_rules/core.yaml` — inside the `auditgraph` package tree so the shipped wheel includes them.
- `pyproject.toml` grows a `[tool.setuptools.package-data]` entry that globs `_package_data/**/*.yaml` and `_package_data/**/*.yml`.
- The in-repo top-level `config/extractors/core.yaml` and `config/link_rules/core.yaml` are **editable-checkout mirrors** — present so a developer running from a git clone sees the same stubs at the paths `pkg.yaml` references. They are NOT the wheel-packaging mechanism.
- The validator's path-resolution fallback (above) uses `importlib.resources.files("auditgraph") / "_package_data"` to reach the shipped stubs when the workspace-local mirror is missing — that's the mechanism that makes the default config work in both dev and installed environments.

Any claim that "root `config/` is shipped as-is" or that `packages.find` packages the stubs is obsolete — explicitly retired in adjustments3.md §11.

## Test contract

- **Happy path (defaults, workspace-local)**: validator called with the shipped `config/extractors/core.yaml` and `config/link_rules/core.yaml` paths resolved against a workspace that has them on disk → no exception.
- **Happy path (package-resource fallback)**: validator called with the default paths from a workspace whose local `config/` directory is missing → falls back to `importlib.resources`, no exception.
- **Missing path (no fallback)**: config references `config/extractors/does-not-exist.yaml`; neither workspace-local nor package-resource path exists → `RulePackError(kind="missing")`.
- **Malformed YAML**: fixture with invalid YAML syntax in a rule-pack file → `RulePackError(kind="malformed")`.
- **Absolute path**: config references an absolute path outside `workspace_root` → resolves verbatim; no fallback attempted.
- **No path doubling**: pkg.yaml at `<workspace_root>/config/pkg.yaml` with `rule_packs: ["config/extractors/core.yaml"]` resolves to `<workspace_root>/config/extractors/core.yaml`, NOT `<workspace_root>/config/config/extractors/core.yaml`. Assert by pointing the validator at a fixture workspace and comparing the resolved path string.
- **Empty list**: config has `rule_packs: []` → no exception.
- **`auditgraph init` copies stubs**: run `initialize_workspace(root, config_source)` against a fresh `tmp_path`; assert that `<root>/config/extractors/core.yaml` and `<root>/config/link_rules/core.yaml` both exist and their content matches the package-resource stubs byte-identically.
- **Shipped wheel contains stubs**: build a wheel via `python -m build -w` (or equivalent), inspect contents, assert both stub YAML files are present under `auditgraph/_package_data/config/`.
- **CLI integration (missing path)**: run `auditgraph rebuild` with a config referencing a missing path; assert exit code 5 and structured JSON `code: rule_pack_missing` on stdout.
- **CLI integration (malformed YAML)**: same as above with malformed YAML; assert exit code 5 and distinct `code: rule_pack_malformed`.
