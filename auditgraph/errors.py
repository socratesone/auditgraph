class AuditgraphError(RuntimeError):
    """Base error for auditgraph operations."""


class ConfigError(AuditgraphError):
    """Invalid configuration or missing configuration."""


class JobConfigError(AuditgraphError):
    """Invalid jobs configuration."""


class JobNotFoundError(AuditgraphError):
    """Requested job is not defined."""
