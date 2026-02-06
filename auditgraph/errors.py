class AuditgraphError(RuntimeError):
    """Base error for auditgraph operations."""


class ConfigError(AuditgraphError):
    """Invalid configuration or missing configuration."""
