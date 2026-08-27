---
name: ask
description: Process-first advisor routing for Claude, Codex, Gemini, Antigravity, Grok, or Cursor via `omg ask`, with artifact capture and no raw CLI assembly
---

# Ask

Use OMG's canonical advisor skill to route a prompt through the local Claude, Codex, Gemini, Antigravity, Grok, or Cursor CLI and persist the result as an ask artifact.

## Usage

```bash
/oh-my-grok:ask <claude|codex|gemini|antigravity|grok|cursor> <question or task>
```

Examples:

```bash
/oh-my-grok:ask codex "review this patch from a security perspective"
/oh-my-grok:ask gemini "suggest UX improvements for this flow"
/oh-my-grok:ask antigravity "suggest UX improvements for this flow"
/oh-my-grok:ask claude "draft an implementation plan for issue #123"
/oh-my-grok:ask cursor "apply this implementation plan"
```

## Routing

**Required execution path — always use this command:**

```bash
omg ask {{ARGUMENTS}}
```

**Do NOT manually construct raw provider CLI commands.** Never run `codex`, `claude`, `gemini`, `agy`, `grok`, or `cursor-agent` directly to fulfill this skill. The `omg ask` wrapper handles correct flag selection, artifact persistence, and provider-version compatibility automatically. Manually assembling provider CLI flags will produce incorrect or outdated invocations.

## Requirements

- The selected local CLI must be installed and authenticated.
- Verify availability with the matching command:

```bash
claude --version
codex --version
gemini --version
agy --version
grok --version
cursor-agent --version
```

- **Antigravity CLI install** (Google's successor to the Gemini CLI): install the `agy`
  binary per the [official Antigravity instructions](https://antigravity.google) (inspect
  any installer before running it). Verify: `agy --version`
  > **Platform note:** `omg ask antigravity` is supported on macOS/Linux. On Windows it is guarded with a clear error, because `agy --print` takes the prompt as an argv value (it cannot read stdin) and has known upstream Windows `-p` limitations; use `omg ask gemini` on Windows.
- **Gemini CLI** remains supported for enterprise/API-key use cases.

## Artifacts

`omg ask` writes artifacts to:

```text
.omg/artifacts/ask/<provider>-<slug>-<timestamp>.md
```

Task: {{ARGUMENTS}}
