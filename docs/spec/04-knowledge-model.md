# Knowledge Model

## Purpose
Define canonical entity/claim/link semantics, contradiction handling, temporal facts, confidence policy, and ontologies.

## Source material
- [SPEC.md](SPEC.md) D) Knowledge Model
- [SPEC.md](SPEC.md) Data Model

## Decisions Required
- Formal definitions for entity, claim, note, task, decision, event.
- Contradiction handling (explicit model vs record both).
- Temporal fact support (validity windows, time-based queries).
- Confidence scores (rule-based only vs model-derived allowed).
- Ontology strategy (single vs multiple namespaces).

## Decisions (to fill)
- Entity/claim/note/task/decision/event definitions: Canonical node types with defined required fields; claims are subject–predicate–object assertions with provenance.
- Contradiction handling: Record both claims and explicitly flag contradictions.
- Temporal facts support: Optional validity windows on claims; missing windows imply timeless facts.
- Confidence policy: Rule-based confidence only for day 1.
- Ontology strategy: Primary namespace with optional secondary namespaces for extensions.

## Resolved
- Entity/claim/note/task/decision/event definitions
- Contradiction handling
- Temporal facts support
- Confidence policy
- Ontology strategy

## Assumptions
- Namespaces are required for non-core entity types to avoid collisions.
- Claims without subject are stored as unlinked with a reason.
