# Phase 1 Refactor Baseline

This phase establishes the new `src/mold_cost` package without breaking the current runtime.

Scope:
- create the new package and packaging metadata
- centralize settings and infrastructure entry points
- add workflow placeholders for the future LangGraph migration
- keep legacy imports working through thin compatibility wrappers

Notes:
- no CAD or pricing business rules are changed in this phase
- `scripts`, `agents`, and `api_gateway` still own the runtime behavior
- the new package currently acts as the stable landing zone for future migrations
