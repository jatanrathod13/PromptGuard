# PromptGuard Implementation Plan — PR-by-PR

> **Source**: Based on findings from `REVIEW-plan-challenges.md`
> **Tracking**: Progress and learnings tracked in `FINDINGS.md`
> **Principle**: Each PR is small, reviewable, and independently mergeable.
> **Rule**: No PR ships without tests for the code it touches.

---

## How to Use This Document

- Each PR has a **unique ID** (PR-01, PR-02, etc.) for cross-referencing
- **Depends on** lists hard prerequisites — the PR cannot start until those merge
- **Files touched** gives the exact scope — no scope creep
- **Acceptance criteria** defines "done" — the PR is not merged until all are met
- **Est. size** is a rough t-shirt size (S/M/L/XL) based on line count and complexity
- Phases are sequential; PRs within a phase can often be parallelized

---

## Phase 0: Critical Fixes (Security + Honesty)

> **Goal**: Fix the two P0 issues before any feature work. Stop the bleeding.

---

### PR-01: Replace `eval()` with safe expression evaluator

| Field | Value |
|-------|-------|
| **Priority** | P0 — Security |
| **Depends on** | None |
| **Est. size** | M (~200 lines changed) |
| **Review issue** | Section 2.1 — Arbitrary code execution via `eval()` |

**Problem**: `eval(invariant, {"__builtins__": {}}, context)` is bypassable via `__class__.__subclasses__()` chains. This is an RCE risk in CI pipelines running untrusted bundles from PRs.

**Approach**: Replace `eval()` with `ast.literal_eval` + a custom AST walker that only allows safe operations (comparisons, attribute access on whitelisted names, `len()`, `isinstance()`, arithmetic). Alternatively, adopt the `asteval` library.

**Files touched**:
- `promptguard/runner/evaluator.py` — Replace `_evaluate_invariant()` (lines 130-166)
- `promptguard/agent/evaluator.py` — Replace `_evaluate_invariants()` (lines 363-433)
- `promptguard/safe_eval.py` — **New file**: shared safe expression evaluator
- `tests/test_safe_eval.py` — **New file**: comprehensive tests including attack vectors
- `tests/runner/test_evaluator.py` — **New file**: tests for invariant evaluation
- `pyproject.toml` — Add `asteval` dependency if using library approach

**Acceptance criteria**:
- [ ] `eval()` removed from entire codebase (grep confirms zero occurrences)
- [ ] Safe evaluator passes all existing invariant expressions (`len(raw_output) < 500`, etc.)
- [ ] Safe evaluator blocks known attack vectors (`__class__.__subclasses__()`, `__import__`, `exec`, `compile`, `getattr` on arbitrary objects)
- [ ] Tests cover: valid expressions, type errors, syntax errors, security bypass attempts
- [ ] Existing tests still pass

---

### PR-02: Mark agent features as experimental, fix docs honesty

| Field | Value |
|-------|-------|
| **Priority** | P0 — Trust |
| **Depends on** | None |
| **Est. size** | S (~100 lines changed) |
| **Review issue** | Sections 1.1, 5.2, 5.3, 6.1, 6.3 |

**Problem**: README and roadmap claim agent features are "complete" when they are stub implementations. CHANGELOG is stale. Roadmap conflicts with vision doc.

**Files touched**:
- `README.md` — Add "experimental" badges to agent features in comparison table; add honest status section
- `CHANGELOG.md` — Add v0.2.0 release notes documenting what actually works vs. what's experimental
- `docs/roadmap.md` — Reconcile with `agentic-platform-vision.md`; mark single source of truth
- `docs/architecture.md` — Add v0.2 modules (agent, baseline, diff, integrations) to architecture diagram
- `promptguard/agent/__init__.py` — Add deprecation/experimental warning on import

**Acceptance criteria**:
- [ ] README comparison table distinguishes "working" vs. "experimental" features
- [ ] CHANGELOG has a complete v0.2.0 entry
- [ ] `roadmap.md` and `agentic-platform-vision.md` no longer contradict (one is canonical, other references it)
- [ ] Architecture docs include all current modules

---

## Phase 1: Test Coverage for Existing Code

> **Goal**: Reach >70% coverage before adding any new features.
> All PRs in this phase are independent and can be worked on in parallel.

---

### PR-03: Tests for baseline module

