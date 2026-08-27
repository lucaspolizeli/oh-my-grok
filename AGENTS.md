# oh-my-grok (repo)

This repository **is** the Grok plugin. Runtime lives in `scripts/omg.py`. Product surface lives in `agents/`, `skills/`, `commands/`, `hooks/`.

- State dir is `.omg/`, never `.omc/`.
- Setup must preserve anything outside `<!-- OMG:START -->` / `<!-- OMG:END -->` in `~/.grok/AGENTS.md`.
- Team workers: `spawn_subagent` (depth 1) plus `cmux new-pane --focus false` in the caller workspace. Do not gate on `tmux -V` inside cmux.
- Models: `grok-4.5` (fast) and `grok-4.6` (standard/high). Do not mention haiku/sonnet/opus as runnable model ids.
- Kill switches: `DISABLE_OMG`, `OMG_SKIP_HOOKS`.
- Validate with `python3 -m unittest tests/test_omg.py` and `grok plugin validate .`.
