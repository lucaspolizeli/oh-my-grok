---
name: omg-doctor
description: Diagnose and fix oh-my-grok installation issues. Use when setup looks broken, hooks are silent, or /team cannot spawn panes.
---

# Doctor

Run the runtime doctor, then interpret the JSON.

```bash
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" doctor
grok plugin validate "${GROK_PLUGIN_ROOT:-.}"
grok plugin list --json
```

## Extra checks

1. **Kill switches** — `echo "DISABLE_OMG=$DISABLE_OMG OMG_SKIP_HOOKS=$OMG_SKIP_HOOKS"`
2. **AGENTS.md markers** — `grep -n "OMG:START\\|OMG:VERSION" "${GROK_HOME:-$HOME/.grok}/AGENTS.md" ./AGENTS.md`
3. **Session state** — `python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" state resolve` and `state status`
4. **cmux** — if the user expected visible `/team` panes: `printf '%s\n' "$CMUX_WORKSPACE_ID" "$CMUX_SURFACE_ID"; cmux identify --json`
5. **Plugin trust** — hooks stay inert until the plugin is trusted. Reinstall with `grok plugin install oh-my-grok --trust` or place it under `~/.grok/plugins/`.

## Report

```
## OMG Doctor Report
### Summary
HEALTHY | ISSUES FOUND
### Checks
| Check | Status | Details |
```

## Auto-fix (ask first)

- Missing AGENTS.md block → `/oh-my-grok:omg-setup`
- Untrusted plugin → `grok plugin install <path> --trust`
- Stale cancel loop → `python3 …/omg.py state clear --mode <mode>` then `/oh-my-grok:cancel --force`
- DISABLE_OMG set → tell the user to unset it; do not silently override