| Field | Value |
|-------|-------|
| **Priority** | P0 — Coverage |
| **Depends on** | None |
| **Est. size** | M (~200 lines added) |
| **Review issue** | Section 1.2 — 0% coverage on baseline/ |

**Files touched**:
- `tests/baseline/__init__.py` — **New file**
- `tests/baseline/test_models.py` — **New file**: BaselineRun serialization, BaselineStorage operations
- `tests/baseline/test_storage.py` — **New file**: Save/load/delete/list with temp dirs, atomic write safety, corrupt file handling

**Acceptance criteria**:
- [ ] `baseline/models.py` coverage >90%
- [ ] `baseline/storage.py` coverage >85%
- [ ] Tests cover: round-trip serialization, missing files, corrupt JSON, concurrent access edge cases
- [ ] All tests pass in CI

---

### PR-04: Tests for diff module

| Field | Value |
|-------|-------|
| **Priority** | P0 — Coverage |
| **Depends on** | None |
| **Est. size** | M (~200 lines added) |
| **Review issue** | Section 1.2 — 0% coverage on diff/ |

**Files touched**:
- `tests/diff/__init__.py` — **New file**
- `tests/diff/test_models.py` — **New file**: DiffType enum, DiffEntry construction, DiffResult properties
- `tests/diff/test_comparator.py` — **New file**: Compare cases (new failure, fixed, regression, unchanged), metric changes, empty baselines

**Acceptance criteria**:
- [ ] `diff/models.py` coverage >90%
- [ ] `diff/comparator.py` coverage >85%
- [ ] Tests cover: all DiffType values, edge cases (empty baseline, empty current, identical runs)

---

### PR-05: Tests for reporter modules

| Field | Value |
|-------|-------|
| **Priority** | P0 — Coverage |
| **Depends on** | None |
| **Est. size** | M (~250 lines added) |
| **Review issue** | Section 1.2 — 0% coverage on reporters/ |

**Files touched**:
- `tests/reporters/__init__.py` — **New file**
- `tests/reporters/test_console.py` — **New file**: Verify console output formatting
- `tests/reporters/test_json_reporter.py` — **New file**: Verify JSON output is valid and contains expected fields
- `tests/reporters/test_markdown.py` — **New file**: Verify markdown tables render correctly
- `tests/reporters/test_registry.py` — **New file**: Registration, lookup, list

**Acceptance criteria**:
- [ ] Each reporter module coverage >80%
- [ ] Reporter registry tests cover: register, get, list, missing reporter error
- [ ] Output format tests verify structure (valid JSON, markdown table syntax, etc.)

---

### PR-06: Tests for agent module (as-is)

| Field | Value |
|-------|-------|
| **Priority** | P0 — Coverage |
| **Depends on** | PR-01 (safe eval used in agent evaluator) |
| **Est. size** | L (~350 lines added) |
| **Review issue** | Section 1.2 — 0% coverage on agent/ |

**Files touched**:
- `tests/agent/__init__.py` — **New file**
- `tests/agent/test_models.py` — **New file**: All agent dataclasses/Pydantic models
- `tests/agent/test_loader.py` — **New file**: Agent bundle YAML parsing, validation
- `tests/agent/test_evaluator.py` — **New file**: Tool usage eval, output eval, safety eval, invariant eval
- `tests/agent/test_runner.py` — **New file**: AgentRunner with mock provider, SimpleToolExecutor, tool call extraction

**Acceptance criteria**:
- [ ] `agent/models.py` coverage >85%
- [ ] `agent/loader.py` coverage >80%
- [ ] `agent/evaluator.py` coverage >80%
- [ ] `agent/runner.py` coverage >75%
- [ ] Tests document current limitations (e.g., regex tool extraction, simulated execution)

---

### PR-07: Tests for CLI (smoke tests) and GitHub integration

| Field | Value |
|-------|-------|
| **Priority** | P1 — Coverage |
| **Depends on** | None |
| **Est. size** | M (~200 lines added) |
| **Review issue** | Sections 1.2, 2.2 |

**Files touched**:
- `tests/test_cli.py` — **New file**: Click CliRunner smoke tests for `init`, `validate`, `run` commands
- `tests/integrations/__init__.py` — **New file**
- `tests/integrations/test_github.py` — **New file**: PR URL parsing, comment formatting, CI env detection
- `promptguard/integrations/github.py` — Replace `import requests` with `httpx` (already a dependency)

