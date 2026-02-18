# Execution Evidence: Neo4j Export and Sync

Date: 2026-02-17

## Environment

- Local Neo4j container: `auditgraph-neo4j`
- Bolt: `bolt://localhost:7687`
- Database: `neo4j`

## Commands Executed

1. `python -m auditgraph.cli rebuild --root . --config config/pkg.yaml`
2. `python -m auditgraph.cli export-neo4j --root . --config config/pkg.yaml --output exports/neo4j/live.cypher`
3. `cat exports/neo4j/live.cypher | docker exec -i auditgraph-neo4j cypher-shell -u neo4j -p <password>`
4. `docker exec auditgraph-neo4j cypher-shell -u neo4j -p <password> "MATCH (n) RETURN count(n) AS nodes; MATCH ()-[r]->() RETURN count(r) AS rels;"`
5. `sync-neo4j --dry-run`
6. `sync-neo4j` (run #1)
7. `sync-neo4j` (run #2)
8. `sync-neo4j` with invalid password
9. `python -m pytest tests/test_neo4j_*.py -q`
10. `python -m pytest -q`

## Result Summary

- Export summary:
  - mode: export
  - nodes_processed: 101
  - relationships_processed: 0
  - failed_count: 0
- Import verification query:
  - nodes: 101
  - rels: 0
- Dry-run summary:
  - mode: dry-run
  - failed_count: 0
- Live sync summaries:
  - run #1 mode: sync, nodes_updated: 101, failed_count: 0
  - run #2 mode: sync, nodes_updated: 101, failed_count: 0
- Invalid credential run:
  - exit code: 1
  - error contains actionable auth guidance for `NEO4J_USER` and `NEO4J_PASSWORD`
- Tests:
  - targeted Neo4j suite: 14 passed
  - full repository suite: 99 passed

## Notes

- Neo4j does not permit password value `neo4j` (default password restriction and minimum length policy).
- Validation used a policy-compliant local password while preserving requested URI, username, and database.
