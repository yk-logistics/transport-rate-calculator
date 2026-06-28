"""Read-only guard: เทียบ payrun BIGC net + DailyJob counts ก่อน/หลัง import.
รับรองว่า import เดลี่ 'ไม่' ขยับ net ที่ลอกจากแบงค์ และ 'ไม่' แตะ LCB."""
import io, json, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import sqlite3

DB = str(Path(__file__).resolve().parents[1] / "app" / "app.db")
OUT = Path(__file__).resolve().parents[2] / "reports" / "_bigc_guard.json"


def snap():
    con = sqlite3.connect(DB); cur = con.cursor()
    net = {}
    for r in cur.execute("""SELECT pr.pay_cycle_tag, ROUND(SUM(pi.net_pay),2)
                            FROM payrun pr JOIN payrunitem pi ON pi.pay_run_id=pr.id
                            WHERE pr.site_code='BIGC' GROUP BY pr.pay_cycle_tag"""):
        net[r[0]] = r[1]
    cnt = {}
    for r in cur.execute("SELECT site_code, COUNT(*) FROM dailyjob GROUP BY site_code"):
        cnt[r[0]] = r[1]
    con.close()
    return {"bigc_net": net, "dailyjob_count": cnt}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "show"
    cur = snap()
    if mode == "before":
        OUT.write_text(json.dumps(cur, ensure_ascii=False, indent=2), encoding="utf-8")
        print("BEFORE saved:", json.dumps(cur, ensure_ascii=False))
    elif mode == "after":
        before = json.loads(OUT.read_text(encoding="utf-8"))
        print("BEFORE:", json.dumps(before, ensure_ascii=False))
        print("AFTER :", json.dumps(cur, ensure_ascii=False))
        net_same = before["bigc_net"] == cur["bigc_net"]
        lcb_same = before["dailyjob_count"].get("LCB") == cur["dailyjob_count"].get("LCB")
        print(f"BIGC net unchanged: {net_same}")
        print(f"LCB DailyJob unchanged: {lcb_same}")
        if not (net_same and lcb_same):
            raise SystemExit("[GUARD FAIL] net หรือ LCB เปลี่ยน — ตรวจด่วน")
        print("[GUARD OK]")
    else:
        print(json.dumps(cur, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