**Acceptance criteria**:
- [ ] CLI smoke tests verify: `--help` works, `init` creates files, `validate` catches errors
- [ ] GitHub integration: PR URL parsing tested, `_format_comment()` tested, `requests` import removed
- [ ] No undeclared dependencies remain (grep for `import requests`)

---

## Phase 2: Provider Layer Rearchitecture

> **Goal**: Make providers capable of tool-calling conversations, not just text-in/text-out.
> This is the prerequisite for real agent testing. Each PR builds on the previous.

---

### PR-08: Extend provider base with messages API support

| Field | Value |
|-------|-------|
| **Priority** | P1 — Architecture |
| **Depends on** | Phase 1 complete (tests exist to catch regressions) |
| **Est. size** | M (~150 lines changed) |
| **Review issue** | Section 3.1 — Provider layer can't support agents |

**Problem**: `generate(prompt: str)` is text-in/text-out. Agents need `chat(messages, tools, system)`.

**Approach**: Add a `chat()` method to `LLMProvider` alongside existing `generate()`. Keep `generate()` for backward compatibility (it calls `chat()` internally). Add shared `httpx.AsyncClient` lifecycle.

**Files touched**:
- `promptguard/providers/base.py` — Add `Message`, `ToolDefinition` dataclasses; add `chat()` abstract method; add client lifecycle (`_client`, `aclose()`)
- `promptguard/providers/mock.py` — Implement `chat()` with tool-call simulation support
- `tests/providers/test_mock.py` — Add tests for `chat()` method
- `tests/providers/test_base.py` — **New file**: Test Message/ToolDefinition models

**Acceptance criteria**:
- [ ] `LLMProvider` has both `generate(prompt)` and `chat(messages, tools, system)` methods
- [ ] `generate()` is implemented in terms of `chat()` (single user message, no tools)
- [ ] `MockProvider.chat()` can return canned tool-call responses
- [ ] All existing tests still pass (backward compatible)
- [ ] Shared `httpx.AsyncClient` pattern documented

---

### PR-09: Implement OpenAI provider with tool calling + connection pooling

| Field | Value |
|-------|-------|
| **Priority** | P1 — Architecture |
| **Depends on** | PR-08 |
| **Est. size** | M (~150 lines changed) |
| **Review issue** | Sections 3.1, 3.3 |

**Files touched**:
- `promptguard/providers/openai.py` — Implement `chat()` with OpenAI tool-calling format; use shared `httpx.AsyncClient`; update default model to current (e.g., `gpt-4o-mini`)
- `tests/providers/test_openai.py` — **New file**: Unit tests with mocked HTTP responses (httpx mock)
- `pyproject.toml` — Consider adding `respx` (httpx mock library) to dev dependencies

**Acceptance criteria**:
- [ ] `OpenAIProvider.chat()` sends proper tool definitions in OpenAI format
- [ ] `OpenAIProvider.chat()` parses tool_calls from response
- [ ] Connection pooling: single `httpx.AsyncClient` reused across calls
- [ ] Unit tests mock HTTP layer (no real API calls in CI)
- [ ] Default model updated from deprecated to current

---

### PR-10: Implement Anthropic provider with tool calling + connection pooling

| Field | Value |
|-------|-------|
| **Priority** | P1 — Architecture |
| **Depends on** | PR-08 |
| **Est. size** | M (~150 lines changed) |
| **Review issue** | Sections 3.1, 3.3, 5.4 |

**Files touched**:
- `promptguard/providers/anthropic.py` — Implement `chat()` with Anthropic tool-use format; use shared `httpx.AsyncClient`; update default model from `claude-3-haiku-20240307` to current
- `tests/providers/test_anthropic.py` — **New file**: Unit tests with mocked HTTP responses

**Acceptance criteria**:
- [ ] `AnthropicProvider.chat()` sends tools in Anthropic format (`input_schema`, etc.)
- [ ] `AnthropicProvider.chat()` parses `tool_use` content blocks from response
- [ ] Default model updated to non-deprecated model
- [ ] Connection pooling implemented
- [ ] Unit tests with mocked HTTP (no real API calls)

---

### PR-11: Add rate limiting for parallel execution

