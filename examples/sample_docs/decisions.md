# Technical Decisions

## ADR-001: Use PostgreSQL over MongoDB

We chose PostgreSQL for ACID compliance and strong relational querying support.

## ADR-002: Event-Driven Architecture

Kafka was selected for async processing to decouple producers from consumers.

## ADR-003: Python for Backend

FastAPI provides async support and automatic OpenAPI documentation.
