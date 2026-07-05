"""AI ช่วยเรียบเรียงโน้ต /todo (เฟส 2 LINE→todo) — เรียก Qwen ฟรีผ่าน 9arm gateway.

กฎยืน: AI เสนอเป็น draft เท่านั้น — ห้ามเขียน DB เอง (โอกด "ใช้ตามนี้" บนหน้า /todo
ถึงจะบันทึกผ่าน /todo/{id}/update ตามปกติ). คีย์อ่านจาก env YK_QWEN_KEY
(หรือไฟล์ตาม YK_QWEN_KEY_FILE) — ไม่ hardcode, ไม่ลง git.
"""
import json
import os
import re
import urllib.request

QWEN_BASE = os.getenv("YK_QWEN_BASE", "https://gateway.9arm.co")
QWEN_MODEL = os.getenv("YK_QWEN_MODEL", "qwen3.6-35b-a3b")

_SYSTEM = (
    "คุณเป็นเสมียนพิสูจน์อักษรโน้ตสั่งงานของบริษัทขนส่ง หน้าที่ของคุณ:\n"
    "1. เขียนข้อความใหม่ให้สะกดถูกต้องทุกคำ เช่น 'ดว่น'→'ด่วน', 'เปลียน'→'เปลี่ยน',"
    " 'พรุ้งนี'→'พรุ่งนี้' — แก้ให้จริง อย่าคัดลอกคำผิดเดิมมา"
    " แต่แก้เฉพาะตัวสะกด ห้ามเปลี่ยนเป็นคำอื่นที่ความหมายต่างออกไป ถ้าไม่แน่ใจให้คงคำเดิม\n"
    "2. จัดวรรคตอน/ขึ้นบรรทัดให้อ่านง่าย แต่ห้ามเพิ่มข้อมูลใหม่ ห้ามตัดข้อมูลทิ้ง —"
    " ทะเบียนรถ ตัวเลข จำนวนเงิน ชื่อคน วันที่ คงเดิมทุกตัว\n"
    "3. บรรทัดที่ขึ้นต้นด้วย 📱 หรือ (⚠️ เป็นบันทึกที่มา — คัดลอกไว้ท้ายข้อความตามเดิมไม่ต้องแก้\n"
    "4. เลือกหมวดตามเนื้อหางานหนึ่งหมวด: แจ้งซ่อม / งาน / เบิกของ"
    " (หรือหมวดอื่นที่ใช้อยู่แล้วถ้าตรงกว่า: {cats} — ห้ามใช้ 'ไลน์' เพราะเป็นแค่ป้ายที่มา)\n"
    'ตอบเป็น JSON อย่างเดียว: {{"text": "ข้อความที่เรียบเรียงแล้ว", "category": "หมวด"}}'
)


def _api_key() -> str:
    key = os.getenv("YK_QWEN_KEY", "").strip()
    if not key:
        kf = os.getenv("YK_QWEN_KEY_FILE", "").strip()
        if kf and os.path.exists(kf):
            with open(kf, encoding="utf-8") as f:
                key = f.read().strip()
    if not key:
        raise RuntimeError("ยังไม่ได้ตั้งคีย์ AI (YK_QWEN_KEY) — แจ้งแอดมิน")
    return key


