# -*- coding: utf-8 -*-
"""claude -p บน Windows ต้องมี Git bash หรือ PowerShell 7 (9 ก.ค. 2026).

แอปบน server รันเป็น **SYSTEM** ซึ่งไม่มี WSL distro (WSL ผูกกับ user) →
`claude` ตายทันทีด้วย "Claude Code on Windows requires either Git for Windows
(for bash) or PowerShell". ทดสอบในสิทธิ์ yklog จะไม่เจอบั๊กนี้ (เคยหลงมาแล้ว).

ทางแก้: ชี้ `CLAUDE_CODE_GIT_BASH_PATH` ให้ claude เอง — หาไฟล์จากที่ติดตั้งมาตรฐาน
หรือ override ด้วย env `YK_GIT_BASH`.
"""
import os

import pytest

from services import ai_assist


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("CLAUDE_CODE_GIT_BASH_PATH", "YK_GIT_BASH"):
        monkeypatch.delenv(k, raising=False)


def test_env_gets_git_bash_when_found(monkeypatch):
    found = r"C:\Program Files\Git\bin\bash.exe"
    monkeypatch.setattr(ai_assist.os.path, "exists", lambda p: p == found)
    env = ai_assist._claude_env()
    assert env["CLAUDE_CODE_GIT_BASH_PATH"] == found


def test_explicit_yk_git_bash_wins(monkeypatch):
    monkeypatch.setenv("YK_GIT_BASH", r"D:\git\bash.exe")
    monkeypatch.setattr(ai_assist.os.path, "exists", lambda p: True)
    assert ai_assist._claude_env()["CLAUDE_CODE_GIT_BASH_PATH"] == r"D:\git\bash.exe"


def test_existing_claude_env_var_not_overwritten(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_GIT_BASH_PATH", r"E:\already\bash.exe")
    monkeypatch.setattr(ai_assist.os.path, "exists", lambda p: True)
    assert ai_assist._claude_env()["CLAUDE_CODE_GIT_BASH_PATH"] == r"E:\already\bash.exe"


def test_no_git_bash_leaves_env_alone(monkeypatch):
    monkeypatch.setattr(ai_assist.os.path, "exists", lambda p: False)
    env = ai_assist._claude_env()
    assert "CLAUDE_CODE_GIT_BASH_PATH" not in env


def test_chat_claude_passes_env_to_subprocess(monkeypatch, tmp_path):
    """ของจริง: chat_claude ต้องส่ง env ตัวนี้เข้า subprocess ไม่ใช่แค่คำนวณทิ้ง."""
    fake_exe = tmp_path / "claude.exe"
    fake_exe.write_text("x")
    monkeypatch.setenv("YK_GIT_BASH", str(tmp_path / "bash.exe"))
    monkeypatch.setattr(ai_assist, "_claude_exe", lambda: str(fake_exe))
    monkeypatch.setattr(ai_assist.os.path, "exists", lambda p: True)
    seen = {}

    class _R:
        returncode = 0
        stdout = "OK"
        stderr = ""

    def fake_run(cmd, **kw):
        seen["env"] = kw.get("env") or {}
        return _R()

    monkeypatch.setattr(ai_assist.subprocess, "run", fake_run)

    assert ai_assist.chat_claude("ทดสอบ") == "OK"
    assert seen["env"]["CLAUDE_CODE_GIT_BASH_PATH"] == str(tmp_path / "bash.exe")