| Field | Value |
|-------|-------|
| **Priority** | P1 — Reliability |
| **Depends on** | PR-08 |
| **Est. size** | S (~100 lines added) |
| **Review issue** | Section 3.4 — No rate limiting |

**Files touched**:
- `promptguard/providers/rate_limiter.py` — **New file**: Token bucket or sliding window rate limiter (asyncio-based)
- `promptguard/providers/base.py` — Integrate rate limiter into `generate()` and `chat()` calls
- `promptguard/bundle/models.py` — Add `rate_limit` field to `ProviderConfig` (requests per minute)
- `tests/providers/test_rate_limiter.py` — **New file**: Verify rate limiting behavior

**Acceptance criteria**:
- [ ] Rate limiter respects configured RPM (requests per minute)
- [ ] Default RPM is sensible (e.g., 60 RPM for OpenAI, configurable per bundle)
- [ ] Parallel execution with rate limiting works correctly under `asyncio.gather`
- [ ] Rate limiter is optional (no performance impact when disabled)

---

## Phase 3: Agent Module Rebuild

> **Goal**: Make agent testing work with real provider tool calling instead of regex parsing.

---

### PR-12: Rebuild agent runner to use provider `chat()` with real tool calling

| Field | Value |
|-------|-------|
| **Priority** | P1 — Core Feature |
| **Depends on** | PR-08, PR-09 or PR-10 (at least one real provider) |
| **Est. size** | L (~300 lines changed) |
| **Review issue** | Sections 1.1, 3.2 |

**Problem**: `AgentRunner._extract_tool_calls()` uses regex to parse tool calls from text output. `_build_tools_spec()` returns empty list. `_generate_with_tools()` falls back to plain `generate()`.

**Approach**: Rewrite `AgentRunner` to use `provider.chat()` with proper tool definitions. Remove regex extraction. Use structured tool_calls from provider response.

**Files touched**:
- `promptguard/agent/runner.py` — Rewrite `_generate_with_tools()` to use `provider.chat()`; remove `_extract_tool_calls()` and `_parse_simple_args()`; rewrite `_build_tools_spec()` to return actual tool schemas
- `promptguard/agent/models.py` — Update `ToolCall` to align with provider response format
- `tests/agent/test_runner.py` — Update tests for new chat-based flow

**Acceptance criteria**:
- [ ] Agent runner uses `provider.chat(messages, tools)` not `provider.generate(prompt)`
- [ ] Tool calls come from structured provider response, not regex parsing
- [ ] Regex-based `_extract_tool_calls()` removed entirely
- [ ] Multi-turn loop works: user → assistant(tool_call) → tool_result → assistant → ...
- [ ] Tests verify tool calling flow with MockProvider

---

### PR-13: Implement LLM-as-judge evaluator

| Field | Value |
|-------|-------|
| **Priority** | P1 — Core Feature |
| **Depends on** | PR-08 (needs provider with chat) |
| **Est. size** | M (~200 lines added) |
| **Review issue** | Section 1.1 — LLM judge is placeholder |

**Problem**: `agent/evaluator.py:282-284` just sets a note: "LLM judge not implemented yet".

**Files touched**:
- `promptguard/evaluators/__init__.py` — **New file**
- `promptguard/evaluators/llm_judge.py` — **New file**: LLMJudge class that sends (rubric + agent output) to a judge model, parses score
- `promptguard/agent/evaluator.py` — Wire LLM judge into `_evaluate_output()` and `_evaluate_task_completion()`
- `tests/evaluators/__init__.py` — **New file**
- `tests/evaluators/test_llm_judge.py` — **New file**: Test with mock provider returning structured scores

**Acceptance criteria**:
- [ ] LLM judge sends rubric + context to configurable judge model
- [ ] Supports both `numeric` (1-5 scale) and `boolean` scoring modes
- [ ] Rubric is configurable per bundle YAML
- [ ] Judge model is configurable (can be different from agent model)
- [ ] Tests use MockProvider to verify prompt construction and score parsing
- [ ] Graceful failure: if judge call fails, evaluation is marked as error (not silent pass)

---

### PR-14: Replace simulated tool execution with pluggable executors

| Field | Value |
|-------|-------|
| **Priority** | P2 — Quality |
| **Depends on** | PR-12 |
| **Est. size** | M (~150 lines changed) |
| **Review issue** | Section 1.1 — Tool execution is fully simulated |

**Problem**: `SimpleToolExecutor._simulate_tool()` returns hardcoded fake responses. Real agent testing needs real tool execution or at least configurable mock responses.

**Files touched**:
- `promptguard/agent/runner.py` — Refactor `ToolExecutor` protocol; add `ConfigurableToolExecutor` that returns user-defined responses from YAML
- `promptguard/agent/models.py` — Add `tool_responses` field to agent bundle config for defining expected tool outputs
- `tests/agent/test_runner.py` — Test configurable executor

**Acceptance criteria**:
- [ ] Users can define tool responses in agent bundle YAML (deterministic testing without real execution)
- [ ] `SimpleToolExecutor` clearly marked as development-only fallback
- [ ] `ToolExecutor` protocol allows custom implementations for real execution
- [ ] Test coverage for configurable executor >90%

---

## Phase 4: New Capabilities

> **Goal**: Add the features that make PromptGuard genuinely differentiated.

---

### PR-15: Multi-trial execution engine

| Field | Value |
|-------|-------|
| **Priority** | P2 — Differentiation |
| **Depends on** | PR-11 (rate limiting), PR-12 (agent runner) |
| **Est. size** | L (~300 lines added) |
| **Review issue** | Section 4.3, 7.3 — Non-determinism handling |

**Problem**: Single-run evaluation produces unreliable CI results due to LLM non-determinism.

**Files touched**:
- `promptguard/runner/trials.py` — **New file**: `TrialRunner` wrapping `Runner` or `AgentRunner` with N trials per case
- `promptguard/runner/statistics.py` — **New file**: Confidence intervals, variance detection, pass rate with significance
- `promptguard/bundle/models.py` — Add `trials` and `confidence_level` fields to `BundleConfig`
- `promptguard/cli.py` — Add `--trials` flag to `run` command
- `tests/runner/test_trials.py` — **New file**
- `tests/runner/test_statistics.py` — **New file**

**Acceptance criteria**:
- [ ] `--trials N` runs each test case N times
- [ ] Results report mean pass rate with confidence interval
- [ ] High-variance cases are flagged (variance > configurable threshold)
- [ ] Default is `trials=1` (backward compatible, no behavior change)
- [ ] Statistics module has >90% test coverage (math must be correct)
- [ ] Works with both behavior bundles and agent bundles

---

### PR-16: Cost tracking per run

| Field | Value |
|-------|-------|
| **Priority** | P2 — Observability |
| **Depends on** | PR-08 (provider responses include usage) |
| **Est. size** | S (~120 lines added) |
| **Review issue** | Section 4.3 — Cost awareness for multi-trial |

**Files touched**:
- `promptguard/runner/cost.py` — **New file**: Token-to-dollar conversion using provider pricing tables; `CostTracker` class
- `promptguard/runner/engine.py` — Integrate cost tracking into `RunResult`
- `promptguard/bundle/models.py` — Add optional `max_cost` threshold
- `tests/runner/test_cost.py` — **New file**

**Acceptance criteria**:
- [ ] Cost tracked per case and per run (total)
- [ ] `max_cost` threshold works as a CI gate
- [ ] Pricing tables for OpenAI and Anthropic (configurable, with sensible defaults)
- [ ] Cost appears in console, JSON, and markdown reporter output

---

### PR-17: Safe expression DSL (replace raw Python invariants)

| Field | Value |
|-------|-------|
| **Priority** | P2 — DX + Security hardening |
| **Depends on** | PR-01 (safe eval foundation) |
| **Est. size** | M (~200 lines) |
| **Review issue** | Section 7.2 — Invariant expressions are a poor language |

**Problem**: Even with `eval()` replaced, Python expression strings in YAML have no IDE support, no error context, and are opaque to non-Python users.

**Approach**: Build a small assertion DSL inspired by PromptFoo's syntax:
- `output.length < 500`
- `output.contains("hello")`
- `output.json.answer.type == "string"`
- `output.json.confidence >= 0.8`

**Files touched**:
- `promptguard/safe_eval.py` — Extend with DSL parser (or replace entirely)
- `promptguard/runner/evaluator.py` — Use DSL for invariant evaluation
- `promptguard/agent/evaluator.py` — Use DSL for invariant evaluation
- `docs/behavior-bundles.md` — Document new expression syntax
- `tests/test_safe_eval.py` — Extend with DSL test cases

