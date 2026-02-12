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

Run extract stage.

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

Run a keyword query over the graph.

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
