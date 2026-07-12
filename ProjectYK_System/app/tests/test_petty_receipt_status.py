# -*- coding: utf-8 -*-
"""v53: ใบเสร็จสดย่อย 3 สถานะ (มี/ไม่มี/รอ) — แทนติ๊ก 2 ทาง + ปุ่มเดียวปิดใบเสร็จ.

โจทย์โอ 12ก.ค.: คีย์ก่อน รอปิดใบเสร็จทีหลัง เหมือนย้ายช่องใน Excel สดย่อย
(รอใบเสร็จ → มีใบเสร็จ) โดยไม่ต้องแก้สองที่.
"""
from datetime import date

from sqlmodel import Session, select

from db_config import engine
from models import AppUser, PettyCashTxn


def _login(client):
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False
        s.add(u); s.commit()
    client.post("/login", data={"username": "yk1", "password": "changeme1"})


def _new_txn(client, **over):
    data = {"txn_date": "2026-07-12", "site_code": "LCB", "direction": "out",
            "amount": "500", "requester_raw": "สมชาย", "memo": "ค่ารับตู้",
            "category": "other", "receipt_status": "waiting"}
    data.update(over)
    r = client.post("/petty-cash/new", data=data, follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        return s.exec(select(PettyCashTxn).order_by(PettyCashTxn.id.desc())).first()


def test_save_waiting_shows_in_clearance_without_pending_amount(client):
    _login(client)
    row = _new_txn(client)
    assert row.receipt_status == "waiting"
    assert row.has_receipt is False
    page = client.get("/petty-cash/clearance").text
    assert "ค่ารับตู้" in page          # โผล่รอเคลียร์แม้ยอดทอน = 0


def test_receipt_got_button_closes_in_one_click(client):
    _login(client)
    row = _new_txn(client)
    r = client.post(f"/petty-cash/{row.id}/receipt-got", follow_redirects=False)
    assert r.status_code == 303
    with Session(engine) as s:
        row2 = s.get(PettyCashTxn, row.id)
    assert row2.receipt_status == "have"
    assert row2.has_receipt is True
    assert "ค่ารับตู้" not in client.get("/petty-cash/clearance").text


def test_save_have_syncs_has_receipt(client):
    _login(client)
    row = _new_txn(client, receipt_status="have")
    assert row.receipt_status == "have" and row.has_receipt is True
    row2 = _new_txn(client, receipt_status="none", memo="ไม่มีบิล")
    assert row2.receipt_status == "none" and row2.has_receipt is False


def test_legacy_rows_without_status_untouched(client):
    _login(client)
    with Session(engine) as s:
        s.add(PettyCashTxn(txn_date=date(2026, 7, 1), site_code="LCB",
                           amount=100.0, memo="แถวเก่า", has_receipt=True))
        s.commit()
    page = client.get("/petty-cash/clearance").text
    assert "แถวเก่า" not in page        # ไม่โดนลากเข้ารอเคลียร์
