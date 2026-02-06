# Extractor Plugin Example

This example shows the expected configuration shape for a deterministic extractor plugin.

## Config (pkg.yaml)

```yaml
profiles:
  default:
    extraction:
      rule_packs:
        - "config/extractors/core.yaml"
    plugins:
      extractors:
        - name: "custom_regex"
          module: "my_plugins.custom_regex"
          entrypoint: "extract"
          config:
            pattern: "TODO:"
```

## Plugin Module (my_plugins/custom_regex.py)

```python
from __future__ import annotations

from typing import Iterable


def extract(paths: Iterable[str], config: dict) -> list[dict]:
    # Deterministic extraction logic here
    return []
```

## Notes
- Plugins must be deterministic and produce the same output for the same inputs.
- Version and rule identifiers should be included in the output provenance.
