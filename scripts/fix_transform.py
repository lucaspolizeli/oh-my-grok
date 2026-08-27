#!/usr/bin/env python3
"""One-shot cleanup of OMC→OMG transform defects in markdown files."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".omg", "__pycache__", "node_modules"}
SKIP_FILES = {
    ROOT / "skills" / "team" / "SKILL.md",
    ROOT / "skills" / "cancel" / "SKILL.md",
    ROOT / "skills" / "omg-setup" / "SKILL.md",
    ROOT / "skills" / "hud" / "SKILL.md",
    ROOT / "skills" / "omg-doctor" / "SKILL.md",
    ROOT / "templates" / "AGENTS.md",
}

STATE_CMD = 'python3 "${GROK_PLUGIN_ROOT}/scripts/omg.py" state'


def transform(text: str) -> str:
    text = re.sub(r"the `/([^\"`\n]+?)\"\)", r"/oh-my-grok:\1", text)
    text = text.replace("`omg-state write` (", f"{STATE_CMD} write (")
    text = text.replace("`omg-state read` (", f"{STATE_CMD} read (")
    text = text.replace("`omg-state clear` (", f"{STATE_CMD} clear (")
    text = text.replace("`omg-state list`", f"{STATE_CMD} list")
    text = text.replace("`omg-state status`", f"{STATE_CMD} status")
    text = re.sub(r"(?<!omg )state_write", "omg state write", text)
    text = re.sub(r"(?<!omg )state_read", "omg state read", text)
    text = re.sub(r"(?<!omg )state_clear", "omg state clear", text)
    text = text.replace('Skill("compact")', "`/compact`")
    text = text.replace("Skill()", "`/oh-my-grok:<skill>`")
    text = text.replace("Skill(\"", "`/oh-my-grok:")
    text = text.replace("cancelomc", "cancelomg")
    text = text.replace("stopomc", "stopomg")
    text = text.replace(".omc/", ".omg/")
    text = text.replace(".omc\"", ".omg\"")
    text = text.replace("`$d/.omc`", "`$d/.omg`")
    text = text.replace("CLAUDE.md", "AGENTS.md")
    text = text.replace("AskUserQuestion", "ask_user_question")
    text = text.replace("oh-my-claudecode", "oh-my-grok")
    text = text.replace("CLAUDE_PLUGIN_ROOT", "GROK_PLUGIN_ROOT")
    text = text.replace("OMC_STATE_DIR", "OMG_STATE_DIR")
    text = text.replace("OMC_SESSION_ID", "OMG_SESSION_ID")
    text = text.replace("DISABLE_OMC", "DISABLE_OMG")
    text = text.replace("OMC_SKIP_HOOKS", "OMG_SKIP_HOOKS")
    text = text.replace("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "unused-grok-has-no-implicit-teams")
    text = text.replace('model="haiku"', 'model="grok-4.5"')
    text = text.replace('model="sonnet"', 'model="grok-4.6"')
    text = text.replace('model="opus"', 'model="grok-4.6"')
    text = text.replace("model=haiku", "model=grok-4.5")
    text = text.replace("model=sonnet", "model=grok-4.6")
    text = text.replace("model=opus", "model=grok-4.6")
    text = text.replace(" (Haiku)", " (grok-4.5)")
    text = text.replace(" (Sonnet)", " (grok-4.6)")
    text = text.replace(" (Opus)", " (grok-4.6)")
    text = text.replace("LOW tier (Haiku)", "grok-4.5")
    text = text.replace("MEDIUM tier (Sonnet)", "grok-4.6")
    text = text.replace("HIGH tier (Opus)", "grok-4.6")
    text = text.replace("architect-medium / Sonnet", "grok-4.6")
    text = text.replace("architect / Opus", "grok-4.6")
    text = text.replace("Claude Architect", "Architect agent")
    text = text.replace("Claude Critic", "Critic agent")
    text = text.replace("Claude agent", "Grok agent")
    text = text.replace("Claude teammate", "Grok teammate")
    text = text.replace("Claude Code", "Grok")
    text = text.replace("~/.claude/", "~/.grok/")
    text = text.replace("omc-teams", "omg-team")
    text = text.replace("omc doctor", "omg doctor")
    text = text.replace("omc ask", "omg ask")
    text = text.replace("omc update", "omg-setup")
    text = text.replace("omc setup", "omg-setup")
    text = text.replace("<!-- OMC:", "<!-- OMG:")
    text = text.replace("Grok /goal` docs: https://code.claude.com/docs/en/goal", "Grok `/goal` docs")
    text = text.replace("Anthropic Grok changelog: https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md", "xAI Grok Build changelog")
    return text


def main() -> None:
    changed = 0
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in {".md", ".json", ".jsonc", ".sh"}:
            continue
        if path.resolve() in SKIP_FILES:
            continue
        original = path.read_text(encoding="utf-8")
        updated = transform(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
            print(path.relative_to(ROOT))
    print(f"updated {changed} files")


if __name__ == "__main__":
    main()
