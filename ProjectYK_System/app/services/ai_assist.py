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


def rewrite_todo(text: str, categories: list[str]) -> dict:
    """ส่งข้อความโน้ตให้ Qwen แก้คำผิด+จัดหมวด → {"text":..., "category":...}.

    พังทางไหนก็ตาม (คีย์หาย/เน็ต/ตอบไม่เป็น JSON) โยน RuntimeError
    ข้อความภาษาคน — หน้าเว็บเอาไปโชว์ตรงๆ ได้.
    """
    # ใช้ท่า OpenAI /v1/chat/completions — ท่า Anthropic /v1/messages บน gateway นี้
    # คืน content ว่าง (LiteLLM แปลงแล้วข้อความหาย — พิสูจน์สด 5ก.ค.)
    body = json.dumps({
        "model": QWEN_MODEL,
        "max_tokens": 1000,
        "temperature": 0,  # งานพิสูจน์อักษร — ไม่ต้องการความสร้างสรรค์ (เคยเปลี่ยน 'พรุ่งนี้'→'บ่ายนี้')
        "messages": [
            {"role": "system", "content": _SYSTEM.format(cats=", ".join(categories) or "-")},
            {"role": "user", "content": text},
        ],
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
