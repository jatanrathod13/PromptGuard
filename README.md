# BehaviorCI

**CI/CD for LLM behavior.**

> Prompts don't ship until behavior passes tests.

BehaviorCI adds a **merge gate** in front of AI systems.  
You define expected behavior as **specs + tests + thresholds**.  
Every prompt or model change is evaluated in CI—and **fails the build** if behavior regresses.

Think **GitHub Actions for LLM behavior**.

---

## Why this exists

LLM behavior silently regresses:
- Prompt tweaks break edge cases
- Model updates shift outputs
- Fixes aren't captured as tests
- The same failures reappear

Traditional CI protects code, not behavior.

BehaviorCI turns LLM behavior into an **engineering artifact**:
- Versioned in git
- Reviewed in PRs
- Tested on every change
- Promoted only if thresholds pass
- Rollbackable when behavior breaks

---

## What it is (and isn't)

### ✅ It is
- CI/CD for LLM behavior
- A file-first spec format ("Behavior Bundles")
- Deterministic eval runs with reports & diffs
- Merge-blocking gates

### ❌ It is not
- A prompt optimizer
- Observability or monitoring
- An agent framework
- A hosted black box

---

## Installation

```bash
pip install behaviorci
```

## Quickstart

```bash
# Create an example bundle
behaviorci init bundles/my-test

# Validate configuration
behaviorci validate bundles/my-test/bundle.yaml

# Run with mock provider (no API key needed)
behaviorci run bundles/my-test/bundle.yaml --provider mock

# Run with OpenAI
export OPENAI_API_KEY=sk-xxx
behaviorci run bundles/my-test/bundle.yaml
```

If thresholds fail → exit code ≠ 0 → CI fails.

---

## Core Concept: Behavior Bundles

A **Behavior Bundle** defines:

| Component | Purpose |
|-----------|---------|
| `bundle.yaml` | Configuration: prompt path, dataset, thresholds |
| `prompt.md` | Prompt template with `{{ variables }}` |
| `dataset.jsonl` | Test cases (one JSON per line) |
| `schema.json` | Output structure validation (optional) |

### Example bundle.yaml

```yaml
name: my-feature
version: "1.0"

prompt_path: prompt.md
dataset_path: dataset.jsonl

output_contract:
  schema_path: schema.json
  invariants:
    - "len(raw_output) < 1000"

thresholds:
  - metric: pass_rate
    operator: ">="
    value: 0.9

provider:
  name: openai
  model: gpt-4o-mini
  temperature: 0.0
```

See [docs/behavior-bundles.md](docs/behavior-bundles.md) for full specification.

---

## CI Integration

### GitHub Actions

```yaml
name: Behavior Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - run: pip install behaviorci
    - run: behaviorci run bundles/my-feature/bundle.yaml
      env:
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

See [docs/ci-integration.md](docs/ci-integration.md) for GitLab, CircleCI, and Azure DevOps examples.

---

## Providers

| Provider | Environment Variable | Example Models |
|----------|---------------------|----------------|
| OpenAI | `OPENAI_API_KEY` | gpt-4o, gpt-4o-mini |
| Anthropic | `ANTHROPIC_API_KEY` | claude-3-opus, claude-3-sonnet |
| Mock | (none) | Deterministic test responses |

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `behaviorci init [path]` | Scaffold example bundle |
| `behaviorci validate <bundle>` | Validate configuration |
| `behaviorci run <bundle>` | Execute tests and emit report |

### Run Options

```bash
behaviorci run bundle.yaml --provider openai  # Override provider
behaviorci run bundle.yaml --format json      # JSON output
behaviorci run bundle.yaml --output report.md # Write to file
behaviorci run bundle.yaml --verbose          # Detailed output
```

See [docs/cli.md](docs/cli.md) for full reference.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Quickstart](docs/quickstart.md) | Get started in 5 minutes |
| [Architecture](docs/architecture.md) | System design and components |
| [Behavior Bundles](docs/behavior-bundles.md) | Full bundle specification |
| [CLI Reference](docs/cli.md) | All commands and options |
| [CI Integration](docs/ci-integration.md) | GitHub, GitLab, CircleCI guides |
| [FAQ](docs/faq.md) | Common questions |
| [Roadmap](docs/roadmap.md) | What's coming next |

---

## Development

```bash
# Clone and install in development mode
git clone https://github.com/behaviorci/behaviorci
cd behaviorci
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check behaviorci/

# Type check
mypy behaviorci/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT
