# PromptGuard Plan Critical Review: Challenges & Issues

## Executive Assessment

PromptGuard has a well-articulated vision — become the "CI/CD infrastructure for AI agents" — but there is a **significant gap between the current implementation reality and the ambitious roadmap**. The codebase is at an early-stage prototype level (~2,500 statements, 17% test coverage), while the vision document (`agentic-platform-vision.md`) describes a platform that would require an order of magnitude more engineering effort. This review identifies concrete challenges across technical, strategic, and execution dimensions.

---

## 1. CRITICAL: Implementation Maturity vs. Claimed Features

### 1.1 Agent Module Is a Skeleton, Not a Feature

The README and roadmap mark "Agent Bundle specification" and "Tool calling agent support" as **complete (v0.2)**, but the actual implementation reveals:

- **Tool extraction is regex-based text parsing** (`agent/runner.py:378-425`), not real API tool-calling. The `_extract_tool_calls()` method parses markdown code blocks and plain text patterns like `tool_name(arg=val)`. This is fundamentally unreliable — LLMs don't produce tool calls in a predictable text format.

- **`_generate_with_tools()` ignores tools entirely** (`agent/runner.py:285-308`). The method builds a tool spec via `_build_tools_spec()` which returns an empty list (`agent/runner.py:456-464`), then falls back to `self.provider.generate(prompt)` — a plain text completion with no tool-calling API integration.

- **Tool execution is fully simulated** (`agent/runner.py:32-101`). `SimpleToolExecutor._simulate_tool()` returns hardcoded fake responses based on keyword matching of tool names (e.g., if "read" is in the name, return `"[Simulated content of {filename}]"`). This cannot validate real agent behavior.

- **LLM-as-judge is a placeholder** (`agent/evaluator.py:282-284`): `result["details"]["note"] = "LLM judge not implemented yet"`. Same for task completion evaluation — it uses a "simple heuristic" that marks any result with tool calls as score 1.0 (`agent/evaluator.py:307-313`).

- **File content validation is stubbed** (`agent/evaluator.py:466-478`): The `_evaluate_expected` method has a `pass` statement where file content checking should be, with a comment "Simplified - would need actual file content."

**Impact**: The v0.2 agent testing feature set is effectively non-functional for real-world use. Marking these as "complete" in documentation creates a trust problem with potential users who try to use these features.

### 1.2 Zero Test Coverage for v0.2 Features

The test coverage analysis reveals:

| Module | Coverage | Status |
|--------|----------|--------|
| `agent/evaluator.py` | **0%** | No tests at all |
| `agent/runner.py` | **0%** | No tests at all |
| `agent/loader.py` | **0%** | No tests at all |
| `agent/models.py` | **0%** | No tests at all |
| `baseline/storage.py` | **0%** | No tests at all |
| `baseline/models.py` | **0%** | No tests at all |
| `diff/comparator.py` | **0%** | No tests at all |
| `diff/models.py` | **0%** | No tests at all |
| `integrations/github.py` | **0%** (implicit) | No tests at all |
| `cli.py` | **0%** | No tests at all |
| All reporters | **0%** | No tests at all |

**Overall project coverage: 17%**. The only tested modules are the v0.1 core (bundle loading, dataset parsing, mock provider, runner engine). Every feature marketed as part of v0.2 — agent bundles, baseline/diff, GitHub integration — has zero test coverage.

For a project whose entire value proposition is **testing and quality gating**, shipping untested code is a particularly damaging credibility issue.

---

## 2. CRITICAL: Security Vulnerabilities

### 2.1 Arbitrary Code Execution via `eval()`

Both `runner/evaluator.py:161` and `agent/evaluator.py:412-413` use Python's `eval()` to execute user-supplied invariant expressions:

```python
result = eval(invariant, {"__builtins__": {}}, context)
```

While `__builtins__` is set to empty, this is **not a secure sandbox**. Known bypass techniques exist:

- Access to `__class__`, `__subclasses__()`, `__globals__` through any object in context
- The `context` dict includes `json`, `re`, `isinstance`, and the full `case_result` object — all of which expose `__class__.__subclasses__()` chains that can reach `os`, `subprocess`, etc.
- Example exploit vector: `output.__class__.__base__.__subclasses__()` can enumerate all loaded Python classes

This is a **remote code execution risk** when running untrusted bundles, which is exactly the CI/CD use case where bundles come from pull requests potentially authored by external contributors.

### 2.2 `requests` Import in GitHub Integration

`integrations/github.py:136-137` does a runtime `import requests` but `requests` is not in the project's dependencies (`pyproject.toml`). This means:
- The REST API fallback path silently fails if `requests` isn't installed
- If it happens to be installed, it's an unmanaged transitive dependency with no version pinning

---

## 3. HIGH: Architectural & Design Issues

### 3.1 Providers Don't Support Tool Calling

The provider abstraction (`providers/base.py`) defines a single method: `generate(prompt: str) -> ProviderResponse`. This is a text-in/text-out interface that fundamentally cannot support:

