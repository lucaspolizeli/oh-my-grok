#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OMG = ROOT / "scripts" / "omg.py"


def run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.pop("DISABLE_OMG", None)
    merged.pop("OMG_SKIP_HOOKS", None)
    merged.pop("OMG_STATE_DIR", None)
    merged.pop("OMG_SESSION_ID", None)
    merged.pop("GROK_SESSION_ID", None)
    merged.pop("GROK_WORKSPACE_ROOT", None)
    merged.pop("CLAUDE_PROJECT_DIR", None)
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(OMG), *args],
        cwd=cwd,
        env=merged,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )


def payload(proc: subprocess.CompletedProcess[str]) -> dict:
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


class OmgRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / ".git").mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_state_roundtrip(self) -> None:
        env = {"OMG_SESSION_ID": "ses-1"}
        written = payload(
            run(
                ["state", "write", "--mode", "ralph", "--active", "true", "--phase", "execution", "--json", '{"iteration": 2}'],
                cwd=self.cwd,
                env=env,
            )
        )
        self.assertTrue(written["active"])
        self.assertEqual(written["current_phase"], "execution")
        self.assertEqual(written["iteration"], 2)
        read = payload(run(["state", "read", "--mode", "ralph"], cwd=self.cwd, env=env))
        self.assertEqual(read["session_id"], "ses-1")
        status = payload(run(["state", "status"], cwd=self.cwd, env=env))
        self.assertEqual(status["active"][0]["mode"], "ralph")

    def test_state_dir_env(self) -> None:
        store = (self.cwd / "central").resolve()
        env = {"OMG_STATE_DIR": str(store), "OMG_SESSION_ID": "s"}
        run(["state", "write", "--mode", "team", "--active", "true"], cwd=self.cwd, env=env)
        resolved = payload(run(["state", "resolve"], cwd=self.cwd, env=env))
        self.assertTrue(Path(resolved["omg_root"]).resolve().is_relative_to(store))
        self.assertTrue(list(store.glob("*/state/sessions/s/team-state.json")))

    def test_workspace_marker(self) -> None:
        parent = self.cwd
        (parent / ".omg-workspace").write_text("", encoding="utf-8")
        child = parent / "repo-a"
        child.mkdir()
        env = {"OMG_SESSION_ID": "s"}
        run(["state", "write", "--mode", "ralph", "--active", "true"], cwd=child, env=env)
        self.assertTrue((parent / ".omg" / "state" / "sessions" / "s" / "ralph-state.json").is_file())

    def test_clear_writes_cancel_signal(self) -> None:
        env = {"OMG_SESSION_ID": "s"}
        run(["state", "write", "--mode", "ralph", "--active", "true"], cwd=self.cwd, env=env)
        run(["state", "clear", "--mode", "ralph"], cwd=self.cwd, env=env)
        status = payload(run(["state", "status"], cwd=self.cwd, env=env))
        self.assertEqual(status["active"], [])
        self.assertTrue(status["cancel_signal"])

    def test_persistent_mode_blocks(self) -> None:
        env = {"OMG_SESSION_ID": "s"}
        run(["state", "write", "--mode", "ralph", "--active", "true", "--phase", "execution"], cwd=self.cwd, env=env)
        event = json.dumps({"reason": "end_turn", "sessionId": "s", "cwd": str(self.cwd), "workspaceRoot": str(self.cwd)})
        proc = run(["hook", "persistent-mode"], cwd=self.cwd, env=env, stdin=event)
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertEqual(data["decision"], "block")
        self.assertIn("boulder never stops", data["reason"])

    def test_persistent_mode_allows_when_disabled(self) -> None:
        env = {"OMG_SESSION_ID": "s", "DISABLE_OMG": "1"}
        run(["state", "write", "--mode", "ralph", "--active", "true"], cwd=self.cwd, env={"OMG_SESSION_ID": "s"})
        event = json.dumps({"reason": "end_turn", "sessionId": "s", "cwd": str(self.cwd), "workspaceRoot": str(self.cwd)})
        proc = run(["hook", "persistent-mode"], cwd=self.cwd, env=env, stdin=event)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "")

    def test_persistent_mode_allows_after_cancel_signal(self) -> None:
        env = {"OMG_SESSION_ID": "s"}
        run(["state", "write", "--mode", "ralph", "--active", "true"], cwd=self.cwd, env=env)
        run(["state", "clear", "--mode", "ralph"], cwd=self.cwd, env=env)
        event = json.dumps({"reason": "end_turn", "sessionId": "s", "cwd": str(self.cwd), "workspaceRoot": str(self.cwd)})
        proc = run(["hook", "persistent-mode"], cwd=self.cwd, env=env, stdin=event)
        self.assertEqual(proc.stdout.strip(), "")

    def test_pre_tool_denies_skill_as_agent(self) -> None:
        event = json.dumps(
            {
                "toolName": "spawn_subagent",
                "toolInput": {"subagent_type": "oh-my-grok:ralph"},
            }
        )
        proc = run(["hook", "pre-tool"], cwd=self.cwd, stdin=event)
        data = json.loads(proc.stdout)
        self.assertEqual(data["decision"], "deny")
        self.assertIn("/oh-my-grok:ralph", data["reason"])

    def test_keyword_detect(self) -> None:
        env = {"OMG_SESSION_ID": "s"}
        event = json.dumps({"prompt": "please ralph this until done", "sessionId": "s", "cwd": str(self.cwd), "workspaceRoot": str(self.cwd)})
        proc = run(["hook", "keyword-detect"], cwd=self.cwd, env=env, stdin=event)
        self.assertEqual(proc.returncode, 0)
        hits = json.loads((self.cwd / ".omg" / "state" / "sessions" / "s" / "keyword-hits.json").read_text())
        self.assertEqual(hits["hits"][0]["skill"], "ralph")

    def test_setup_preserves_surrounding_agents(self) -> None:
        agents = self.cwd / "AGENTS.md"
        agents.write_text("# keep me\n\ncmux rules stay.\n", encoding="utf-8")
        env = {"GROK_PLUGIN_ROOT": str(ROOT)}
        result = payload(run(["setup", "--project"], cwd=self.cwd, env=env))
        text = agents.read_text(encoding="utf-8")
        self.assertIn("# keep me", text)
        self.assertIn("cmux rules stay.", text)
        self.assertIn("<!-- OMG:START -->", text)
        self.assertIn("<!-- OMG:END -->", text)
        self.assertEqual(result["project_agents"]["action"], "appended")
        payload(run(["setup", "--project"], cwd=self.cwd, env=env))
        again = agents.read_text(encoding="utf-8")
        self.assertEqual(again.count("<!-- OMG:START -->"), 1)

    def test_doctor_runs(self) -> None:
        env = {"GROK_PLUGIN_ROOT": str(ROOT)}
        proc = run(["doctor"], cwd=self.cwd, env=env)
        data = json.loads(proc.stdout)
        self.assertIn(data["summary"], {"HEALTHY", "WARN", "CRITICAL"})
        names = [item["check"] for item in data["checks"]]
        self.assertIn("plugin files", names)


if __name__ == "__main__":
    unittest.main()
