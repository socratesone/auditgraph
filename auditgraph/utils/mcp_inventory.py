"""CLI tool inventory for manifest coverage checks."""

READ_TOOLS = (
    "version",
    "query",
    "node",
    "neighbors",
    "diff",
    "jobs list",
    "why-connected",
)

WRITE_TOOLS = (
    "init",
    "ingest",
    "import",
    "normalize",
    "extract",
    "link",
    "index",
    "rebuild",
    "export",
    "jobs run",
)

ALL_TOOLS = READ_TOOLS + WRITE_TOOLS
