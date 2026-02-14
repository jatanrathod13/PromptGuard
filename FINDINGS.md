# PromptGuard — Findings, Key Learnings & Mistakes Log

> **Purpose**: Living document to track discoveries, patterns, anti-patterns, and mistakes
> found during the review and implementation of PromptGuard.
> **How to use**: Add entries as you work. Reference PR IDs from `IMPLEMENTATION-PLAN.md`.
> Each entry should be actionable — not just "X is bad" but "X is bad because Y, fix with Z."

---

## Table of Contents

1. [Security Findings](#1-security-findings)
2. [Architecture & Design Findings](#2-architecture--design-findings)
3. [Code Quality Findings](#3-code-quality-findings)
4. [Testing Findings](#4-testing-findings)
5. [Documentation & Process Findings](#5-documentation--process-findings)
6. [Strategic & Competitive Findings](#6-strategic--competitive-findings)
7. [Mistakes Made (Pre-Review)](#7-mistakes-made-pre-review)
8. [Lessons for Future Development](#8-lessons-for-future-development)

---

## 1. Security Findings

### F-SEC-01: `eval()` with `__builtins__={}` is NOT a sandbox

- **Where**: `runner/evaluator.py:161`, `agent/evaluator.py:412`
- **Severity**: Critical (RCE)
- **Detail**: Setting `{"__builtins__": {}}` prevents direct use of built-in functions like `open()` or `__import__()`, but does NOT prevent access through object introspection chains. Any object in the eval context exposes `__class__.__mro__[1].__subclasses__()` which can reach `os._wrap_close`, `subprocess.Popen`, etc.
- **Proof of concept**: `().__class__.__mro__[1].__subclasses__()[132].__init__.__globals__["system"]("whoami")` — the exact index varies by Python version but the technique is well-documented.
- **Attack surface**: CI pipelines running bundles from PRs authored by untrusted contributors. Malicious invariant expression in a `bundle.yaml` = arbitrary code execution on the CI runner.
- **Fix**: PR-01 replaces with AST-based safe evaluator that whitelists allowed operations.
- **Lesson**: `eval()` with restricted builtins is a known anti-pattern. Never use `eval()` on user-supplied input regardless of `__builtins__` restrictions. This is explicitly called out in Python's own documentation.

### F-SEC-02: Undeclared `requests` dependency

- **Where**: `integrations/github.py:136`
- **Severity**: Low (functionality gap, not exploitable)
- **Detail**: `import requests` at runtime inside `_post_via_api()`. The `requests` library is not in `pyproject.toml` dependencies. If it happens to be installed as a transitive dependency, it's used without version pinning. If not installed, the REST API fallback silently fails and returns `False`.
- **Fix**: PR-07 replaces with `httpx` (already a declared dependency).
- **Lesson**: Never use runtime imports for undeclared dependencies. If a feature needs a library, either declare it as a dependency or as an optional extra with a clear error message on import failure.

---

## 2. Architecture & Design Findings

### F-ARCH-01: Provider interface is text-only — can't support tool calling

- **Where**: `providers/base.py` — `generate(prompt: str) -> ProviderResponse`
- **Impact**: Blocks all agent testing functionality
- **Detail**: The LLM provider abstraction only supports single text prompt → text response. Modern LLM APIs (OpenAI, Anthropic) support structured tool calling through messages API with tool definitions. The agent module tries to work around this by parsing tool calls from raw text using regex (`agent/runner.py:378-425`), which is fundamentally unreliable.
- **Root cause**: v0.1 was designed only for prompt testing (send prompt, check output). Agent testing was bolted on top of the same interface rather than rearchitecting the foundation.
- **Fix**: PR-08 adds `chat(messages, tools, system)` method to provider base.
- **Lesson**: When adding a feature that needs different capabilities from the core abstraction, extend the abstraction first — don't hack around it with string parsing.

### F-ARCH-02: New HTTP client per request destroys connection pooling

- **Where**: `providers/openai.py:91`, `providers/anthropic.py:95`
- **Impact**: Performance — 10x slower under parallel load
- **Detail**: `async with httpx.AsyncClient() as client:` inside each `generate()` call creates a new TCP connection (including TLS handshake) for every request. With parallel execution of 50 test cases, this means 50 concurrent TLS handshakes to the same host. An `httpx.AsyncClient` instance with connection pooling can reuse connections, reducing latency from ~200ms to ~20ms per request after warmup.
- **Fix**: PR-09/PR-10 move to shared client instances with lifecycle management.
- **Lesson**: HTTP clients should be created once and reused. This is the default advice in httpx documentation and applies to all HTTP client libraries (requests.Session, aiohttp.ClientSession, etc.).

### F-ARCH-03: Agent runner is both executor and test harness

- **Where**: `agent/runner.py`
- **Impact**: Wrong abstraction — tests PromptGuard's agent loop, not the user's agent
- **Detail**: `AgentRunner` re-implements a multi-turn agent loop (conversation management, tool dispatch, step counting) instead of wrapping an existing agent framework. This means: (a) the tool execution logic is PromptGuard's own simulation, not real agent behavior; (b) users can't test their actual agents — they'd have to redefine them in PromptGuard's format; (c) PromptGuard becomes an agent framework rather than a testing tool.
- **Desired state**: PromptGuard wraps any agent (OpenAI, LangChain, etc.) via an adapter, observes its execution, and evaluates the trace. The agent's own framework handles execution; PromptGuard only tests and evaluates.
- **Fix**: PR-12 (rebuild runner) + PR-18 (TestableAgent protocol).
- **Lesson**: A testing tool should observe and evaluate, not re-implement the thing it's testing. This is the same principle as testing a web app by making HTTP requests to it, not by reimplementing the web framework.

### F-ARCH-04: No rate limiting makes parallel execution dangerous

- **Where**: `runner/engine.py:188-203` — `_run_parallel()` uses naked `asyncio.gather()`
- **Impact**: API rate limit errors in production use
- **Detail**: `asyncio.gather(*tasks)` with no semaphore or rate limiter fires all requests simultaneously. OpenAI's default rate limit is ~500 RPM for GPT-4o-mini. A bundle with 100 test cases at 3 retries each = up to 300 concurrent requests.
- **Fix**: PR-11 adds configurable rate limiting.
- **Lesson**: Any feature that makes concurrent API calls needs rate limiting from day one. It should be considered part of the feature, not a follow-up.

---

## 3. Code Quality Findings

### F-CODE-01: Largest file is CLI at 1,176 lines with zero tests

- **Where**: `promptguard/cli.py`
- **Impact**: High change risk, no safety net
- **Detail**: The CLI file contains 520 statements, embedded example templates (YAML, markdown, JSON, JSONL), and all command implementations. It's the user-facing entry point but has no test coverage. Any refactoring or feature addition to CLI commands risks breaking user workflows with no automated detection.
- **Fix**: PR-07 adds CLI smoke tests.
- **Lesson**: CLI is the most user-facing code and should be tested first, not last. Use Click's `CliRunner` for unit testing CLI commands.

### F-CODE-02: Agent module is the largest module (1,616 lines) with 0% coverage

- **Where**: `promptguard/agent/` — 5 files, zero tests
- **Impact**: Impossible to refactor safely
- **Detail**: The agent module was written in one pass (presumably for the v0.2 release) without any tests. The models file alone is 521 lines of dataclasses and Pydantic models. Without tests, any change to this module is a gamble.
- **Fix**: PR-06 adds tests for agent module as-is, before any refactoring.
- **Lesson**: Write tests alongside code, not after. Shipping an untested module creates a testing debt that compounds with each change.

### F-CODE-03: Diff reporter is 503 lines — largest reporter by far

- **Where**: `promptguard/reporters/diff.py`
- **Impact**: Complexity, untested
- **Detail**: The diff reporter is ~4x larger than any other reporter. It likely contains rendering logic that should be broken into smaller functions. With 0% test coverage, output formatting bugs can slip through.
- **Fix**: PR-05 adds reporter tests.

### F-CODE-04: Duplicate evaluation logic between runner and agent evaluator

- **Where**: `runner/evaluator.py` and `agent/evaluator.py`
- **Impact**: Maintenance burden, inconsistency risk
- **Detail**: Both files implement JSON schema validation, invariant evaluation, and Python `eval()` with nearly identical logic. Changes to one must be mirrored in the other. The safe eval fix (PR-01) must update both files.
- **Fix**: PR-01 extracts shared logic into `safe_eval.py`. Future refactoring should further consolidate evaluation into a single module.
- **Lesson**: DRY (Don't Repeat Yourself) is especially important for security-sensitive code. If evaluation logic needs to change, having it in two places doubles the risk of missing one.

---

## 4. Testing Findings

### F-TEST-01: Overall coverage is 17% — far below credible threshold

- **Where**: Project-wide
- **Impact**: Cannot safely make changes
- **Detail**: Only 442 lines of tests for 6,795 lines of source code. The tested modules are: bundle (dataset, loader, models), mock provider, runner engine. Everything else — agent, baseline, diff, reporters, CLI, integrations, real providers — is untested.
- **Target**: >70% coverage after Phase 1 (PR-03 through PR-07).
- **Lesson**: For a project whose value proposition is "CI/CD for testing," having poor test coverage is an ironic and damaging credibility issue.

### F-TEST-02: Test isolation issue — pytest from different Python env fails

- **Where**: CI environment
- **Impact**: Flaky development setup
- **Detail**: Running `pytest tests/ -v` (standalone pytest binary) fails with `ModuleNotFoundError: No module named 'yaml'` even though PyYAML is installed in the system Python. This happens because the `pytest` binary was installed by `uv` into a different Python environment than where `pip install -e ".[dev]"` installed the package. Running `python -m pytest tests/ -v` works correctly because it uses the same Python that has the dependencies.
- **Root cause**: `pyproject.toml` pytest config uses `asyncio_mode` which is not recognized by all pytest versions, causing warnings. The test runner path divergence causes import failures.
- **Fix**: PR-07 should document using `python -m pytest` and/or add a `Makefile` / `justfile` with standardized commands.
- **Lesson**: Always document and test the exact commands developers should use. "It works on my machine" is not a valid test strategy.

### F-TEST-03: No integration tests for real providers

- **Where**: `tests/providers/` — only `test_mock.py` exists
- **Impact**: API changes silently break production functionality
- **Detail**: OpenAI and Anthropic providers construct raw HTTP requests with httpx. There are no tests that verify the request format matches what the APIs expect. If OpenAI changes their endpoint or response format, PromptGuard would break with no test to detect it.
- **Fix**: PR-09 and PR-10 add unit tests with mocked HTTP responses (not real API calls). Optional integration test marked with `pytest.mark.integration` for manual verification.
- **Lesson**: Providers that call external APIs need at least mocked HTTP tests that verify request/response format. Real integration tests should be opt-in (requiring API keys) but available.

### F-TEST-04: Anthropic provider uses deprecated default model

- **Where**: `providers/anthropic.py:53` — `return "claude-3-haiku-20240307"`
- **Impact**: Will break when model is decommissioned
- **Detail**: `claude-3-haiku-20240307` is being deprecated. Default should be updated to a current model.
- **Fix**: PR-10 updates default model.
- **Lesson**: Default model strings should be easy to find and update. Consider making them configurable via environment variable or config file as fallback.

---

## 5. Documentation & Process Findings

### F-DOC-01: CHANGELOG only covers v0.1.0 despite v0.2.0 being released

- **Where**: `CHANGELOG.md`
- **Impact**: Users and contributors can't see what changed
- **Detail**: The changelog lists v0.1.0 changes but v0.2.0 (which added agent bundles, baseline/diff, GitHub integration) has no changelog entry. For an OSS project, this is a significant hygiene gap.
- **Fix**: PR-02.

### F-DOC-02: Two contradictory roadmaps

- **Where**: `docs/roadmap.md` vs `docs/agentic-platform-vision.md`
- **Impact**: Contributor confusion
- **Detail**:
  - `roadmap.md` says: v0.3 = Policy Packs, v0.4 = Enhanced Providers, v0.5 = Advanced Evaluation
  - `agentic-platform-vision.md` says: v0.3 = Universal Adapters, v0.4 = Statistical Engine, v0.5 = Integration Layer, v0.6 = Enterprise
  - These are completely different plans. A contributor reading the roadmap would implement policy packs; one reading the vision doc would implement adapters.
- **Fix**: PR-02 reconciles into single source of truth.
- **Lesson**: When strategy changes, update ALL documents. Having two roadmaps is worse than having none.

### F-DOC-03: Architecture docs missing v0.2 components

- **Where**: `docs/architecture.md`
- **Impact**: Incomplete mental model for new contributors
- **Detail**: Architecture doc only shows v0.1 components (CLI → Bundle Loader → Runner → Providers → Reporters → Exit Code). Missing: agent module, baseline/storage, diff/comparator, integrations/github.
- **Fix**: PR-02.

### F-DOC-04: README comparison table overstates capabilities

- **Where**: `README.md` — feature comparison vs. PromptFoo and Langfuse
- **Impact**: Trust damage when users discover features don't work
- **Detail**: Checkmarks for "Agent tool-calling tests" and "Baseline & diff" imply production-ready features. In reality, agent tool-calling uses regex text parsing with simulated execution, and baseline/diff has zero test coverage.
- **Fix**: PR-02 adds "experimental" qualifiers.
- **Lesson**: Feature comparison tables are powerful marketing but dangerous when they overstate. Users who discover claims are false become detractors, not contributors.

---

## 6. Strategic & Competitive Findings

### F-STRAT-01: "Connective tissue" strategy creates dependency risk

- **Impact**: Strategic risk
- **Detail**: Positioning between Langfuse and PromptFoo means PromptGuard's value depends on both maintaining stable APIs. Neither has incentive to keep integration-friendly (they could build CI gating themselves). Langfuse has already added evaluation features. PromptFoo already has CI integration.
- **Mitigation**: Build independent value first (statistical testing, trajectory evaluation), then add integrations as bonus features, not core dependencies.
- **Lesson**: Never make your core value proposition dependent on a competitor's API stability.

### F-STRAT-02: Six framework adapters are unsustainable for a small team

- **Impact**: Maintenance burden
- **Detail**: The vision proposes adapters for OpenAI Agents SDK, Claude Agent SDK, LangChain/LangGraph, CrewAI, Google ADK, and raw OTel. Each adapter is an ongoing maintenance commitment (framework API changes, new versions, breaking changes). LangChain alone averages breaking changes every few months.
- **Mitigation**: Start with 1 adapter (OpenAI Agents SDK — most structured, has OTel). Prove the pattern works. Add second adapter only after first is stable for 2+ months.
- **Lesson**: Build depth before breadth. One excellent adapter is worth more than six broken ones.

### F-STRAT-03: Multi-trial statistical testing has practical cost/time barriers

- **Impact**: Adoption risk
- **Detail**: 5 trials × 20 tasks = 100 API calls per CI run. At GPT-4o pricing (~$0.03/call), that's $3/run. Teams running CI 20 times/day = $60/day = ~$1,800/month just for testing. At 30 trials for statistical validity, costs 6x higher.
- **Mitigation**: Default to 1 trial (current behavior). Offer 3-trial "quick check" mode. Reserve 5+ trials for nightly/weekly runs. Cache results for unchanged prompts.
- **Lesson**: Features with per-use cost need explicit cost modeling before shipping. Users won't adopt a testing tool that costs more than the product it tests.

### F-STRAT-04: Naming collision with Meta's Prompt-Guard model

- **Impact**: Brand confusion, potential trademark issue
- **Detail**: Meta published "Prompt-Guard-86M" (prompt injection detection model) on HuggingFace. Same domain (LLM safety/testing), similar name. If Meta publishes a PyPI package called `prompt-guard` or `promptguard`, there would be direct package name conflict.
- **Mitigation**: Monitor Meta's package registry activity. Consider proactive rename if project gains traction.

---

## 7. Mistakes Made (Pre-Review)

> These are patterns observed in the existing codebase that should be avoided going forward.

### M-01: Shipping features without tests

- **What happened**: v0.2.0 shipped agent bundles, baseline/diff, and GitHub integration — ~2,800 lines of code — with zero tests.
- **Why it happened**: Likely pressure to ship features quickly, with testing deferred to "later."
- **Consequence**: Cannot safely refactor or extend any v0.2 feature. Every change is a gamble.
- **Prevention**: Enforce rule: no PR merges without tests for new code. Add coverage check to CI (`--cov-fail-under=70`).

### M-02: Building agent execution instead of agent observation

- **What happened**: `agent/runner.py` re-implements a multi-turn agent loop (conversation management, tool dispatch, step counting) instead of wrapping existing agent frameworks.
- **Why it happened**: Likely seemed simpler to build a self-contained agent runner than to design an adapter pattern for multiple frameworks.
- **Consequence**: PromptGuard tests its own agent implementation, not the user's actual agent. Users can't use PromptGuard to test their LangChain/OpenAI/CrewAI agents without redefining them in PromptGuard's format.
- **Prevention**: Before building, ask: "Is this tool testing the user's code, or our code?" If the answer is "our code," the abstraction is wrong.

### M-03: Marketing features before they work

- **What happened**: README comparison table and roadmap mark agent tool-calling, LLM-as-judge, and baseline/diff as "complete" when they're stubs.
- **Why it happened**: Enthusiasm for the vision; desire to position competitively against PromptFoo.
- **Consequence**: Users who try these features find they don't work, damaging trust and credibility.
- **Prevention**: Use "experimental" or "alpha" labels for features that aren't production-ready. Be explicit about what works and what doesn't.

### M-04: Using `eval()` for user-supplied expressions

- **What happened**: Invariant checking uses `eval()` with a restricted `__builtins__` dict.
- **Why it happened**: Quickest way to execute Python expressions from YAML config. The `__builtins__={}` restriction gives a false sense of security.
- **Consequence**: Remote code execution vulnerability in the core CI/CD use case.
- **Prevention**: Never use `eval()` on untrusted input. Use purpose-built expression evaluators. If you need dynamic expressions, use an AST walker with an explicit allowlist of operations.

### M-05: Not using official provider SDKs

- **What happened**: OpenAI and Anthropic providers construct raw HTTP requests with httpx instead of using the official `openai` and `anthropic` Python packages.
- **Why it happened**: Possibly to avoid extra dependencies, or to maintain full control over the HTTP layer.
- **Consequence**: (a) No tool-calling support (would need to implement OpenAI/Anthropic tool-calling protocol manually); (b) No streaming support; (c) API format changes silently break the providers; (d) Missing retry logic, error handling, and edge cases that official SDKs handle.
- **Prevention**: Use official SDKs unless there's a compelling reason not to. The maintenance burden of reimplementing an API client always exceeds the cost of a dependency.

---

## 8. Lessons for Future Development

### L-01: Test coverage is a prerequisite, not a follow-up

Every PR must include tests for the code it changes. The `IMPLEMENTATION-PLAN.md` enforces this: no PR's acceptance criteria can be met without tests. Add `--cov-fail-under=70` to CI after Phase 1.

### L-02: Extend abstractions before building on top of them

When a new feature needs capabilities the current architecture doesn't support (e.g., agent testing needs tool calling, but providers only support text), fix the architecture first. Don't build workarounds (regex parsing) that create technical debt.

### L-03: One adapter, proven, then expand

Framework adapters are ongoing maintenance commitments. Start with the most structured framework (OpenAI Agents SDK), prove the adapter pattern works end-to-end, stabilize it for 2+ months, then add the next adapter. Never ship 6 adapters simultaneously.

### L-04: Cost model before shipping multi-trial

Any feature with per-use API cost needs explicit cost modeling: "This feature will cost X dollars per CI run for a Y-size test suite." Document the cost implications in the feature's documentation. Provide cost-saving defaults (e.g., 1 trial default, caching).

### L-05: Keep security-sensitive code in one place

Evaluation logic (invariant checking, expression parsing) was duplicated between `runner/evaluator.py` and `agent/evaluator.py`. When a security fix is needed, it must be applied in two places — doubling the risk of missing one. Extract shared security-sensitive logic into a single module.

### L-06: Documentation is a contract with users

If the README says a feature works, users will try to use it. If it doesn't work, users become detractors. Treat documentation claims as binding commitments. Use "experimental" labels freely and without shame — users respect honesty more than a polished feature list that lies.

### L-07: CI pipelines need reproducible environments

The test failure caused by pytest running from a different Python environment than where dependencies were installed is a classic reproducibility issue. Use `python -m pytest` (not bare `pytest`) to ensure the same interpreter. Consider adding a `Makefile` with standardized commands.

### L-08: Don't compete with your integration targets

If PromptGuard's strategy depends on Langfuse and PromptFoo, it should build value that neither can replicate (trajectory evaluation, cross-framework testing, statistical significance). It should NOT try to replace their core features (observability, red teaming). Be the bridge, not a lesser copy.

---

## Change Log for This Document

| Date | Section | Change | Author |
|------|---------|--------|--------|
| 2026-02-14 | All | Initial findings from comprehensive code review | Claude |
| | | | |
| | | | |
