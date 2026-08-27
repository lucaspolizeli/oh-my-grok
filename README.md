# oh-my-grok

Multi-agent orchestration for [Grok Build](https://docs.x.ai). Same product surface as [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) and the [cmux OMC](https://cmux.com/docs/agent-integrations/oh-my-claudecode) / [Claude Code Teams](https://cmux.com/docs/agent-integrations/claude-code-teams) integrations, reimplemented on Grok plugins, skills, subagents, Stop hooks, and cmux panes.

Grok is the orchestrator. This is not a CLI worker inside OMC.

**You talk to it with slash commands in a Grok session.** After install + setup, the everyday loop is:

```text
/oh-my-grok:plan "redesign auth"
/oh-my-grok:execute
/oh-my-grok:review
/oh-my-grok:verify
```

---

## Requirements

- [Grok CLI](https://docs.x.ai) (`grok`) authenticated
- Python 3
- Optional: [cmux](https://cmux.com) if you want `/team` workers as visible panes (sidebar + Feed)

---

## Install

From GitHub (what you want if you are a user, not a contributor):

```bash
grok plugin marketplace add lucaspolizeli/oh-my-grok
grok plugin install oh-my-grok --trust
```

Or install the repo directly:

```bash
grok plugin install lucaspolizeli/oh-my-grok --trust
```

Confirm it is listed and trusted:

```bash
grok plugin list
grok plugin details oh-my-grok
```

Then **restart the Grok session** (or press `r` on the Plugins tab). Hooks stay inert until the plugin is trusted and the session is reloaded.

### Live local checkout (contributors)

`grok plugin install` copies files. Edits in a git checkout do not reach hooks until you reinstall, unless you symlink:

```bash
git clone https://github.com/lucaspolizeli/oh-my-grok.git
cd oh-my-grok
mkdir -p ~/.grok/plugins
ln -sfn "$(pwd)" ~/.grok/plugins/oh-my-grok
grok plugin marketplace add .
grok plugin install oh-my-grok --trust
grok plugin validate .
```

---

## First-run setup

In a Grok session, in the project you want to use:

```text
/oh-my-grok:omg-setup
```

That does three things:

1. Injects an `<!-- OMG:START -->` … `<!-- OMG:END -->` block into `~/.grok/AGENTS.md` (user) and `./AGENTS.md` (project). **It only rewrites between those markers.** Existing cmux rules and your notes stay.
2. Creates `.omg/` in the project (`state`, `plans`, `research`, `logs`, `artifacts`, `handoffs`, `wiki`) and gitignores it.
3. Writes `~/.config/oh-my-grok/config.jsonc` on first user setup.

Flags:

| Command | Effect |
| --- | --- |
| `/oh-my-grok:omg-setup` | user + project |
| `/oh-my-grok:omg-setup --user` | `~/.grok/AGENTS.md` only |
| `/oh-my-grok:omg-setup --project` | this repo only |
| `/oh-my-grok:omg-setup --force` | rewrite the OMG block even if present |

Restart the session after setup. Then sanity-check:

```text
/oh-my-grok:omg-doctor
```

---

## How to invoke things

| You type | What happens |
| --- | --- |
| `/oh-my-grok:plan …` | Runs the **skill** (canonical). Short form `/plan` works when unambiguous. |
| Saying `ralph` / `autopilot` / `cancelomg` in prose | Grok **only logs** the keyword. You still have to invoke the skill. UserPromptSubmit cannot inject extra context. |
| `spawn_subagent(subagent_type="oh-my-grok:executor")` | Runs a **specialist agent**. Depth is 1: workers must not spawn children. |

Skills and agents are different. `/oh-my-grok:ai-slop-cleaner` is a skill. `oh-my-grok:executor` is an agent. Calling a skill as an agent is denied.

---

## Which command should I run?

| I want… | Run |
| --- | --- |
| Plan before coding (vague idea, interview if needed) | `/oh-my-grok:plan "…"` |
| Plan with Planner / Architect / Critic consensus | `/oh-my-grok:plan --consensus "…"` |
| Build an approved task | `/oh-my-grok:execute` |
| Review finished work (does not author the change) | `/oh-my-grok:review` |
| Prove it actually works | `/oh-my-grok:verify` |
| Keep looping until the PRD stories pass | `/oh-my-grok:ralph "…"` |
| Idea → spec → plan → code → QA, hands-off | `/oh-my-grok:autopilot "…"` |
| Several visible workers on one task (best inside cmux) | `/oh-my-grok:team 3:executor "…"` |
| Socratic interview before any plan | `/oh-my-grok:deep-interview "…"` |
| Stop the persistence loop / shut workers down | `/oh-my-grok:cancel` |
| Diagnose install, hooks, trust, cmux | `/oh-my-grok:omg-doctor` |

**Default for a real feature:** plan → execute → review → verify.

**Default for "don't stop until it's done":** ralph (known task) or autopilot (from an idea).

**Default for parallel workers you can watch:** `/team` inside cmux.

Do not start ralph/autopilot/team for a one-line fix. Just say what to change.

---

## Everyday flow

```text
/oh-my-grok:plan "add invite-only signup"
```

Plan writes to `.omg/plans/` and stays `pending approval` unless you explicitly opt into execution.

```text
/oh-my-grok:execute
/oh-my-grok:review
/oh-my-grok:verify
```

Review never authors the change it judges. Verify reports commands run and what passed, not "should work".

---

## Persistence ("the boulder")

Ralph, autopilot, and team stay alive through the **Stop** hook. When you see:

```text
The boulder never stops
```

the active mode is not done. Grok continues until the completion criteria are met, then it must run `/oh-my-grok:cancel`.

To abort:

```text
/oh-my-grok:cancel
/oh-my-grok:cancel --force
```

You can also say `cancelomg` or `stopomg` (still invoke the skill). Cancel shuts team workers first, then clears mode state.

Kill switches (environment):

| Variable | Effect |
| --- | --- |
| `DISABLE_OMG=1` | Turn the whole plugin runtime off |
| `OMG_SKIP_HOOKS=persistent-mode,keyword-detect` | Skip named hooks |

---

## Team (visible workers)

```text
/oh-my-grok:team 3:executor "fix the TypeScript errors in src/"
/oh-my-grok:team ralph "close the open QA list"
```

- **N** — worker count (1-8 typical; hard cap 20)
- **agent-type** — who does `team-exec` (`executor`, `debugger`, `designer`, `grok`, `codex`, `cursor`)
- **ralph** — wrap the pipeline in the persistence loop

Pipeline: `team-plan → team-prd → team-exec → team-verify → team-fix` (bounded).

Two worker surfaces:

| Surface | When | How |
| --- | --- | --- |
| In-session subagent | Specialists (`explore`, `planner`, `executor`, …) | `spawn_subagent` (depth 1) |
| Visible CLI pane | You asked for visible workers, or provider is `grok`/`codex`/`cursor` **and** `CMUX_WORKSPACE_ID` is set | `cmux new-pane --focus false` in the **caller** workspace |

Inside cmux, `/team` is native. It does not need `tmux`. If cmux is absent, workers fall back to headless `grok -p`.

Handoffs live in `.omg/handoffs/`. Stop with `/oh-my-grok:cancel`.

---

## Agents

Invoke as `oh-my-grok:<name>` via `spawn_subagent`. Fast lookups use `grok-4.5`; implementation, architecture, and review use `grok-4.6`.

| Agent | Job |
| --- | --- |
| `explore` | Read-only codebase search |
| `planner` | Plans and specs |
| `analyst` | Requirements and hidden constraints |
| `architect` | Architecture review |
| `executor` | Implementation |
| `debugger` | Root-cause isolation |
| `test-engineer` | Test strategy and coverage |
| `qa-tester` | Interactive CLI testing |
| `code-reviewer` | Defects, risk, simplification |
| `security-reviewer` | Security pass |
| `verifier` | Evidence that it works |
| `critic` | Plan / design critique |
| `designer` | UI |
| `writer` | Docs |
| `document-specialist` | External docs / SDK lookup |
| `git-master` | Commits, rebase, history |
| `code-simplifier` | Clarity pass on recent diffs |
| `tracer` | Causal tracing |
| `scientist` | Data / research execution |

---

## State

Runtime state is `.omg/` (not `.omc/`). Override with `OMG_STATE_DIR`, or drop a `.omg-workspace` marker in a parent folder to share one `.omg/` across sibling repos.

```bash
python3 scripts/omg.py state status
python3 scripts/omg.py state read --mode ralph
python3 scripts/omg.py state write --mode ralph --active true --phase execution
python3 scripts/omg.py state clear --mode ralph
python3 scripts/omg.py doctor
```

Inside a Grok session, prefer `"${GROK_PLUGIN_ROOT}/scripts/omg.py"`.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Slash commands missing | Plugin not installed/enabled. `grok plugin list`, then restart. |
| Hooks never fire | Plugin not trusted, or session not reloaded. `grok plugin install oh-my-grok --trust`, press `r` on Plugins. |
| "I said ralph but nothing persisted" | Keywords are observe-only. Invoke `/oh-my-grok:ralph "…"`. |
| Stop hook keeps blocking after you are done | `/oh-my-grok:cancel`. If stuck: `python3 …/omg.py state clear --mode <mode>` then `/oh-my-grok:cancel --force`. |
| `/team` is invisible | You are not in cmux (`CMUX_WORKSPACE_ID` unset). Open the project in cmux, or accept headless `grok -p`. |
| `/team` spawned in the wrong workspace | Stay in the caller workspace. Workers use `--focus false` and must not `select-workspace`. |
| AGENTS.md lost cmux rules | Should not happen. Setup only rewrites between `OMG:START/END`. Restore from `AGENTS.md.omg.bak`. |
| Doctor reports ISSUES | `/oh-my-grok:omg-doctor` and follow the table. Do not unset `DISABLE_OMG` silently if you set it. |
| Local edits to skills/hooks ignored | Install copies the plugin. Reinstall, or symlink `~/.grok/plugins/oh-my-grok` to the checkout. |

```bash
python3 scripts/omg.py doctor
grok plugin validate .
echo "DISABLE_OMG=$DISABLE_OMG OMG_SKIP_HOOKS=$OMG_SKIP_HOOKS"
```

---

## Mapping from oh-my-claudecode

This is **not** a fork of the OMC Node runtime. OMC is hooks + skills + agents + a large Node runtime (MCP `state_*`, Claude statusline HUD, implicit teams). Grok has no injective `UserPromptSubmit`, no implicit teams, and no Claude `statusLine`. oh-my-grok reimplements the product surface on Grok primitives.

| OMC 5.0 | oh-my-grok |
| --- | --- |
| `Task(subagent_type="oh-my-claudecode:executor")` | `spawn_subagent(subagent_type="oh-my-grok:executor")` |
| MCP `state_write` | `python3 scripts/omg.py state write` |
| `.omc/` | `.omg/` |
| `DISABLE_OMC` | `DISABLE_OMG` |
| haiku / sonnet / opus | `grok-4.5` / `grok-4.6` |
| implicit agent teams | subagents (depth 1) + cmux panes |
| Claude `statusLine` HUD | Grok dashboard + `cmux set-status` |
| `UserPromptSubmit` injects skill | observe-only; the model invokes the skill (AGENTS.md) |

---

## Tests

```bash
python3 -m unittest tests/test_omg.py
grok plugin validate .
```

---

## License

MIT. Agent and skill text adapted from oh-my-claudecode (MIT, Yeachan Heo).