def chat_qwen(messages: list[dict], max_tokens: int = 1000, temperature: float = 0) -> str:
    """ยิง messages (ท่า OpenAI role/content) ไป Qwen ผ่าน 9arm → คืนข้อความตอบ.

    ใช้ท่า OpenAI /v1/chat/completions — ท่า Anthropic /v1/messages บน gateway นี้
    คืน content ว่าง (LiteLLM แปลงแล้วข้อความหาย — พิสูจน์สด 5ก.ค.).
    พังทางไหนก็ตามโยน RuntimeError ข้อความภาษาคน — หน้าเว็บเอาไปโชว์ตรงๆ ได้."""
    body = json.dumps({
        "model": QWEN_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }).encode()
    req = urllib.request.Request(
        f"{QWEN_BASE}/v1/chat/completions", data=body, method="POST",
        headers={"content-type": "application/json",
                 "authorization": f"Bearer {_api_key()}",
                 # WAF หน้า gateway บล็อก UA ดีฟอลต์ของ Python (403) — ต้องตั้งเอง
                 "user-agent": "yk-todo-ai/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode())
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"เรียก AI ไม่สำเร็จ ({e.__class__.__name__}) — ลองใหม่อีกครั้ง") from e
    raw = ((resp.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    if not raw.strip():
        raise RuntimeError("AI ไม่ได้ส่งคำตอบกลับมา — ลองใหม่อีกครั้ง")
    return raw


def _parse_draft(raw: str, text: str) -> dict:
    """แกะ JSON จากคำตอบ AI + กันบันทึกที่มา (📱/(⚠️) หาย — ใช้ร่วม Qwen/Claude."""
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        d = json.loads(m.group()) if m else {}
    except json.JSONDecodeError:
        d = {}
    draft = str(d.get("text") or "").strip()
    if not draft:
        raise RuntimeError("AI ตอบมาไม่เป็นรูปแบบที่อ่านได้ — ลองกดใหม่อีกครั้ง")
    # กันบันทึกที่มาหาย: บรรทัด 📱 / (⚠️ จากหน้า /line ต้องยังอยู่ใน draft เสมอ
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith(("📱", "(⚠️")) and s not in draft:
            draft += "\n\n" + s
    return {"text": draft, "category": str(d.get("category") or "").strip()}


def rewrite_todo(text: str, categories: list[str], provider: str = "auto") -> dict:
    """เรียบเรียงโน้ต → {"text":..., "category":..., "engine": "qwen"|"claude"}.

    provider (ตั้งได้ที่หน้า /ai): "auto" = Qwen ฟรีก่อน ถ้าพัง fallback Claude,
    "qwen"/"claude" = ใช้ตัวนั้นตัวเดียว."""
    sys_prompt = _SYSTEM.format(cats=", ".join(categories) or "-")
    if provider != "claude":
        try:
            # temperature 0: งานพิสูจน์อักษร — ไม่ต้องการความสร้างสรรค์
            # (เคยเปลี่ยน 'พรุ่งนี้'→'บ่ายนี้')
            raw = chat_qwen([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text},
            ])
            return {**_parse_draft(raw, text), "engine": "qwen"}
        except RuntimeError:
            if provider == "qwen" or not claude_available():
                raise
    raw = chat_claude(sys_prompt + "\n\nโน้ตต้นฉบับ:\n" + text, timeout=120)
    return {**_parse_draft(raw, text), "engine": "claude"}


# ---- Claude ผ่าน `claude -p` headless (เฟส 3 หน้า /ai) -------------------------
# เอา token Max ยิง API ตรง = ผิด ToS; claude -p บนเครื่องที่ login ด้วย Max ของโอ = ได้
# (โควต้าแชร์กับเซสชันทำงานของโอ). อ่านอย่างเดียวเป็น guard จริงผ่าน --allowedTools.

def _claude_exe() -> str | None:
    import shutil

    exe = os.getenv("YK_CLAUDE_EXE", "").strip()
    if exe and os.path.exists(exe):
        return exe
    exe = shutil.which("claude")
    if exe:
        return exe
    p = os.path.expanduser(r"~\.local\bin\claude.exe")
    return p if os.path.exists(p) else None


def claude_available() -> bool:
    return _claude_exe() is not None


def chat_claude(prompt: str, cwd: str | None = None, timeout: int = 180) -> str:
    """ถาม Claude ด้วย claude -p อ่านอย่างเดียว (Read,Grep,Glob) — คืนข้อความตอบ.

    ตั้ง CLAUDE_CONFIG_DIR ชี้โปรไฟล์ที่ login ไว้ได้ผ่าน env YK_CLAUDE_CONFIG
    (จำเป็นบน server: แอปรันเป็น SYSTEM แต่ Max login อยู่โปรไฟล์ yklog)."""
    import subprocess

    exe = _claude_exe()
    if not exe:
        raise RuntimeError("เครื่องนี้ยังไม่ได้ติดตั้ง/ล็อกอิน claude CLI — ใช้ Qwen ไปก่อน "
                           "(วิธีติดตั้งอยู่ใน docs/AI_CHAT_RUNBOOK.md)")
    env = dict(os.environ)
    cfg = os.getenv("YK_CLAUDE_CONFIG", "").strip()
    if cfg:
        env["CLAUDE_CONFIG_DIR"] = cfg
    try:
        r = subprocess.run(
            [exe, "-p", prompt, "--allowedTools", "Read,Grep,Glob"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, cwd=cwd, env=env)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Claude ใช้เวลานานเกินไป — ลองถามสั้นลงหรือใช้ Qwen")
    if r.returncode != 0 or not (r.stdout or "").strip():
        tail = (r.stderr or r.stdout or "").strip()[-300:]
        raise RuntimeError(f"เรียก Claude ไม่สำเร็จ: {tail or 'ไม่มีคำตอบ'}")
    return r.stdout.strip()
