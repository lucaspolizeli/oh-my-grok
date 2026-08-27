---
name: omg-setup
description: Install or refresh oh-my-grok. Injects the OMG block into ~/.grok/AGENTS.md without clobbering existing rules (including cmux). Use when the user says setup omg, install oh-my-grok, or runs /omg-setup.
argument-hint: "[--user|--project|--force|--help]"
---

# OMG Setup

When this skill is invoked, run the setup. Do not only restate these instructions.

## Flags

- `--help` — show usage and stop
- `--user` — configure `~/.grok/AGENTS.md` only
- `--project` — configure this repo's `AGENTS.md` + `.omg/` only
- `--force` — rewrite the OMG block even if already present
- no flags — user + project

## Help

```
/oh-my-grok:omg-setup
/oh-my-grok:omg-setup --user
/oh-my-grok:omg-setup --project
/oh-my-grok:omg-setup --force
```

## Run

```bash
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" setup
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" setup --user
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" setup --project
python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" doctor
```

The setup script:

1. Injects `<!-- OMG:START -->` … `<!-- OMG:END -->` into `~/.grok/AGENTS.md` and/or `./AGENTS.md`.
2. Replaces only the text between those markers. Everything else (cmux rules, user notes) stays.
3. Writes a backup `AGENTS.md.omg.bak` when it mutates a file.
4. Creates `.omg/{state,plans,research,logs,artifacts,handoffs,wiki}/`.
5. Appends `.omg/` to `.gitignore` if missing.
6. Writes `~/.config/oh-my-grok/config.jsonc` on first user setup.

Then confirm the plugin is installed and trusted:

```bash
grok plugin marketplace add "$(python3 -c 'import os; print(os.environ.get("GROK_PLUGIN_ROOT","."))')"
grok plugin install oh-my-grok --trust
grok plugin validate "${GROK_PLUGIN_ROOT:-.}"
```

If the marketplace is already this repo, skip add and just enable/trust.

## After setup

Tell the user:

- Restart the Grok session (or press `r` on the Plugins tab) so hooks load.
- Canonical flow: `/oh-my-grok:plan` → `/oh-my-grok:execute` → `/oh-my-grok:review` → `/oh-my-grok:verify`.
- Visible teams: `/oh-my-grok:team` inside cmux.
- Kill switches: `DISABLE_OMG=1`, `OMG_SKIP_HOOKS=persistent-mode`.
- Run `/oh-my-grok:omg-doctor` if something looks off.

Do not overwrite `~/.grok/AGENTS.md` wholesale. Do not remove existing cmux or user rules.
