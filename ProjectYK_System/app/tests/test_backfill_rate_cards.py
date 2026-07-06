# -*- coding: utf-8 -*-
"""D1: backfill RateCard จากแถวเดลี่ที่มีราคาแล้วในประวัติ (แถวที่ import มา
ก่อนฟีเจอร์ auto-learn เกิด — ไม่เคยผ่าน rate_record_from_daily เลย).

dry-run ต้องไม่เขียนอะไร; apply ต้องได้การ์ดที่ทำให้ rate_find เจอเรทสำหรับ
แถวว่างเงื่อนไขเดียวกัน; รันซ้ำต้อง idempotent (ไม่เกิดการ์ดซ้ำ)."""
import os
import tempfile
from datetime import date

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

import pytest
from sqlmodel import SQLModel, Session, select

from db_config import engine
import main as appmod
from models import DailyJob, RateCard

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from backfill_rate_cards import backfill  # noqa: E402


@pytest.fixture()
def db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    appmod.init_db()
    with Session(engine) as s:
        # แถวมีราคา (ประวัติ) + แถวว่างเงื่อนไขเดียวกัน + แถวลา (ต้องถูกข้าม)
        s.add(DailyJob(work_date=date(2026, 5, 2), site_code="BIGC", status_code="DV",
                       destination="สาขาบางนา", revenue_customer=1500.0))
        s.add(DailyJob(work_date=date(2026, 5, 9), site_code="BIGC", status_code="DV",
                       destination="สาขาบางนา", revenue_customer=0.0))
        s.add(DailyJob(work_date=date(2026, 5, 3), site_code="BIGC", status_code="DV",
                       destination="สาขาบางนา", leave_status="ลา", revenue_customer=900.0))
        s.commit()
    yield


def test_dry_run_writes_nothing(db):
    with Session(engine) as s:
        result = backfill(s, dry_run=True)
        assert result["learned_from"] == 1
    with Session(engine) as s:
        assert s.exec(select(RateCard)).all() == []


def test_apply_creates_cards_and_suggestion_found(db):
    with Session(engine) as s:
        result = backfill(s, dry_run=False)
        assert result["learned_from"] == 1
        assert result["new_card_ids"]
    with Session(engine) as s:
        empty = [j for j in s.exec(select(DailyJob)).all()
                 if not (j.revenue_customer or 0)][0]
        card = appmod.rate_find(s, "revenue_customer",
                                appmod._rate_ctx_from_daily(s, empty))
        assert card is not None
        assert card.rate_value == 1500.0   # จากแถวประวัติ ไม่ใช่แถวลา


def test_rerun_is_idempotent(db):
    with Session(engine) as s:
        backfill(s, dry_run=False)
    with Session(engine) as s:
        n1 = len(s.exec(select(RateCard)).all())
        result2 = backfill(s, dry_run=False)
        assert result2["new_card_ids"] == []
    with Session(engine) as s:
        assert len(s.exec(select(RateCard)).all()) == n1
