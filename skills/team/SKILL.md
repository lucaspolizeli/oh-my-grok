---
name: team
description: N coordinated workers on a shared task list. Uses in-session spawn_subagent plus visible cmux panes (or headless grok -p). Use when the user says /team or wants parallel agents.
argument-hint: "[N:agent-type] [ralph] <task description>"
---

# Team

Coordinate N workers on one task. Grok has no implicit agent-teams API and no `TeamCreate`/`TeamDelete`. This skill is the OMG team runtime.

## Usage

```
/oh-my-grok:team N:agent-type "task description"
/oh-my-grok:team "task description"
/oh-my-grok:team ralph "task description"
```

- **N** — worker count (1-8 default auto-size; hard cap 20)
- **agent-type** — overrides the `team-exec` worker (`executor`, `debugger`, `designer`, `grok`, `codex`, `cursor`)
- **ralph** — wrap the pipeline in Ralph persistence

## Two worker surfaces

| Surface | When | How |
| --- | --- | --- |
| In-session subagent | Default for specialist agents (`explore`, `planner`, `executor`, `verifier`, …) | `spawn_subagent(subagent_type="oh-my-grok:<name>", background=true)`. Depth is 1: workers must not spawn children. |
| Visible CLI pane | User asked for visible workers, or provider is `grok`/`codex`/`cursor` and `CMUX_WORKSPACE_ID` is set | `python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" team spawn --team <slug> --worker worker-N --provider grok` which runs `cmux new-pane --focus false` in the **caller** workspace |

Inside cmux, never gate `/team` on `tmux -V`. Stay in `CMUX_WORKSPACE_ID`. Pass `--focus false`. Do not call `focus-pane` / `select-workspace`.

If cmux is absent, `omg.py team spawn` falls back to headless `grok -p --always-approve --prompt-file …`.

## Pipeline

`team-plan → team-prd → team-exec → team-verify → team-fix (bounded loop)`

| Stage | Required agents | Optional |
| --- | --- | --- |
| team-plan | `explore` (grok-4.5), `planner` (grok-4.6) | `analyst`, `architect` |
| team-prd | `analyst` | `critic` |
| team-exec | `executor` | `debugger`, `designer`, `writer`, `test-engineer` |
| team-verify | `verifier` | `security-reviewer`, `code-reviewer` |
| team-fix | `executor` | `debugger` |

The user's `N:agent-type` only overrides `team-exec`. Other stages pick specialists.

Stop the verify/fix loop when verification passes, or after `max_fix_loops` (default 3) with evidence of failure.

## State

```bash
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" state write --mode team --active true --phase team-plan --json '{"team_name":"fix-ts-errors","agent_count":3}'
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" state read --mode team
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" state write --mode team --phase team-exec
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" state clear --mode team
```

Handoffs go to `.omg/handoffs/<stage>.md` (10-20 lines: Decided / Rejected / Risks / Files / Remaining). The lead reads the previous handoff before spawning the next stage.

## Workflow

1. Parse N, agent-type, task, ralph flag. Slug the team name (`fix-ts-errors`).
2. If `state read --mode team` is already `active=true` and non-terminal, resume that stage instead of spawning duplicates.
3. `team-plan`: spawn explore + planner. Write the task graph. Pre-assign owners with `todo_write`.
4. `team-prd` only if acceptance criteria are missing.
5. `team-exec`: spawn all workers in parallel.
   - Specialists: `spawn_subagent` with the worker preamble below.
   - Visible grok/codex/cursor: write `.omg/state/team/<slug>/workers/<name>/prompt.md` then `omg.py team spawn`.
6. Monitor via `todo_write` and `omg.py team status --team <slug>`. Reassign stuck `in_progress` work after ~10 minutes.
7. `team-verify` then `team-fix` as needed.
8. Shutdown: `omg.py team shutdown --team <slug>`, then `state clear --mode team`. If ralph is linked, clear ralph too only after team shutdown.

## Worker preamble

Include this in every worker prompt:

```
You are a TEAM WORKER in OMG team "{team_name}". Your name is "{worker_name}".
You report to the team lead. You are not the leader.

1. CLAIM the first pending todo assigned to you. Mark it in_progress.
2. WORK directly. Do NOT spawn subagents. Do NOT run /team, /ralph, /autopilot.
3. COMPLETE the todo when done, with evidence (commands run, files changed).
4. If blocked, leave the todo in_progress and report the blocker.
5. ALWAYS use absolute file paths.
```

For cmux CLI workers, also tell them to write a short summary to their `output.md`.

## Isolation

Independent file-scoped subtasks can use `spawn_subagent(..., isolation="worktree")`. Visible CLI workers share the caller workspace unless you create a git worktree first and pass `--cwd` to `omg.py team spawn`.

## Team + Ralph

When invoked as `/team ralph`:

1. Write ralph state `active=true` with `linked_team=true`.
2. Run the team pipeline inside each ralph iteration.
3. On verify pass, run `code-reviewer` before `/oh-my-grok:cancel`.
4. `/oh-my-grok:cancel` shuts the team down first, then clears ralph.

## Cancel

`/oh-my-grok:cancel` is the only clean exit. It runs `omg.py team shutdown` then `state clear --mode team`.
