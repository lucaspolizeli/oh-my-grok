---
description: ""
---

# OMG external-context

This compatibility command keeps `/oh-my-grok:external-context` available without loading the full `external-context` skill description in every Grok session.

## Dispatch

1. Read the full bundled skill instructions from the active OMG plugin/install: `skills/external-context/SKILL.md`.
2. Follow that SKILL.md exactly, treating the user's arguments as:

```text
$ARGUMENTS
```

If the file is not directly readable from the current working directory, locate it under the active `GROK_PLUGIN_ROOT`/`OMC_PLUGIN_ROOT`, package root, or installed OMG plugin directory, then continue.