- **Tool/function calling** (the core of agent testing)
- **Multi-turn conversation** (required for agent loops)
- **Structured outputs** (JSON mode, response_format)
- **System messages** (separate from user prompts)
- **Streaming** (roadmap v0.4)

The entire provider layer needs to be redesigned to support the Messages API pattern (system + messages[] + tools[]) before agent testing can work. This isn't a small change — it's a foundational rearchitecture that affects every provider, the runner, and the agent runner.

### 3.2 Agent Runner Conflates Concerns

`agent/runner.py` tries to be both:
1. An **agent execution engine** (managing multi-turn conversation loops with tool execution)
2. A **test harness** (recording traces for evaluation)

Real agent testing should wrap an *existing* agent (from OpenAI SDK, LangChain, etc.) and observe its behavior — not re-implement agent execution from scratch. The current approach means PromptGuard's "agent testing" is actually "testing PromptGuard's own agent implementation," which is not what users need.

### 3.3 Synchronous Provider Calls in Async Context

The OpenAI and Anthropic providers create a new `httpx.AsyncClient()` for every single request (`openai.py:91`, `anthropic.py:95`):

```python
async with httpx.AsyncClient() as client:
```

This destroys connection pooling and is a performance antipattern. For parallel execution (a key advertised feature), this means N concurrent requests create N TCP connections with N TLS handshakes instead of reusing connections.

### 3.4 No Rate Limiting

There is no rate limiting implementation despite the parallel execution feature. Running 100 test cases in parallel against OpenAI's API will hit rate limits immediately. The roadmap mentions this for v0.4, but it should be a prerequisite for the parallel execution feature already shipped in v0.1.

---

## 4. HIGH: Strategic & Competitive Challenges

### 4.1 The "Connective Tissue" Strategy Has a Bootstrapping Problem

The vision positions PromptGuard between Langfuse (observability) and PromptFoo (red teaming). This creates a dependency on both ecosystems:

- **Langfuse trace ingestion** requires Langfuse to maintain a stable trace format and API — if they change it, PromptGuard breaks
- **PromptFoo delegation** requires shelling out to a Node.js subprocess (`promptfoo redteam run`) from a Python tool — cross-runtime dependencies are fragile and hard to maintain
- **Neither Langfuse nor PromptFoo has any incentive to make integration easy** — they could build competing CI gating features themselves

The strategy makes PromptGuard dependent on two well-funded startups' goodwill while providing no moat if they decide to expand into PromptGuard's territory.

### 4.2 Framework Adapter Maintenance Burden

The vision proposes adapters for 6+ frameworks (OpenAI Agents SDK, Claude Agent SDK, LangChain, LangGraph, CrewAI, Google ADK). Each framework:

- Has its own release cycle and breaking changes
- Defines agents, tools, and traces differently
- May change APIs without notice (CrewAI and LangChain are known for frequent breaking changes)

For a solo maintainer or small team, maintaining 6 framework adapters is unsustainable. LangChain alone has had ~15 major breaking changes across its callback system. Each adapter represents an ongoing maintenance commitment, not a one-time build.

### 4.3 The Statistics Claim Needs Careful Implementation

The vision makes a bold claim: "No other open-source tool does multi-trial statistical agent testing." While statistically sound evaluation is valuable, the implementation challenges are significant:

- **Cost**: 5 trials × 20 tasks = 100 LLM calls per test run. At ~$0.03/call for GPT-4o, that's $3 per CI run for a small test suite. Teams running CI frequently will see costs multiply rapidly.
- **Time**: 100 sequential LLM calls at ~2 seconds each = ~3 minutes minimum per test run. Even with parallelism and rate limits, CI pipelines would slow significantly.
- **Statistical validity**: 5 trials per task gives very wide confidence intervals. You need ~30+ samples for normal approximation to be reliable. But 30 trials × 20 tasks = 600 calls = $18 per run.

The plan doesn't address how to make multi-trial testing practical within real CI time and cost budgets.

### 4.4 Naming Collision Risk

