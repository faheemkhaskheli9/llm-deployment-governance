# Architecture Notes: LLM Deployment Approval Platform

## Pipeline

```text
Development -> Evaluation -> Review -> Approved -> Production (with audit + rollback at each stage)
```

## Components

- Prompt version tracking
- Model version tracking
- Prompt diff viewer
- Model configuration diff viewer
- Evaluation results attached to each version
- Approval workflow (Dev -> Eval -> Review -> Approved -> Prod)
- Deployment history
- Rollback history
- Audit logs
- Environment promotion pipeline

## Design Notes

- **Phase 1 (`PromptVersion`)** applies the knowledge-base `episodic-memory`
  pattern: versions are immutable, append-only records queried by exact
  key/version, not similarity. See `src/governance/models.py`.

- Keep provider/model choices swappable behind interfaces (see `multi-llm-router`
  and similar projects in this portfolio for the general pattern).
- Prefer configuration-driven pipelines (YAML/JSON in `configs/`) over hardcoded
  parameters so experiments are reproducible.
