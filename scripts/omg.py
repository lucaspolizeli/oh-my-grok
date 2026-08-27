#!/usr/bin/env python3
"""oh-my-grok runtime CLI.

Stdlib-only helper used by plugin hooks and skills.

  omg.py state resolve|read|write|clear|list|status
  omg.py hook persistent-mode|session-start|keyword-detect|pre-tool
  omg.py team spawn|status|shutdown
  omg.py setup [--user|--project|--force]
  omg.py doctor
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
START_MARKER = "<!-- OMG:START -->"
END_MARKER = "<!-- OMG:END -->"
VERSION_MARKER = "<!-- OMG:VERSION:0.1.0 -->"

PERSISTENT_MODES = (
    "ralph",
    "autopilot",
    "team",
    "ultragoal",
    "ralplan",
    "execute",
    "deep-interview",
    "skill-active",
)

SKILL_NAMES = {
    "ai-slop-cleaner",
    "ask",
    "autopilot",
    "autoresearch",
    "cancel",
    "configure-notifications",
    "debug",
    "deep-interview",
    "deepinit",
    "execute",
    "external-context",
    "hud",
    "omg-doctor",
    "omg-setup",
    "plan",
    "project-session-manager",
    "ralph",
    "ralplan",
    "release",
    "remember",
    "research",
    "review",
    "self-improve",
    "skill",
    "skillify",
    "team",
    "trace",
    "ultragoal",
    "verify",
    "visual-verdict",
    "wiki",
}

KEYWORD_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    ("cancel", "cancel", re.compile(r"\b(cancelomg|stopomg|cancelomc|stopomc)\b", re.I)),
    ("ralph", "ralph", re.compile(r"\bralph\b", re.I)),
    ("autopilot", "autopilot", re.compile(r"\bautopilot\b", re.I)),
    ("ralplan", "plan", re.compile(r"\bralplan\b", re.I)),
    ("deep-interview", "deep-interview", re.compile(r"\bdeep[-\s]interview\b", re.I)),
    ("ai-slop-cleaner", "ai-slop-cleaner", re.compile(r"\b(deslop|anti-slop|slop[- ]clean)\b", re.I)),
    ("tdd", "execute", re.compile(r"\btdd\b", re.I)),
    ("deepsearch", "research", re.compile(r"\bdeepsearch\b", re.I)),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def plugin_root() -> Path:
    env = os.environ.get("GROK_PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def grok_home() -> Path:
    return Path(os.environ.get("GROK_HOME", Path.home() / ".grok")).expanduser()


def skip_hooks(*names: str) -> bool:
    if os.environ.get("DISABLE_OMG") in {"1", "true", "yes"}:
        return True
    skipped = {part.strip() for part in os.environ.get("OMG_SKIP_HOOKS", "").split(",") if part.strip()}
    return any(name in skipped for name in names)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def read_json(path: Path) -> Any | None:
    try:
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_json(path: Path, data: Any) -> None:
    atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def emit(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")


def project_id(cwd: Path) -> str:
    source = cwd.resolve().as_posix()
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            source = result.stdout.strip()
    except OSError:
        pass
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", cwd.name) or "project"
    return f"{slug}-{digest}"


def git_toplevel(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    path = result.stdout.strip()
    return Path(path) if path else None


def find_workspace_marker(cwd: Path) -> Path | None:
    current = cwd.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".omg-workspace").exists():
            return candidate
    return None


def effective_cwd(args: argparse.Namespace | None = None) -> Path:
    if args is not None and getattr(args, "cwd", None):
        return Path(args.cwd).expanduser().resolve()
    return Path.cwd().resolve()


def resolve_omg_root(cwd: Path | None = None) -> Path:
    here = (cwd or Path.cwd()).resolve()
    env_dir = os.environ.get("OMG_STATE_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve() / project_id(here)
    marker = find_workspace_marker(here)
    if marker:
        return marker / ".omg"
    git_root = git_toplevel(here)
    if git_root:
        return git_root / ".omg"
    return here / ".omg"


def session_id_from(event: dict[str, Any] | None = None) -> str:
    event = event or {}
    for key in ("OMG_SESSION_ID", "GROK_SESSION_ID"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    for key in ("sessionId", "session_id"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "default"


def state_dir(root: Path) -> Path:
    return root / "state"


def session_dir(root: Path, session: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", session)[:180] or "default"
    return state_dir(root) / "sessions" / safe


def mode_path(root: Path, session: str, mode: str) -> Path:
    return session_dir(root, session) / f"{mode}-state.json"


def load_mode(root: Path, session: str, mode: str) -> dict[str, Any] | None:
    data = read_json(mode_path(root, session, mode))
    return data if isinstance(data, dict) else None


def is_active(data: dict[str, Any] | None) -> bool:
    if not data:
        return False
    return data.get("active") is True


def list_sessions(root: Path) -> list[str]:
    base = state_dir(root) / "sessions"
    if not base.is_dir():
        return []
    return sorted(path.name for path in base.iterdir() if path.is_dir())


def active_modes_for(root: Path, session: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for mode in PERSISTENT_MODES:
        data = load_mode(root, session, mode)
        if is_active(data) and data is not None:
            found.append({"mode": mode, **data})
    return found


def cancel_active(root: Path, session: str) -> bool:
    data = load_mode(root, session, "cancel-signal")
    if not is_active(data) or data is None:
        return False
    expires = data.get("expires_at")
    if not isinstance(expires, str):
        return True
    try:
        parsed = datetime.fromisoformat(expires.replace("Z", "+00:00"))
    except ValueError:
        return True
    return datetime.now(timezone.utc) < parsed


def cmd_state_resolve(args: argparse.Namespace) -> int:
    cwd = effective_cwd(args)
    root = resolve_omg_root(cwd)
    session = args.session or session_id_from()
    emit(
        {
            "omg_root": str(root),
            "state_dir": str(state_dir(root)),
            "session_id": session,
            "session_dir": str(session_dir(root, session)),
        }
    )
    return 0


def cmd_state_read(args: argparse.Namespace) -> int:
    root = resolve_omg_root(effective_cwd(args))
    session = args.session or session_id_from()
    data = load_mode(root, session, args.mode)
    emit(data or {"mode": args.mode, "active": False, "exists": False})
    return 0


def cmd_state_write(args: argparse.Namespace) -> int:
    root = resolve_omg_root(effective_cwd(args))
    session = args.session or session_id_from()
    path = mode_path(root, session, args.mode)
    current = load_mode(root, session, args.mode) or {}
    patch: dict[str, Any] = {}
    if args.json:
        parsed = json.loads(args.json)
        if not isinstance(parsed, dict):
            raise SystemExit("state write --json must be an object")
        patch.update(parsed)
    if args.active is not None:
        patch["active"] = args.active.lower() in {"1", "true", "yes", "on"}
    if args.phase:
        patch["current_phase"] = args.phase
    if args.set:
        for item in args.set:
            if "=" not in item:
                raise SystemExit(f"invalid --set {item!r}; expected key=value")
            key, value = item.split("=", 1)
            patch[key] = value
    current.update(patch)
    current["mode"] = args.mode
    current["session_id"] = session
    current["updated_at"] = now_iso()
    if "created_at" not in current:
        current["created_at"] = current["updated_at"]
    if "active" not in current:
        current["active"] = True
    write_json(path, current)
    emit(current)
    return 0


def cmd_state_clear(args: argparse.Namespace) -> int:
    root = resolve_omg_root(effective_cwd(args))
    session = args.session or session_id_from()
    path = mode_path(root, session, args.mode)
    existed = path.is_file()
    if existed:
        path.unlink()
    if args.mode != "cancel-signal" and not args.no_signal:
        expires = datetime.now(timezone.utc) + timedelta(seconds=30)
        write_json(
            mode_path(root, session, "cancel-signal"),
            {
                "active": True,
                "mode": args.mode,
                "requested_at": now_iso(),
                "expires_at": expires.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "source": "omg.py state clear",
            },
        )
    emit({"cleared": existed, "mode": args.mode, "session_id": session})
    return 0


def cmd_state_list(args: argparse.Namespace) -> int:
    root = resolve_omg_root(effective_cwd(args))
    sessions = list_sessions(root)
    payload = []
    for session in sessions:
        payload.append(
            {
                "session_id": session,
                "active": [item["mode"] for item in active_modes_for(root, session)],
            }
        )
    emit({"omg_root": str(root), "sessions": payload})
    return 0


def cmd_state_status(args: argparse.Namespace) -> int:
    root = resolve_omg_root(effective_cwd(args))
    session = args.session or session_id_from()
    emit(
        {
            "session_id": session,
            "active": active_modes_for(root, session),
            "cancel_signal": cancel_active(root, session),
            "omg_root": str(root),
        }
    )
    return 0


def hook_persistent_mode() -> int:
    if skip_hooks("persistent-mode", "stop-continuation"):
        return 0
    event = read_stdin_json()
    if event.get("reason") not in {None, "", "end_turn"}:
        return 0
    if event.get("subagentType") or event.get("subagent_type"):
        return 0
    cwd = Path(event.get("workspaceRoot") or event.get("cwd") or os.getcwd())
    root = resolve_omg_root(cwd)
    session = session_id_from(event)
    if cancel_active(root, session):
        return 0
    active = active_modes_for(root, session)
    if not active:
        return 0
    lead = active[0]
    mode = lead.get("mode", "unknown")
    phase = lead.get("current_phase") or lead.get("phase") or "running"
    iteration = lead.get("iteration")
    extra = f" iteration={iteration}" if iteration is not None else ""
    reason = (
        "The boulder never stops. "
        f"Active OMG mode: {mode} (phase={phase}{extra}). "
        "Continue the work. Do not stop until the mode completion criteria are met, "
        "then run /oh-my-grok:cancel."
    )
    emit({"decision": "block", "reason": reason})
    return 0


def hook_session_start() -> int:
    if skip_hooks("session-start"):
        return 0
    event = read_stdin_json()
    cwd = Path(event.get("workspaceRoot") or event.get("cwd") or os.getcwd())
    root = resolve_omg_root(cwd)
    session = session_id_from(event)
    path = session_dir(root, session) / "session.json"
    existing = read_json(path) if path.is_file() else None
    payload = {
        "session_id": session,
        "cwd": str(cwd),
        "started_at": now_iso() if not isinstance(existing, dict) else existing.get("started_at", now_iso()),
        "updated_at": now_iso(),
        "source": event.get("matcher") or event.get("hookEventName") or "session_start",
        "omg_version": VERSION,
    }
    write_json(path, payload)
    (root / "logs").mkdir(parents=True, exist_ok=True)
    return 0


def extract_prompt(event: dict[str, Any]) -> str:
    for key in ("prompt", "text", "userPrompt", "content"):
        value = event.get(key)
        if isinstance(value, str):
            return value
    return ""


def hook_keyword_detect() -> int:
    if skip_hooks("keyword-detect", "keyword-detector"):
        return 0
    event = read_stdin_json()
    prompt = extract_prompt(event)
    if not prompt:
        return 0
    cwd = Path(event.get("workspaceRoot") or event.get("cwd") or os.getcwd())
    root = resolve_omg_root(cwd)
    session = session_id_from(event)
    hits = []
    for name, skill, pattern in KEYWORD_RULES:
        if pattern.search(prompt):
            hits.append({"keyword": name, "skill": skill})
    if not hits:
        return 0
    write_json(
        session_dir(root, session) / "keyword-hits.json",
        {"session_id": session, "updated_at": now_iso(), "hits": hits},
    )
    log_path = root / "logs" / "keywords.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": now_iso(), "session_id": session, "hits": hits}) + "\n")
    return 0


def hook_pre_tool() -> int:
    if skip_hooks("pre-tool", "pre-tool-enforcer"):
        return 0
    event = read_stdin_json()
    tool = str(event.get("toolName") or event.get("tool_name") or "")
    if tool not in {"spawn_subagent", "Task", "Agent"}:
        return 0
    tool_input = event.get("toolInput") or event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    subagent = str(tool_input.get("subagent_type") or tool_input.get("subagentType") or "")
    name = subagent.split(":")[-1].strip().lower()
    if name in SKILL_NAMES:
        emit(
            {
                "decision": "deny",
                "reason": (
                    f"{subagent!r} is an OMG skill, not an agent. "
                    f"Invoke /oh-my-grok:{name} instead of spawn_subagent."
                ),
            }
        )
    return 0


def team_dir(root: Path, team: str) -> Path:
    slug = re.sub(r"[^a-z0-9-]", "-", team.lower()).strip("-") or "team"
    return state_dir(root) / "team" / slug


def worker_dir(root: Path, team: str, worker: str) -> Path:
    return team_dir(root, team) / "workers" / worker


def which_or_none(name: str) -> str | None:
    return shutil.which(name)


def cmux_in_caller() -> bool:
    return bool(os.environ.get("CMUX_WORKSPACE_ID") and which_or_none("cmux"))


def list_cmux_surfaces(workspace: str) -> set[str]:
    try:
        result = subprocess.run(
            ["cmux", "list-pane-surfaces", "--workspace", workspace, "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return set()
    if result.returncode != 0:
        return set()
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return set()
    found: set[str] = set()
    items = payload if isinstance(payload, list) else payload.get("surfaces") or payload.get("items") or []
    for item in items:
        if isinstance(item, dict):
            ident = item.get("id") or item.get("surfaceId") or item.get("surface")
            if ident:
                found.add(str(ident))
        elif isinstance(item, str):
            found.add(item)
    return found


def spawn_cmux_worker(prompt_file: Path, cwd: Path, model: str | None) -> dict[str, Any]:
    workspace = os.environ["CMUX_WORKSPACE_ID"]
    before = list_cmux_surfaces(workspace)
    created = subprocess.run(
        [
            "cmux",
            "new-pane",
            "--workspace",
            workspace,
            "--type",
            "terminal",
            "--direction",
            "right",
            "--focus",
            "false",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if created.returncode != 0:
        raise RuntimeError(created.stderr.strip() or "cmux new-pane failed")
    after = list_cmux_surfaces(workspace)
    new_surfaces = sorted(after - before)
    surface = new_surfaces[-1] if new_surfaces else os.environ.get("CMUX_SURFACE_ID", "")
    grok_bin = which_or_none("grok") or "grok"
    parts = [grok_bin, "--always-approve", "--cwd", str(cwd)]
    if model:
        parts.extend(["-m", model])
    parts.extend(["--prompt-file", str(prompt_file)])
    command = " ".join(shlex.quote(part) for part in parts) + "\n"
    send = subprocess.run(
        ["cmux", "send", "--surface", surface, "--focus", "false", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if send.returncode != 0:
        raise RuntimeError(send.stderr.strip() or "cmux send failed")
    return {"surface": surface, "workspace": workspace, "kind": "cmux"}


def spawn_headless_worker(prompt_file: Path, output_file: Path, cwd: Path, model: str | None) -> dict[str, Any]:
    grok_bin = which_or_none("grok") or "grok"
    cmd = [grok_bin, "-p", "--always-approve", "--cwd", str(cwd), "--prompt-file", str(prompt_file), "--output-format", "plain"]
    if model:
        cmd.extend(["-m", model])
    handle = output_file.open("w", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT)
    handle.close()
    return {"pid": proc.pid, "kind": "headless"}


def cmd_team_spawn(args: argparse.Namespace) -> int:
    cwd = Path(args.cwd).resolve() if args.cwd else Path.cwd()
    root = resolve_omg_root(cwd)
    worker = worker_dir(root, args.team, args.worker)
    worker.mkdir(parents=True, exist_ok=True)
    prompt_file = Path(args.prompt_file).resolve() if args.prompt_file else worker / "prompt.md"
    output_file = Path(args.output_file).resolve() if args.output_file else worker / "output.md"
    if args.prompt and not prompt_file.is_file():
        atomic_write(prompt_file, args.prompt)
    if not prompt_file.is_file():
        raise SystemExit("team spawn requires --prompt-file or --prompt")
    status: dict[str, Any] = {
        "team": args.team,
        "worker": args.worker,
        "provider": args.provider,
        "cwd": str(cwd),
        "prompt_file": str(prompt_file),
        "output_file": str(output_file),
        "spawned_at": now_iso(),
        "alive": True,
    }
    try:
        if args.provider == "grok" and cmux_in_caller() and not args.headless:
            status.update(spawn_cmux_worker(prompt_file, cwd, args.model))
        elif args.provider == "grok":
            status.update(spawn_headless_worker(prompt_file, output_file, cwd, args.model))
        else:
            binary = {"codex": "codex", "cursor": "cursor-agent", "gemini": "gemini"}.get(args.provider, args.provider)
            if not which_or_none(binary):
                raise RuntimeError(f"{binary} is not on PATH")
            if cmux_in_caller() and not args.headless:
                workspace = os.environ["CMUX_WORKSPACE_ID"]
                subprocess.run(
                    ["cmux", "new-pane", "--workspace", workspace, "--type", "terminal", "--direction", "right", "--focus", "false"],
                    check=False,
                )
            proc = subprocess.Popen(
                [binary, str(prompt_file)],
                cwd=cwd,
                stdout=output_file.open("w", encoding="utf-8"),
                stderr=subprocess.STDOUT,
            )
            status.update({"pid": proc.pid, "kind": "cli"})
    except Exception as exc:
        status["alive"] = False
        status["error"] = str(exc)
        write_json(worker / "status.json", status)
        emit(status)
        return 1
    write_json(worker / "status.json", status)
    emit(status)
    return 0


def cmd_team_status(args: argparse.Namespace) -> int:
    root = resolve_omg_root(effective_cwd(args))
    base = team_dir(root, args.team) / "workers"
    workers = []
    if base.is_dir():
        for path in sorted(base.iterdir()):
            data = read_json(path / "status.json")
            if isinstance(data, dict):
                workers.append(data)
    emit({"team": args.team, "workers": workers})
    return 0


def cmd_team_shutdown(args: argparse.Namespace) -> int:
    root = resolve_omg_root(effective_cwd(args))
    base = team_dir(root, args.team) / "workers"
    stopped = []
    if base.is_dir():
        for path in sorted(base.iterdir()):
            data = read_json(path / "status.json") or {}
            pid = data.get("pid") if isinstance(data, dict) else None
            if isinstance(pid, int) and pid > 1:
                try:
                    os.kill(pid, 15)
                    stopped.append({"worker": path.name, "pid": pid})
                except OSError:
                    stopped.append({"worker": path.name, "pid": pid, "missing": True})
            if isinstance(data, dict):
                data["alive"] = False
                data["stopped_at"] = now_iso()
                write_json(path / "status.json", data)
    emit({"team": args.team, "stopped": stopped})
    return 0


def agents_block() -> str:
    template = plugin_root() / "templates" / "AGENTS.md"
    if template.is_file():
        return template.read_text(encoding="utf-8").strip() + "\n"
    return (
        f"{START_MARKER}\n{VERSION_MARKER}\n\n"
        "# oh-my-grok\n\n"
        "Invoke skills with `/oh-my-grok:<name>`. "
        "Delegate with `spawn_subagent(subagent_type=\"oh-my-grok:<agent>\")`.\n"
        f"{END_MARKER}\n"
    )


def inject_block(path: Path, block: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if START_MARKER in existing and END_MARKER in existing:
        updated = re.sub(
            re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
            block.strip(),
            existing,
            count=1,
            flags=re.S,
        )
        action = "replaced"
    elif existing.strip():
        updated = existing.rstrip() + "\n\n" + block.strip() + "\n"
        action = "appended"
    else:
        updated = block.strip() + "\n"
        action = "created"
    if path.is_file() and existing != updated:
        backup = path.with_name(path.name + ".omg.bak")
        shutil.copy2(path, backup)
    if existing != updated:
        atomic_write(path, updated if updated.endswith("\n") else updated + "\n")
    return action


def ensure_gitignore(repo: Path) -> None:
    gitignore = repo / ".gitignore"
    snippet = ".omg/\n.omg-workspace\n"
    if gitignore.is_file():
        text = gitignore.read_text(encoding="utf-8")
        if ".omg/" in text:
            return
        atomic_write(gitignore, text.rstrip() + "\n\n# oh-my-grok runtime state\n" + snippet)
        return
    atomic_write(gitignore, "# oh-my-grok runtime state\n" + snippet)


def cmd_setup(args: argparse.Namespace) -> int:
    block = agents_block()
    results: dict[str, Any] = {"version": VERSION}
    if args.user or not args.project:
        user_agents = grok_home() / "AGENTS.md"
        results["user_agents"] = {"path": str(user_agents), "action": inject_block(user_agents, block)}
        config_dir = Path.home() / ".config" / "oh-my-grok"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.jsonc"
        if not config_path.is_file():
            write_json(
                config_path,
                {
                    "setupCompleted": now_iso(),
                    "setupVersion": VERSION,
                    "team": {"ops": {"maxAgents": 8, "defaultAgentType": "grok"}},
                },
            )
            results["user_config"] = str(config_path)
    if args.project or not args.user:
        cwd = effective_cwd(args)
        project_agents = cwd / "AGENTS.md"
        results["project_agents"] = {"path": str(project_agents), "action": inject_block(project_agents, block)}
        omg_root = resolve_omg_root(cwd)
        for name in ("state", "plans", "research", "logs", "artifacts", "handoffs", "wiki"):
            (omg_root / name).mkdir(parents=True, exist_ok=True)
        results["omg_root"] = str(omg_root)
        ensure_gitignore(omg_root.parent if omg_root.name == ".omg" else cwd)
    emit(results)
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    checks = []

    def add(name: str, status: str, details: str) -> None:
        checks.append({"check": name, "status": status, "details": details})

    add("omg.py", "OK", f"version {VERSION} at {Path(__file__).resolve()}")
    add("python3", "OK" if sys.version_info >= (3, 9) else "WARN", sys.version.split()[0])
    grok_bin = which_or_none("grok")
    add("grok", "OK" if grok_bin else "CRITICAL", grok_bin or "grok is not on PATH")
    root = plugin_root()
    required = [
        root / "plugin.json",
        root / "hooks" / "hooks.json",
        root / "templates" / "AGENTS.md",
        root / "skills" / "team" / "SKILL.md",
        root / "agents" / "executor.md",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    add("plugin files", "OK" if not missing else "CRITICAL", "all present" if not missing else f"missing: {missing}")
    user_agents = grok_home() / "AGENTS.md"
    if user_agents.is_file() and START_MARKER in user_agents.read_text(encoding="utf-8"):
        add("user AGENTS.md", "OK", str(user_agents))
    else:
        add("user AGENTS.md", "WARN", "run /oh-my-grok:omg-setup --user")
    add("cmux", "OK" if which_or_none("cmux") else "WARN", os.environ.get("CMUX_WORKSPACE_ID") or "optional; used for visible /team panes")
    add("DISABLE_OMG", "OK" if os.environ.get("DISABLE_OMG") not in {"1", "true"} else "WARN", os.environ.get("DISABLE_OMG") or "unset")
    worst = "CRITICAL" if any(item["status"] == "CRITICAL" for item in checks) else "WARN" if any(item["status"] == "WARN" for item in checks) else "HEALTHY"
    emit({"summary": worst, "checks": checks})
    return 0 if worst != "CRITICAL" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omg", description="oh-my-grok runtime")
    parser.add_argument("--cwd", help="working directory override")
    parser.add_argument("--session", help="session id override")
    sub = parser.add_subparsers(dest="cmd", required=True)

    state = sub.add_parser("state")
    state_sub = state.add_subparsers(dest="state_cmd", required=True)
    state_sub.add_parser("resolve")
    read = state_sub.add_parser("read")
    read.add_argument("--mode", required=True)
    write = state_sub.add_parser("write")
    write.add_argument("--mode", required=True)
    write.add_argument("--active")
    write.add_argument("--phase")
    write.add_argument("--json")
    write.add_argument("--set", action="append", default=[])
    clear = state_sub.add_parser("clear")
    clear.add_argument("--mode", required=True)
    clear.add_argument("--no-signal", action="store_true")
    state_sub.add_parser("list")
    state_sub.add_parser("status")

    hook = sub.add_parser("hook")
    hook.add_argument("hook_name", choices=["persistent-mode", "session-start", "keyword-detect", "pre-tool"])

    team = sub.add_parser("team")
    team_sub = team.add_subparsers(dest="team_cmd", required=True)
    spawn = team_sub.add_parser("spawn")
    spawn.add_argument("--team", required=True)
    spawn.add_argument("--worker", required=True)
    spawn.add_argument("--provider", default="grok", choices=["grok", "codex", "cursor", "gemini"])
    spawn.add_argument("--prompt-file")
    spawn.add_argument("--output-file")
    spawn.add_argument("--prompt")
    spawn.add_argument("--model")
    spawn.add_argument("--headless", action="store_true")
    status = team_sub.add_parser("status")
    status.add_argument("--team", required=True)
    shutdown = team_sub.add_parser("shutdown")
    shutdown.add_argument("--team", required=True)

    setup = sub.add_parser("setup")
    setup.add_argument("--user", action="store_true")
    setup.add_argument("--project", action="store_true")
    setup.add_argument("--force", action="store_true")

    sub.add_parser("doctor")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "state":
        mapping = {
            "resolve": cmd_state_resolve,
            "read": cmd_state_read,
            "write": cmd_state_write,
            "clear": cmd_state_clear,
            "list": cmd_state_list,
            "status": cmd_state_status,
        }
        return mapping[args.state_cmd](args)
    if args.cmd == "hook":
        mapping = {
            "persistent-mode": hook_persistent_mode,
            "session-start": hook_session_start,
            "keyword-detect": hook_keyword_detect,
            "pre-tool": hook_pre_tool,
        }
        return mapping[args.hook_name]()
    if args.cmd == "team":
        mapping = {
            "spawn": cmd_team_spawn,
            "status": cmd_team_status,
            "shutdown": cmd_team_shutdown,
        }
        return mapping[args.team_cmd](args)
    if args.cmd == "setup":
        return cmd_setup(args)
    if args.cmd == "doctor":
        return cmd_doctor(args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
