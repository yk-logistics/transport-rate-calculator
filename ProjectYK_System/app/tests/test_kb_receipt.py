# -*- coding: utf-8 -*-
"""A2 ใบเสร็จ+ใบหัก 50ทวิ: เลขถูกต้อง (KB เต็ม → หัก 3% → โอน 90%) + เลขเอกสาร
idempotent + Doc Designer save/override/reset."""
import json
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import AppUser, DocIssue, DocTemplate, KbSettle
from services import doc_templates as dt


@pytest.fixture()
def client():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        u = s.exec(select(AppUser).where(AppUser.username == "yk1")).first()
        u.must_change_pw = False; s.add(u)
        # เคสจริงในสเปค: ชุด CYIV2606-023+026 KB รวม 1,713 → หัก 51.39 โอน 1,541.70
        s.add(KbSettle(inv_no="CYIV2606-023", kb_amount=942.0, transfer_amount=19027.98))
        s.add(KbSettle(inv_no="CYIV2606-026", kb_amount=771.0, transfer_amount=19027.98))
        s.commit()
    with TestClient(appmod.app) as c:
        c.post("/login", data={"username": "yk1", "password": "changeme1"})
        yield c


def test_baht_text():
    assert dt.baht_text(1713) == "หนึ่งพันเจ็ดร้อยสิบสามบาทถ้วน"
    assert dt.baht_text(51.39) == "ห้าสิบเอ็ดบาทสามสิบเก้าสตางค์"
    assert dt.baht_text(1541.70) == "หนึ่งพันห้าร้อยสี่สิบเอ็ดบาทเจ็ดสิบสตางค์"
    assert dt.baht_text(2500000) == "สองล้านห้าแสนบาทถ้วน"


def test_receipt_numbers_match_spec_case(client):
    r = client.get("/kb-payout/receipt?invs=CYIV2606-023,CYIV2606-026")
    assert r.status_code == 200
    assert "1,713.00" in r.text                      # ใบเสร็จ = KB เต็ม
    assert "51.39" in r.text                          # ใบหัก = 3%
    assert "1,541.70" in r.text                       # โอนคืน 90% ใน note
    assert "หนึ่งพันเจ็ดร้อยสิบสามบาทถ้วน" in r.text
    assert "ชาญณรงค์ มาลีแย้ม" in r.text               # เจ้าของงาน CY
    assert "หนังสือรับรองการหักภาษี ณ ที่จ่าย" in r.text


def test_doc_no_idempotent_and_running(client):
    a = client.get("/kb-payout/receipt?invs=CYIV2606-023,CYIV2606-026").text
    b = client.get("/kb-payout/receipt?invs=CYIV2606-026,CYIV2606-023").text  # สลับลำดับ
    import re
    no_a = re.search(r"RC(\d{4}-\d{4})", a).group(1)
    no_b = re.search(r"RC(\d{4}-\d{4})", b).group(1)
    assert no_a == no_b                               # ชุดเดิม = เลขเดิม
    # ชุดใหม่ (ใบเดียว) = เลขถัดไป
    c = client.get("/kb-payout/receipt?invs=CYIV2606-023").text
    no_c = re.search(r"RC(\d{4}-\d{4})", c).group(1)
    assert no_c != no_a
    with Session(engine) as s:
        issues = s.exec(select(DocIssue).where(DocIssue.doc_type == "kb_receipt")).all()
        assert [i.no for i in sorted(issues, key=lambda x: x.no)] == [1, 2]


def test_receipt_requires_settled(client):
    r = client.get("/kb-payout/receipt?invs=CYIV2606-999")
    assert r.status_code == 400
    assert "ยังไม่ติ๊กรับ" in r.text


def test_designer_override_and_reset(client):
    r = client.get("/admin/doc-designer?key=kb_receipt")
    assert r.status_code == 200
    # แก้ฟอร์ม: เหลือ element เดียว
    custom = [{"type": "text", "x": 10, "y": 10, "w": 100, "h": 8,
               "size": 20, "bold": True, "align": "left", "text": "ใบเสร็จฉบับแก้เอง {{doc_no}}"}]
    rr = client.post("/admin/doc-designer/save", json={"key": "kb_receipt", "elements": custom})
    assert rr.json()["ok"]
    page = client.get("/kb-payout/receipt?invs=CYIV2606-023,CYIV2606-026").text
    assert "ใบเสร็จฉบับแก้เอง" in page                 # override มีผลกับใบจริง
    # reset กลับมาตรฐาน
    client.post("/admin/doc-designer/save", json={"key": "kb_receipt", "elements": [], "reset": True})
    with Session(engine) as s:
        assert s.exec(select(DocTemplate).where(DocTemplate.key == "kb_receipt")).first() is None
    page2 = client.get("/kb-payout/receipt?invs=CYIV2606-023,CYIV2606-026").text
    assert "ใบเสร็จรับเงิน" in page2 and "ใบเสร็จฉบับแก้เอง" not in page2
