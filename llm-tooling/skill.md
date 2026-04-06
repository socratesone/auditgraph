# Auditgraph Skill

This document describes the MCP tool surface for auditgraph.

## ag_diff

Diff two runs.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "run_a": {
      "type": "string"
    },
    "run_b": {
      "type": "string"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "run_a": "run-1",
    "run_b": "run-2"
  },
  "output": {
    "diff": []
  }
}
```

## ag_export

Export a subgraph.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "format": {
      "type": "string"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    },
    "output": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "format": "json",
    "output": "exports/graph.json"
  },
  "output": {
    "format": "json",
    "path": "exports/graph.json"
  }
}
```

## ag_extract

Run extract stage. For markdown files, extracts sections (headings), technology mentions, and references (links) as sub-entities.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    },
    "run_id": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "root": "."
  },
  "output": {
    "stage": "extract",
    "status": "ok"
  }
}
```

## ag_import

Manually import files or directories.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "paths": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "required": [
    "paths"
  ],
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "paths": [
      "./src"
    ]
  },
  "output": {
    "stage": "import",
    "status": "ok"
  }
}
```

## ag_index

Run index stage.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    },
    "run_id": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "root": "."
  },
  "output": {
    "stage": "index",
    "status": "ok"
  }
}
```

## ag_ingest

Run ingest stage.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "root": "."
  },
  "output": {
    "stage": "ingest",
    "status": "ok"
  }
}
```

## ag_init

Initialize an auditgraph workspace.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "root": {
      "type": "string"
    },
    "config_source": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "root": "."
  },
  "output": {
    "created": true
  }
}
```

## ag_jobs_list

List available automation jobs.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {},
  "output": {
    "jobs": []
  }
}
```

## ag_jobs_run

Run a named automation job.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "required": [
    "name"
  ],
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "name": "daily"
  },
  "output": {
    "job": "daily",
    "status": "queued"
  }
}
```

## ag_link

Run link stage.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    },
    "run_id": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "root": "."
  },
  "output": {
    "stage": "link",
    "status": "ok"
  }
}
```

## ag_list

List entities with filtering, sorting, pagination, and aggregation. Returns a response envelope with results, total_count, limit, offset, and truncated fields.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "description": "Filter by entity type"
    },
    "where": {
      "type": "string",
      "description": "Field predicate: field<op>value"
    },
    "sort": {
      "type": "string",
      "description": "Sort by field name"
    },
    "limit": {
      "type": "integer",
      "default": 100,
      "description": "Max results (default 100)"
    },
    "offset": {
      "type": "integer",
      "default": 0,
      "description": "Skip first N results"
    },
    "count": {
      "type": "boolean",
      "description": "Return count only"
    },
    "group_by": {
      "type": "string",
      "description": "Group results by field"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "type": "commit",
    "limit": 10
  },
  "output": {
    "results": [],
    "total_count": 0,
    "limit": 10,
    "offset": 0,
    "truncated": false
  }
}
```

## ag_neighbors

Fetch neighbors for a node.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "depth": {
      "type": "integer"
    },
    "edge_type": {
      "type": "string",
      "description": "Filter by edge type"
    },
    "min_confidence": {
      "type": "number",
      "description": "Minimum confidence threshold"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "id": "entity:123",
    "depth": 1
  },
  "output": {
    "id": "entity:123",
    "neighbors": []
  }
}
```

## ag_node

Fetch a node by id.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "id": "entity:123"
  },
  "output": {
    "id": "entity:123"
  }
}
```

## ag_normalize

Run normalize stage.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    },
    "run_id": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "root": "."
  },
  "output": {
    "stage": "normalize",
    "status": "ok"
  }
}
```

## ag_query

