# Behavior Bundles

A **Behavior Bundle** is a portable, file-first definition of expected LLM behavior. It packages everything needed to test a prompt:

- The prompt template
- Test cases (inputs)
- Expected output structure
- Pass/fail criteria

## Bundle Structure

```
bundles/my-feature/
├── bundle.yaml       # Configuration (required)
├── prompt.md         # Prompt template (required)
├── dataset.jsonl     # Test cases (required)
└── schema.json       # Output schema (optional)
```

## bundle.yaml Reference

```yaml
# Required fields
name: my-feature-bundle
prompt_path: prompt.md
dataset_path: dataset.jsonl

# Optional metadata
version: "1.0"
description: Tests for my feature's LLM behavior

# Output contract (optional)
output_contract:
  schema_path: schema.json        # JSON Schema for structure validation
  invariants:                      # Python expressions evaluated on output
    - "len(raw_output) < 1000"
    - "'error' not in raw_output.lower()"

# Pass/fail thresholds
thresholds:
  - metric: pass_rate              # % of cases that pass all checks
    operator: ">="
    value: 0.9
  - metric: schema_valid_rate      # % of outputs matching schema
    operator: ">="
    value: 0.95

# Provider configuration
provider:
  name: openai                     # openai | anthropic | mock
  model: gpt-4o-mini               # Provider-specific model ID
  temperature: 0.0                 # 0.0 for deterministic (recommended)
  max_tokens: 256                  # Maximum response length

# Execution options
parallel: false                    # Run cases in parallel
timeout: 30.0                      # Timeout per case (seconds)
retries: 1                         # Retry failed API calls
```

## Prompt Template

Prompts use [Jinja2](https://jinja.palletsprojects.com/) templating:

```markdown
You are a helpful assistant.

Question: {{ question }}

Answer in JSON format:
{
  "answer": "your answer",
  "confidence": 0.95
}
```

Variables come from the dataset's `input` field.

## Dataset Format

JSONL (JSON Lines) with one case per line:

```jsonl
{"input": {"question": "What is 2+2?"}, "expected_output": {"answer": "4"}}
{"input": {"question": "Capital of France?"}, "expected_output": {"answer": "Paris"}}
{"input": {"question": "Color of the sky?"}, "id": "sky-color-test"}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `input` | object | Variables substituted into prompt template |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (auto-generated if omitted) |
| `expected_output` | any | Expected response for comparison |
| `metadata` | object | Additional data for reporting |

## Output Contracts

Contracts define what makes a valid LLM response.

### JSON Schema

Validates output structure:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["answer", "confidence"],
  "properties": {
    "answer": { "type": "string", "minLength": 1 },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
  },
  "additionalProperties": false
}
```

### Invariants

Python expressions evaluated against the output:

```yaml
invariants:
  - "len(raw_output) < 2000"           # Length check
  - "'error' not in raw_output.lower()" # Must not contain "error"
  - "output.get('confidence', 0) > 0.5" # Confidence threshold
```

Available variables:
- `output` — Parsed JSON (or raw string if not JSON)
- `raw_output` — Raw response string

## Thresholds

Thresholds determine if the bundle passes or fails:

```yaml
thresholds:
  - metric: pass_rate
    operator: ">="
    value: 0.9
```

### Available Metrics

| Metric | Description |
|--------|-------------|
| `pass_rate` | % of cases passing all checks |
| `schema_valid_rate` | % of outputs matching schema |
| `error_rate` | % of cases with provider errors |
| `avg_latency_ms` | Average response time |
| `max_latency_ms` | Maximum response time |

### Operators

- `>=` — Greater than or equal
- `>` — Greater than
- `<=` — Less than or equal
- `<` — Less than
- `==` — Equal to

## Example: Complete Bundle

### bundle.yaml

```yaml
name: question-answering
version: "1.0"
description: Tests Q&A response format and accuracy

prompt_path: prompt.md
dataset_path: questions.jsonl

output_contract:
  schema_path: schema.json
  invariants:
    - "len(raw_output) < 500"
    - "output.get('confidence', 0) >= 0.5"

thresholds:
  - metric: pass_rate
    operator: ">="
    value: 0.85
  - metric: schema_valid_rate
    operator: ">="
    value: 0.95

provider:
  name: openai
  model: gpt-4o-mini
  temperature: 0.0
```

### prompt.md

```markdown
Answer the following question concisely and accurately.

Question: {{ question }}

Respond with a JSON object containing:
- "answer": Your concise answer
- "confidence": A number from 0 to 1

JSON response only, no additional text.
```

### questions.jsonl

```jsonl
{"input": {"question": "What is the capital of Japan?"}}
{"input": {"question": "How many planets are in our solar system?"}}
{"input": {"question": "Who wrote Romeo and Juliet?"}}
```

### schema.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["answer", "confidence"],
  "properties": {
    "answer": { "type": "string" },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
  }
}
```

## Best Practices

1. **Start simple** — Begin with just prompt + dataset, add contracts later
2. **Use temperature 0** — For reproducible tests
3. **Keep datasets focused** — 10-50 cases per bundle
4. **Version bundles** — Use semantic versioning in `version` field
5. **Descriptive IDs** — Name test cases for easy failure identification
6. **Document invariants** — Add comments explaining why each rule exists
