# BehaviorCI

**CI/CD for LLM behavior.**

> Prompts don’t ship until behavior passes tests.

BehaviorCI adds a **merge gate** in front of AI systems.  
You define expected behavior as **specs + tests + thresholds**.  
Every prompt or model change is evaluated in CI—and **fails the build** if behavior regresses.

Think **GitHub Actions for LLM behavior**.

---

## Why this exists

LLM behavior silently regresses:
- Prompt tweaks break edge cases
- Model updates shift outputs
- Fixes aren’t captured as tests
- The same failures reappear

Traditional CI protects code, not behavior.

BehaviorCI turns LLM behavior into an **engineering artifact**:
- Versioned in git
- Reviewed in PRs
- Tested on every change
- Promoted only if thresholds pass
- Rollbackable when behavior breaks

---

## What it is (and isn’t)

### ✅ It is
- CI/CD for LLM behavior
- A file-first spec format (“Behavior Bundles”)
- Deterministic eval runs with reports & diffs
- Merge-blocking gates

### ❌ It is not
- A prompt optimizer
- Observability or monitoring
- An agent framework
- A hosted black box

---

## Quickstart

```bash
pip install behaviorci
behaviorci init
behaviorci run bundles/example/bundle.yaml
```

If thresholds fail → exit code ≠ 0 → CI fails.

---

## Core concept: Behavior Bundles

A **Behavior Bundle** defines:

* Prompt(s)
* Dataset (tests)
* Output contract (schema + invariants)
* Thresholds
* Fallback policies
* Reports

All as plain files. All reviewable.

See `docs/behavior-bundles.md`.

---

## Documentation

* Architecture: `docs/architecture.md`
* Behavior Bundles: `docs/behavior-bundles.md`
* CLI Reference: `docs/cli.md`
* CI Integration: `docs/ci-integration.md`
* Roadmap: `docs/roadmap.md`
* FAQ: `docs/faq.md`

---

## License

MIT
