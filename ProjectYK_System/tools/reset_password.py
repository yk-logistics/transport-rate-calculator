# -*- coding: utf-8 -*-
"""รีเซตรหัสผ่านผู้ใช้ MVP — รันบนเครื่องเซิร์ฟเวอร์ (ดับเบิลคลิก RESET_PASSWORD.bat บน Desktop)

ใช้เมื่อลืมรหัสผ่าน (รวมถึง admin ลืมเอง): เลือก user → ได้รหัสชั่วคราว →
ล็อกอินแล้วระบบบังคับตั้งรหัสใหม่ทันที (must_change_pw)

รายละเอียด/แผนสำรอง: docs/MVP_ADMIN_RECOVERY_RUNBOOK.md
"""
from __future__ import annotations

import secrets
import sqlite3
import subprocess
import sys
from pathlib import Path

import bcrypt

# ตัวอักษรอ่านง่าย — ตัด 0/O/1/l/i ที่ดูสับสน
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
PW_LEN = 10  # แอปบังคับขั้นต่ำ 8

APP_TASK = "YK_MVP_APP"


def find_db() -> Path:
    here = Path(__file__).resolve().parent
    for cand in (here / "app.db", here.parent / "app" / "app.db"):
        if cand.exists():
            return cand
    sys.exit("ไม่พบ app.db (วางสคริปต์ไว้ในโฟลเดอร์เดียวกับ app.db หรือใช้ --db <path>)")


def gen_temp_pw() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(PW_LEN))


def list_users(db_path: Path) -> list[tuple]:
    con = sqlite3.connect(db_path)
    try:
        return con.execute(
            "SELECT id, username, display_name, role, status FROM appuser ORDER BY id"
        ).fetchall()
    finally:
        con.close()


def reset_user(db_path: Path, user_id: int) -> str:
    temp_pw = gen_temp_pw()
    pw_hash = bcrypt.hashpw(temp_pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute(
            "UPDATE appuser SET password_hash=?, must_change_pw=1 WHERE id=?",
            (pw_hash, user_id),
        )
        con.commit()
        if cur.rowcount != 1:
            sys.exit(f"ไม่พบ user id {user_id} — ไม่ได้แก้อะไร")
    finally:
        con.close()
    return temp_pw


def restart_app() -> None:
    """รีสตาร์ทแอป (ล้างตัวล็อก 15 นาทีของ login_guard ซึ่งอยู่ใน memory)"""
    ps = (
        f"Stop-ScheduledTask -TaskName {APP_TASK}; Start-Sleep 2; "
        "$c = Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue; "
        "if ($c) { Stop-Process -Id $c.OwningProcess -Force }; Start-Sleep 1; "
        f"Start-ScheduledTask -TaskName {APP_TASK}; Start-Sleep 4; "
        "if (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue) "
        "{ 'OK: app is back on port 8010' } else { 'WARN: port 8010 not listening yet' }"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=60,
        )
        print(out.stdout.strip() or out.stderr.strip())
        if out.returncode != 0:
            print("รีสตาร์ทไม่สำเร็จ — ลองคลิกขวาไฟล์ .bat → Run as administrator "
                  "หรือรอ 15 นาทีแล้วล็อกอินใหม่")
    except Exception as e:  # noqa: BLE001 — เครื่องมือกู้ฉุกเฉิน อย่าตายกลางทาง
        print(f"รีสตาร์ทไม่สำเร็จ ({e}) — รอ 15 นาทีแล้วล็อกอินใหม่ได้เช่นกัน")


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if "--db" in sys.argv:
        db_path = Path(sys.argv[sys.argv.index("--db") + 1])
        if not db_path.exists():
            sys.exit(f"ไม่พบไฟล์ {db_path}")
    else:
        db_path = find_db()

    print("=== รีเซตรหัสผ่านผู้ใช้ MVP ===")
    print(f"ฐานข้อมูล: {db_path}\n")

    users = list_users(db_path)
    for uid, username, display_name, role, status in users:
        flag = "" if status == "active" else f"  << {status}"
        print(f"  [{uid}] {username}  ({role})  {display_name}{flag}")

    choice = input("\nพิมพ์หมายเลข [id] ของคนที่จะรีเซตรหัส (Enter เปล่า = ยกเลิก): ").strip()
    if not choice:
        print("ยกเลิก ไม่ได้แก้อะไร")
        return
    valid_ids = {u[0] for u in users}
    if not choice.isdigit() or int(choice) not in valid_ids:
        sys.exit(f"หมายเลข '{choice}' ไม่อยู่ในรายชื่อ — ยกเลิก")
    uid = int(choice)
    username = next(u[1] for u in users if u[0] == uid)

    temp_pw = reset_user(db_path, uid)
    print()
    print("=" * 46)
    print(f"  user:          {username}")
    print(f"  รหัสชั่วคราว:  {temp_pw}")
    print("=" * 46)
    print("ล็อกอินด้วยรหัสนี้ แล้วระบบจะบังคับตั้งรหัสใหม่ทันที")
    print("(รหัสนี้ใช้ได้จนกว่าจะตั้งรหัสใหม่ — อย่าทิ้งไว้บนกระดาษ)")

    ans = input("\nถ้าเพิ่งใส่รหัสผิดเกิน 5 ครั้ง ชื่อจะโดนล็อก 15 นาที — "
                "รีสตาร์ทแอปเพื่อปลดล็อกเลยไหม? (y/N): ").strip().lower()
    if ans == "y":
        restart_app()
    else:
        print("ไม่รีสตาร์ท — ถ้าล็อกอินไม่ผ่านเพราะโดนล็อก ให้รอ 15 นาทีแล้วลองใหม่")


if __name__ == "__main__":
    main()