**Acceptance criteria**:
- [ ] New DSL supports: comparisons, string operations (contains, startsWith, endsWith, matches), JSON path access, length, type checks
- [ ] Old Python expression syntax still works (backward compatible) but emits deprecation warning
- [ ] Error messages include the expression text and what went wrong
- [ ] Documentation updated with examples
- [ ] Zero security risk (no arbitrary code execution possible)

---

## Phase 5: First Framework Adapter

> **Goal**: Prove the adapter pattern with one framework before expanding.
> Pick OpenAI Agents SDK — it's the most structured and has OTel support.

---

### PR-18: TestableAgent protocol and AgentTrace data model

| Field | Value |
|-------|-------|
| **Priority** | P2 — Platform |
| **Depends on** | PR-12 (rebuilt agent runner) |
| **Est. size** | M (~200 lines added) |
| **Review issue** | Section 4.2 — Framework adapter pattern |

**Files touched**:
- `promptguard/adapters/__init__.py` — **New file**
- `promptguard/adapters/base.py` — **New file**: `TestableAgent` Protocol, `AgentTrace` dataclass, `AgentConfig` dataclass
- `promptguard/agent/runner.py` — Accept `TestableAgent` as input (in addition to raw provider)
- `tests/adapters/__init__.py` — **New file**
- `tests/adapters/test_base.py` — **New file**: Protocol compliance tests

**Acceptance criteria**:
- [ ] `TestableAgent` protocol defined with `run()`, `get_tools()`, `get_config()`
- [ ] `AgentTrace` captures: steps, tool calls with args/results, token usage, timing, final output
- [ ] Data model is framework-agnostic (no framework-specific imports)
- [ ] Agent runner can accept either a `TestableAgent` or raw provider config

---

### PR-19: OpenAI Agents SDK adapter

| Field | Value |
|-------|-------|
| **Priority** | P2 — Platform |
| **Depends on** | PR-18 |
| **Est. size** | M (~200 lines added) |
| **Review issue** | Section 4.2 |

**Files touched**:
- `promptguard/adapters/openai_agents.py` — **New file**: `wrap_openai_agent()` function implementing `TestableAgent`
- `tests/adapters/test_openai_agents.py` — **New file**: Tests with mocked OpenAI Agents SDK
- `pyproject.toml` — Add `openai-agents` as optional dependency (`[openai-agents]` extra)

**Acceptance criteria**:
- [ ] `wrap_openai_agent(agent)` returns a `TestableAgent`
- [ ] Captures tool calls, handoffs, and final output as `AgentTrace`
- [ ] Works without openai-agents installed (graceful ImportError with helpful message)
- [ ] Tests don't require real OpenAI API key

---

### PR-20: Python SDK — `promptguard.test()` API

| Field | Value |
|-------|-------|
| **Priority** | P2 — DX |
| **Depends on** | PR-18, PR-13 (LLM judge) |
| **Est. size** | M (~200 lines added) |
| **Review issue** | Vision doc — Python-first SDK |

**Files touched**:
- `promptguard/sdk.py` — **New file**: `test()` function, `TestResult` dataclass, programmatic API
- `promptguard/__init__.py` — Export `test`, `TestResult`
- `tests/test_sdk.py` — **New file**: End-to-end SDK usage with mock agents
- `docs/sdk.md` — **New file**: Python SDK documentation with examples

**Acceptance criteria**:
- [ ] `promptguard.test(agent=..., dataset=..., evaluators=..., thresholds=...)` works
- [ ] Returns `TestResult` with `.passed`, `.metrics`, `.case_results`
- [ ] Works in pytest: `assert promptguard.test(...).passed`
- [ ] Documentation includes quickstart example

---

## Phase 6: Integration & Polish

> **Goal**: Connect to the ecosystem. Only after core is solid.

---

### PR-21: Langfuse trace ingestion

| Field | Value |
|-------|-------|
| **Priority** | P3 — Integration |
| **Depends on** | PR-18 (AgentTrace model) |
| **Est. size** | M (~200 lines added) |

**Files touched**:
- `promptguard/traces/__init__.py` — **New file**
- `promptguard/traces/langfuse.py` — **New file**: `LangfuseTraceSource`, `traces_to_dataset()`
- `tests/traces/test_langfuse.py` — **New file**: Tests with mocked Langfuse API responses
- `pyproject.toml` — Add `langfuse` as optional dependency

