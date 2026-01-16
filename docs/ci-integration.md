# CI Integration

BehaviorCI is CI-agnostic.

## GitHub Actions

```yaml
- run: behaviorci validate bundles/example/bundle.yaml
- run: behaviorci run bundles/example/bundle.yaml
```

Non-zero exit code blocks the PR.