Run a tokenized keyword query over the graph. Queries are split into tokens and matched against entity names and aliases. Results are scored by match coverage.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "q": {
      "type": "string"
    },
    "type": {
      "type": "string",
      "description": "Filter by entity type"
    },
    "where": {
      "type": "string",
      "description": "Field predicate: field<op>value"
    },
    "sort": {
      "type": "string",
      "description": "Sort by field name"
    },
    "limit": {
      "type": "integer",
      "description": "Max results"
    },
    "offset": {
      "type": "integer",
      "description": "Skip first N results"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "q": "payments"
  },
  "output": {
    "query": "payments",
    "results": []
  }
}
```

## ag_rebuild

Rebuild all stages.

- Risk: high
- Idempotency: non-idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "root": "."
  },
  "output": {
    "stage": "rebuild",
    "status": "ok"
  }
}
```

## ag_version

Return the auditgraph CLI version.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object",
  "properties": {
    "version": {
      "type": "string"
    }
  },
  "required": [
    "version"
  ],
  "additionalProperties": false
}
```

### Example
```
{
  "input": {},
  "output": {
    "version": "0.1.0"
  }
}
```

## ag_why_connected

Explain why two nodes are connected.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "from_id": {
      "type": "string"
    },
    "to_id": {
      "type": "string"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "required": [
    "from_id",
    "to_id"
  ],
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object"
}
```

### Example
```
{
  "input": {
    "from_id": "entity:1",
    "to_id": "entity:2"
  },
  "output": {
    "path": []
  }
}
```

## git_commits_for_file

Return commits that modified a given file, ordered by authored timestamp descending.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "file": {
      "type": "string"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "required": [
    "file"
  ],
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "file": {
      "type": "string"
    },
    "commits": {
      "type": "array"
    }
  },
  "required": [
    "status",
    "file",
    "commits"
  ]
}
```

### Example
```
{
  "input": {
    "file": "src/main.py"
  },
  "output": {
    "status": "ok",
    "file": "src/main.py",
    "commits": []
  }
}
```

## git_file_history

Return full provenance history for a file: authors, commits, introduction info, and lineage.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "file": {
      "type": "string"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "required": [
    "file"
  ],
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "file": {
      "type": "string"
    },
    "authors": {
      "type": "array"
    },
    "commits": {
      "type": "array"
    },
    "introduced": {
      "type": "object"
    },
    "lineage": {
      "type": "array"
    }
  },
  "required": [
    "status",
    "file",
    "authors",
    "commits",
    "introduced",
    "lineage"
  ]
}
```

### Example
```
{
  "input": {
    "file": "src/main.py"
  },
  "output": {
    "status": "ok",
    "file": "src/main.py",
    "authors": [],
    "commits": [],
    "introduced": {},
    "lineage": []
  }
}
```

## git_file_introduced

Return the earliest commit that introduced a given file, with rename lineage if detected.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "file": {
      "type": "string"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "required": [
    "file"
  ],
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "file": {
      "type": "string"
    },
    "commit": {
      "type": "object"
    },
    "lineage": {
      "type": "array"
    }
  },
  "required": [
    "status",
    "file",
    "commit",
    "lineage"
  ]
}
```

### Example
```
{
  "input": {
    "file": "src/main.py"
  },
  "output": {
    "status": "ok",
    "file": "src/main.py",
    "commit": {},
    "lineage": []
  }
}
```

## git_who_changed

Return author identities who modified a given file, with commit counts and date ranges.

- Risk: low
- Idempotency: idempotent

### Inputs
```
{
  "type": "object",
  "properties": {
    "file": {
      "type": "string"
    },
    "root": {
      "type": "string"
    },
    "config": {
      "type": "string"
    }
  },
  "required": [
    "file"
  ],
  "additionalProperties": false
}
```

### Outputs
```
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "file": {
      "type": "string"
    },
    "authors": {
      "type": "array"
    }
  },
  "required": [
    "status",
    "file",
    "authors"
  ]
}
```

### Example
```
{
  "input": {
    "file": "src/main.py"
  },
  "output": {
    "status": "ok",
    "file": "src/main.py",
    "authors": []
  }
}
```