**Acceptance criteria**:
- [ ] Can pull traces from Langfuse by tag, date range, score
- [ ] Converts traces to JSONL dataset format for regression testing
- [ ] Works without langfuse installed (graceful import error)
- [ ] Tests mock Langfuse API (no real credentials needed)

---

### PR-22: GitHub Action v2

| Field | Value |
|-------|-------|
| **Priority** | P3 — CI/CD |
| **Depends on** | PR-15 (multi-trial), PR-16 (cost tracking) |
| **Est. size** | M (~150 lines) |

**Files touched**:
- `.github/actions/promptguard/action.yml` — **New file**: Composite GitHub Action
- `.github/workflows/ci.yaml` — Update to use new action
- `promptguard/integrations/github.py` — Enhance comment formatting with trial stats and cost info
- `tests/integrations/test_github.py` — Update tests

**Acceptance criteria**:
- [ ] GitHub Action supports: `bundles`, `trials`, `format` inputs
- [ ] PR comments include: pass/fail, metrics, regressions, cost summary
- [ ] Action works with both behavior and agent bundles

---

### PR-23: PromptFoo red-team delegation

| Field | Value |
|-------|-------|
| **Priority** | P3 — Integration |
| **Depends on** | PR-18 (TestableAgent), PR-20 (SDK) |
| **Est. size** | L (~300 lines added) |

**Files touched**:
- `promptguard/integrations/promptfoo.py` — **New file**: Config generation, subprocess execution, result parsing
- `promptguard/agent/models.py` — Add `security` config section to agent bundle
- `tests/integrations/test_promptfoo.py` — **New file**: Tests with mocked subprocess

**Acceptance criteria**:
- [ ] Generates valid PromptFoo config from agent bundle security section
- [ ] Wraps agent as HTTP provider for PromptFoo consumption
- [ ] Parses PromptFoo JSON results and integrates into quality gate
- [ ] Works without PromptFoo installed (graceful error with install instructions)
- [ ] Tests don't require PromptFoo installed

---

## Dependency Graph

```
PR-01 (safe eval) ─────────────────────────────────────────────────┐
PR-02 (docs honesty)                                               │
                                                                    │
PR-03 (baseline tests) ──────┐                                     │
PR-04 (diff tests) ──────────┤                                     │
PR-05 (reporter tests) ──────┼── Phase 1 done ──┐                  │
PR-06 (agent tests) ─────────┤  (depends PR-01) │                  │
PR-07 (CLI + GH tests) ──────┘                   │                  │
                                                   │                  │
                              PR-08 (provider base) ◄── Phase 1 ────┘
                              ┌──┴──┐
                          PR-09   PR-10          PR-11
                         (OpenAI) (Anthropic)   (rate limit)
                              └──┬──┘              │
                                 │                  │
                              PR-12 (agent rebuild) ◄┘
                              ┌──┴──┐
                          PR-13    PR-14
                        (LLM judge) (tool exec)
                              │
                         PR-15 (multi-trial) ◄── PR-11
                              │
                         PR-16 (cost tracking)
                              │
PR-17 (DSL) ◄── PR-01        │
                              │
                         PR-18 (TestableAgent)
                         ┌────┼────┐
                     PR-19  PR-20  PR-21
                    (OAI)  (SDK)  (Langfuse)
                              │
                     PR-22 (GH Action v2) ◄── PR-15, PR-16
                              │
                     PR-23 (PromptFoo)
```

---

## Release Milestones

| Milestone | PRs Included | Version | Outcome |
|-----------|-------------|---------|---------|
| **Security & Honesty** | PR-01, PR-02 | v0.2.1 | Safe eval, honest docs |
| **Test Coverage** | PR-03 through PR-07 | v0.2.2 | >70% coverage |
| **Provider Rearchitecture** | PR-08 through PR-11 | v0.3.0-alpha | Tool calling works |
| **Agent Rebuild** | PR-12 through PR-14 | v0.3.0-beta | Real agent testing |
| **Statistical Testing** | PR-15, PR-16, PR-17 | v0.3.0 | Multi-trial, cost tracking, safe DSL |
| **Platform** | PR-18 through PR-20 | v0.4.0-alpha | First adapter, Python SDK |
| **Integrations** | PR-21 through PR-23 | v0.4.0 | Langfuse, GitHub, PromptFoo |
