# Contributing Guidelines

Welcome to the team! Since we are 4 members working fast for the Trueforge Hackathon, here is how we can collaborate efficiently.

## Branching Strategy
- Main branch: `main`; it is the stable integration branch.
- Start every task from the latest `origin/main`.
- Keep backend work in one of the two system tracks:
  - `feature/system-1-<topic>` for the virtual hardware sandbox.
  - `feature/system-2-<topic>` for the agent harness and autonomous investigator.
- Use an additional `feature/integration-<topic>` branch when a change crosses
  both systems.
- Use a separate git worktree when two tracks are active at the same time. Do
  not switch branches in a worktree that contains uncommitted work.

## Commit Messages
Write clear, concise commit messages. 

## Pull Requests
1. Every non-trivial branch must have a PR against `main`; do not merge work
   directly into `main`.
2. Open the PR as soon as the branch has a reviewable vertical slice. Small PRs
   are preferred over holding unrelated work for a large batch.
3. Use the PR template to identify the backend track, tests, contracts, and
   determinism impact.
4. Tag at least one other team member for review before merging.
5. Keep each PR focused on one backend outcome. Follow-up PRs are expected when
   the investigation loop exposes new work.

### Parallel worktree layout

The recommended local layout is:

```text
Harness-Agent/                         # main checkout
Harness-Agent-worktrees/
  system-1-sandbox/                    # feature/system-1-<topic>
  system-2-agent-harness/              # feature/system-2-<topic>
```

Both worktrees must be based on the same fetched `origin/main` commit before
work begins. Each worktree gets its own commits and PR; integration changes
must explicitly describe the System 1/System 2 contract they connect.

## Working with AI Agents
- Use the `.cursorrules` to keep the AI aligned with our architecture.
- Store useful prompts or agent contexts in the `.ai/` directory so others can reuse them.
