# Architecture

BehaviorCI is intentionally simple.

## Execution flow

1. Load Behavior Bundle
2. Validate config and references
3. Execute dataset cases
4. Evaluate output contracts
5. Apply thresholds
6. Emit reports
7. Exit pass/fail

## Core components

- CLI
- Bundle loader
- Provider adapters
- Runner
- Reporters

Design constraints:
- File-first
- CI-friendly
- Deterministic where possible
