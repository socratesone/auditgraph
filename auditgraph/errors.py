class AuditgraphError(RuntimeError):
    """Base error for auditgraph operations."""


class ConfigError(AuditgraphError):
    """Invalid configuration or missing configuration."""


class JobConfigError(AuditgraphError):
    """Invalid jobs configuration."""


class JobNotFoundError(AuditgraphError):
    """Requested job is not defined."""


class SecurityPolicyError(AuditgraphError):
    """Security policy validation failure."""


class PathPolicyError(AuditgraphError):
    """Path policy validation failure."""
