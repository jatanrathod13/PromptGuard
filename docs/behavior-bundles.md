# Behavior Bundles

A Behavior Bundle is a **portable definition of expected LLM behavior**.

## Required files

- bundle.yaml
- dataset.jsonl
- prompt.md

Optional:
- schema.json
- reports/

## Output contracts

Contracts consist of:
- JSON schema
- Invariants (rules)

BehaviorCI enforces **constraints**, not “quality”.

## Thresholds

Thresholds decide release eligibility.

If thresholds fail → build fails.
