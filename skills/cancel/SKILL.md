---
name: cancel
aliases: [cancel-ralph, cancelomg]
description: Cancel any active OMG mode (autopilot, ralph, team, ultragoal, ralplan, execute). Use when the user says cancelomg, stopomg, or /cancel.
argument-hint: "[--force|--all]"
---

# Cancel

The standard way to finish or abort an OMG mode. The Stop hook keeps blocking with "The boulder never stops" until this skill clears state.

## Usage

```
/oh-my-grok:cancel
/oh-my-grok:cancel --force
```

Say `cancelomg` or `stopomg`.

## CLI

```bash
OMG="$GROK_PLUGIN_ROOT/scripts/omg.py"
python3 "$OMG" state list
python3 "$OMG" state status
python3 "$OMG" state read --mode team
python3 "$OMG" state clear --mode ralph
python3 "$OMG" team shutdown --team <slug>
```

`state clear` also writes a 30-second `cancel-signal` so the Stop hook lets the turn end. For autopilot pause-without-signal, use `state write --mode autopilot --active false` instead of `clear`.

## Steps

1. Parse `--force` / `--all`.
2. Run `state list` and `state status` for the current session (`GROK_SESSION_ID` / `OMG_SESSION_ID`).
3. Cancel in dependency order:
   1. **team** — `team shutdown --team <slug>` then `state clear --mode team`. If `linked_ralph`, also clear ralph.
   2. **autopilot** — `state write --mode autopilot --active false` (preserve resume data). Then clear linked ralph if present.
   3. **ralph** — if `linked_team`, cancel team first. Then `state clear --mode ralph`.
   4. **ultragoal** — `state clear --mode ultragoal`. Keep `.omg/ultragoal/` artifacts.
   5. **ralplan** — `state clear --mode ralplan`.
   6. **execute** / **deep-interview** / **skill-active** — `state clear --mode <name>`.
4. Always clear `skill-active` last so the Stop hook does not keep firing.
5. `--force` / `--all`: repeat for every session from `state list`, then delete leftover `.omg/state/*.json` except durable `.omg/ultragoal/` and `.omg/wiki/`.

## Team shutdown

If team is active:

1. Read `team_name` from `state read --mode team`.
2. `python3 "$OMG" team shutdown --team "$TEAM"`.
3. Best-effort: if `CMUX_WORKSPACE_ID` is set, do **not** close panes the user may still be reading; only stop the worker processes recorded in `.omg/state/team/<slug>/workers/*/status.json`.
4. Clear team state.

## Messages

| Mode | Success |
| --- | --- |
| Autopilot | Autopilot paused. Progress preserved for resume. |
| Ralph | Ralph cancelled. Persistent mode deactivated. |
| Team | Team cancelled. Workers shut down. |
| Ultragoal | Ultragoal guard released; durable plan/ledger preserved. |
| None | No active OMG modes detected. |

## Fallback when the CLI is missing

```bash
SESSION="${GROK_SESSION_ID:-default}"
ROOT="$(python3 - <<'PY'
from pathlib import Path
import os
print(os.environ.get("OMG_STATE_DIR") or "")
PY
)"
# If python is unavailable, walk up for .omg
d="$PWD"
while [ "$d" != "/" ] && [ ! -d "$d/.omg" ]; do d="$(dirname "$d")"; done
rm -f "$d/.omg/state/sessions/$SESSION/"*-state.json
```

Do not use this fallback for autopilot if you want resume data.
