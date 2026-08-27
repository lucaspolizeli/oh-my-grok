# oh-my-grok

Orquestração multiagente para [Grok Build](https://docs.x.ai), no mesmo espírito do [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) e das integrações [cmux OMC](https://cmux.com/pt-BR/docs/agent-integrations/oh-my-claudecode) / [Claude Code Teams](https://cmux.com/pt-BR/docs/agent-integrations/claude-code-teams).

O Grok é o orquestrador. Não é um worker CLI dentro do OMC.

## O que entra

- 19 agentes (`explore`, `planner`, `executor`, `verifier`, `code-reviewer`, …) invocáveis como `oh-my-grok:<nome>`
- Skills Tier-0: `/plan` → `/execute` → `/review` → `/verify`, mais `ralph`, `autopilot`, `team`, `deep-interview`
- Persistência via Stop hook (`The boulder never stops`)
- Estado em `.omg/` (não `.omc/`)
- `/team` visível no cmux: `cmux new-pane --focus false` no workspace chamador
- Setup que injeta um bloco `OMG:START/END` em `~/.grok/AGENTS.md` **sem apagar** regras existentes (cmux incluso)

## O que não é um fork do runtime Node do OMC

O OMC 5.0 é hooks + skills + agentes + um runtime Node grande (MCP `state_*`, HUD statusline, implicit teams do Claude). O Grok não tem `UserPromptSubmit` injetivo, nem implicit teams, nem `statusLine` do Claude. Este plugin reimplementa a **superfície de produto** nos primitivos do Grok: plugin, skills, `spawn_subagent`, Stop hook, CLI Python, panes cmux.

| OMC 5.0 | oh-my-grok |
| --- | --- |
| `Task(subagent_type="oh-my-claudecode:executor")` | `spawn_subagent(subagent_type="oh-my-grok:executor")` |
| MCP `state_write` | `python3 scripts/omg.py state write` |
| `.omc/` | `.omg/` |
| `DISABLE_OMC` | `DISABLE_OMG` |
| haiku / sonnet / opus | `grok-4.5` / `grok-4.6` |
| implicit agent teams | subagents (depth 1) + panes cmux |
| Claude `statusLine` HUD | dashboard Grok + `cmux set-status` |
| `UserPromptSubmit` injeta skill | observe-only; o modelo invoca a skill (AGENTS.md) |

## Install

No diretório deste repo:

```bash
grok plugin marketplace add .
grok plugin install oh-my-grok --trust
grok plugin validate .
```

Depois, numa sessão Grok:

```
/oh-my-grok:omg-setup
```

Isso injeta o bloco OMG em `~/.grok/AGENTS.md` e cria `.omg/` no projeto. Reinicie a sessão (ou `r` na aba Plugins) para carregar os hooks.

Instalação local confiável (auto-trust):

```bash
mkdir -p ~/.grok/plugins
ln -s "$(pwd)" ~/.grok/plugins/oh-my-grok
```

## Uso

```
/oh-my-grok:plan "redesenhar o auth"
/oh-my-grok:execute
/oh-my-grok:review
/oh-my-grok:verify

/oh-my-grok:ralph "fechar todos os TypeScript errors"
/oh-my-grok:team 3:executor "corrigir os erros em src/"
/oh-my-grok:cancel
```

Palavras-chave (o hook só registra; você precisa invocar a skill): `ralph`, `autopilot`, `ralplan`, `deep interview`, `deslop`, `cancelomg`.

## /team no cmux

Dentro do cmux (`CMUX_WORKSPACE_ID` definido), workers visíveis sobem com:

```bash
python3 "$GROK_PLUGIN_ROOT/scripts/omg.py" team spawn \
  --team fix-ts-errors --worker worker-1 --provider grok
```

Isso cria um pane no workspace chamador (`--focus false`) e manda `grok --always-approve --prompt-file …`. Especialistas in-session continuam via `spawn_subagent` (depth 1).

## Estado

```bash
python3 scripts/omg.py state status
python3 scripts/omg.py state write --mode ralph --active true --phase execution
python3 scripts/omg.py state clear --mode ralph
python3 scripts/omg.py doctor
```

Kill switches: `DISABLE_OMG=1`, `OMG_SKIP_HOOKS=persistent-mode,keyword-detect`.

## Validação

```bash
python3 -m unittest tests/test_omg.py
grok plugin validate .
```

## Licença

MIT. Texto de agentes/skills adaptado do oh-my-claudecode (MIT, Yeachan Heo).
