---
name: hud
description: Surface OMG status on the Grok dashboard and, inside cmux, the workspace sidebar. Use when the user says /hud, statusline, or wants live mode visibility.
argument-hint: "[setup|status]"
---

# HUD

Grok does not have Claude Code's `statusLine`. OMG status lives in three places:

1. **Grok Agent Dashboard** — `/dashboard` (or `grok dashboard`). Lists live sessions; subagents appear under their parent.
2. **cmux sidebar** — when `CMUX_WORKSPACE_ID` is set, write status/progress onto the caller workspace.
3. **`.omg/state/`** — `omg.py state status` is the source of truth.

## Commands

| Argument | Action |
| --- | --- |
| _(none)_ / `status` | Print `omg.py state status` and current cmux sidebar state |
| `setup` | Wire cmux sidebar status for this workspace |

## Status

```bash
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" state status
```

Inside cmux:

```bash
cmux set-status omg "idle" --workspace "${CMUX_WORKSPACE_ID}" --color "#888888"
cmux sidebar-state --workspace "${CMUX_WORKSPACE_ID}" --json
```

When a mode is active, update the sidebar from the lead session:

```bash
cmux set-status omg "ralph" --workspace "${CMUX_WORKSPACE_ID}" --color "#ff9500"
cmux set-progress 0.4 --label "Ralph US-002" --workspace "${CMUX_WORKSPACE_ID}"
```

Do not install Node statusline wrappers, `~/.grok/hud/omc-hud.mjs`, or write `statusLine` into Claude `settings.json`.
