# Issue AC Agent

> An autonomous GitHub Actions agent that reviews every new issue and drafts
> Acceptance Criteria for human approval.

## What it does

When an issue is **opened**, the workflow `.github/workflows/issue-ac-agent.yml`:

1. Reads the issue and grounds itself in the codebase (`CLAUDE.md`, `pipeline.py`, …).
2. Applies the `acceptance-criteria` methodology (vendored at
   `.claude/skills/acceptance-criteria/SKILL.md`).
3. Analyzes **bottlenecks, edge cases, criticality, open questions**.
4. Posts **one comment** with the analysis + an AC draft.
5. Tags the issue `needs-ac-review` (and `ac-bot-processed`).

A human then reviews the draft, edits it, moves the approved AC into the issue
body, and removes the `needs-ac-review` label.

## Human-in-the-loop

The agent never decides "done" on its own — it produces a **draft**:

| Label              | Meaning                                                        |
|--------------------|---------------------------------------------------------------|
| `needs-ac-review`  | AC draft posted, waiting for a human to approve/edit.         |
| `ac-bot-processed` | Idempotency guard — the agent will never comment twice.       |
| `needs-info`       | Issue too vague; the agent asked clarifying questions instead.|

## One-time setup

```bash
# Add your Anthropic key as a repo secret (required by the workflow):
gh secret set ANTHROPIC_API_KEY --body "sk-ant-..."
```

That's it — the workflow triggers automatically on the next opened issue.

## Manual run / backfill

For existing issues or re-runs:

```bash
gh workflow run issue-ac-agent.yml -f issue_number=12
```

(or via the **Actions → Issue AC Agent → Run workflow** button.)

> Re-running on an already-processed issue is a no-op: the `ac-bot-processed`
> label makes the agent stop before commenting. Remove that label first to force
> a fresh pass.

## Guardrails baked in

- **Idempotency** — `ac-bot-processed` prevents duplicate comments.
- **Loop prevention** — issues opened by bots are skipped at the job level.
- **No fabrication** — underspecified issues get clarifying questions, not invented AC.
- **Least privilege** — the agent may only read the repo and use a small set of
  `gh issue` commands; it cannot push code or open PRs.
- **Pinned model + turn cap** — `claude-sonnet-4-6`, `--max-turns 20`,
  15-minute job timeout.
- **Reproducible skill** — the methodology is vendored into the repo, so CI does
  not depend on a plugin marketplace being reachable.

## Tuning

- **Reduce noise / opt-in mode:** if drafting on *every* issue is too much, change
  the trigger to fire only when a human applies a label:
  ```yaml
  on:
    issues:
      types: [labeled]
  ```
  and add a job guard `if: github.event.label.name == 'ready-for-ac'`.
- **Different model:** edit `--model` in the workflow.
- **Update the skill:** re-sync `.claude/skills/acceptance-criteria/SKILL.md` from
  the `ymazhar/claude-knowledge-skills` marketplace when it changes.