"PromptGuard" is already the name of [Meta's prompt injection detection model](https://huggingface.co/meta-llama/Prompt-Guard-86M) (Prompt-Guard-86M). While not identical, having the same name as a Meta AI safety product in the same domain creates confusion and potential trademark issues. The PyPI package `promptguard` could face challenges if Meta decides to publish a package with the same name.

---

## 5. MEDIUM: Development & Process Issues

### 5.1 CI Pipeline Has Environment Isolation Issues

The test failure I encountered (`ModuleNotFoundError: No module named 'yaml'`) reveals that the pip-installed package (`pip install -e ".[dev]"`) doesn't properly install all dependencies when run from a different Python environment than where pip installed them. The CI workflow (`ci.yaml`) may pass on GitHub Actions due to a consistent `ubuntu-latest` environment but fail in other setups. This is because `pytest` is invoked as a standalone tool rather than through `python -m pytest`, causing it to potentially use a different Python installation than where the dependencies were installed.

### 5.2 CHANGELOG is Stale

`CHANGELOG.md` only documents v0.1.0, despite v0.2.0 being the current release. For an open-source project seeking contributors, an up-to-date changelog is basic OSS hygiene.

### 5.3 Roadmap Version Conflict

The `roadmap.md` shows v0.3 as "Policy Packs" and v0.4 as "Enhanced Providers", but `agentic-platform-vision.md` redefines v0.3 as "Universal Agent Adapters" and v0.4 as "Statistical Engine". These two documents contradict each other. A potential contributor or user would not know which is the actual plan.

### 5.4 No Integration Tests with Real Providers

All tests use the mock provider. There are no integration tests that validate the OpenAI or Anthropic providers actually work. Given that these providers construct raw HTTP requests with `httpx` (rather than using the official SDKs), there's a risk that API changes silently break production functionality. The Anthropic provider still defaults to `claude-3-haiku-20240307`, a model that is being deprecated.

---

## 6. MEDIUM: Documentation vs. Reality Gaps

### 6.1 README Feature Comparison Table is Misleading

The README compares PromptGuard favorably against PromptFoo and Langfuse with checkmarks for features like "Agent tool-calling tests" and "Baseline & diff". These features exist as code but are non-functional (as detailed in Section 1). The comparison creates an inaccurate impression for users evaluating the tool.

### 6.2 Example Bundle Only Tests Mock Provider

The hello-world example uses the mock provider, which returns deterministic canned responses. A user following the quickstart will see "all tests pass" but hasn't actually validated any LLM behavior. There should be examples showing real provider usage with realistic test cases.

### 6.3 Architecture Docs Don't Reflect v0.2

`docs/architecture.md` only documents the v0.1 architecture (bundles, runner, providers, reporters). The v0.2 components (agent module, baseline, diff, integrations) are not mentioned. The architecture diagram is incomplete.

---

## 7. Methodology Challenges

### 7.1 The "File-First" Approach Has Scaling Limits

YAML-defined bundles work for small test suites, but the approach breaks down when:

- **Test suites grow large**: Hundreds of JSONL entries become unmanageable to review in PRs
- **Tests need programmatic generation**: Fuzzing, data-driven tests, and parametric testing are awkward in YAML
- **Multiple teams need different configs**: Bundle inheritance/composition isn't supported

The vision document acknowledges this by proposing a Python SDK, but this creates two paths (YAML and Python) that need feature parity and documentation.

### 7.2 Invariant Expressions Are a Poor Language Choice

Using Python `eval()` for invariant expressions (e.g., `len(raw_output) < 500`) is:

- **Insecure** (Section 2.1)
- **Fragile**: No IDE support, no type checking, no error messages pointing to YAML line numbers
- **Opaque for non-Python users**: Data scientists familiar with SQL or analytics tools can't write invariants

A purpose-built expression language (like PromptFoo's assertion syntax, or a CEL-like DSL) would be safer and more user-friendly.

### 7.3 No Strategy for Handling Non-Determinism in v0.1/v0.2

The current `run` command executes each test case exactly once. LLM outputs are non-deterministic (even at temperature 0.0, outputs can vary across API versions and model updates). A single run can produce different pass/fail results each time, making CI gates unreliable. The multi-trial statistical approach is the right solution, but it's planned for v0.4 — meaning the current tool can produce inconsistent CI results.

---

## 8. Summary of Recommendations

| Priority | Issue | Recommendation |
|----------|-------|----------------|
| **P0** | Agent module is non-functional | Either remove agent features from v0.2 marketing or implement real tool-calling |
| **P0** | `eval()` security vulnerability | Replace with a safe expression evaluator (e.g., `asteval`, CEL, or a custom DSL) |
| **P0** | 17% test coverage | Write tests for all v0.2 modules before adding v0.3 features |
| **P1** | Provider layer can't support agents | Redesign to support messages API pattern with tool definitions |
| **P1** | Roadmap conflict between docs | Reconcile `roadmap.md` and `agentic-platform-vision.md` into one source of truth |
| **P1** | No rate limiting for parallel execution | Add configurable rate limiting before advertising parallel execution |
| **P2** | Connection pooling antipattern | Use shared `httpx.AsyncClient` instances per provider |
| **P2** | Naming collision with Meta's PromptGuard | Evaluate trademark risk and consider rename if needed |
| **P2** | Framework adapter maintenance burden | Start with 1-2 adapters (OpenAI + LangChain), prove the pattern, then expand |
| **P3** | Stale changelog and architecture docs | Update documentation to match actual v0.2 state |

---

## Conclusion

PromptGuard has a genuinely valuable core idea — CI/CD gating for LLM behavior — and the v0.1 behavior bundle system (prompt + dataset + schema validation + thresholds) is a solid, working foundation. However, the project is **over-promising and under-delivering** on its v0.2 feature set, and the v0.3-v0.6 vision requires engineering resources that far exceed what a typical early-stage open-source project can sustain.

The most productive path forward would be to:
1. **Be honest about v0.2 status** — mark agent features as "experimental/alpha"
2. **Harden the foundation** — achieve >80% coverage on existing modules, fix security issues
3. **Pick ONE v0.3 bet** — either universal adapters OR statistical testing, not both
4. **Ship real provider integration first** — use official SDKs (openai, anthropic) with tool-calling support before building adapters for agent frameworks
