"""หน้า /deposits — ยอดเงินประกันตนรวม: ดู + แก้ (มี audit) + ประวัติรายคน."""
import os, tempfile
import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["YK_SESSION_SECRET"] = "t"
os.environ["YK_INSECURE_COOKIES"] = "1"

from datetime import date
from sqlmodel import SQLModel, Session, select
from starlette.testclient import TestClient

from db_config import engine
import main as appmod
from models import Employee, PayRun, PayRunItem, AppUser, DepositAudit


def test_deposit_audit_model_exists():
    # ฟิลด์ครบตามสเปก
    a = DepositAudit(employee_id=1, changed_by="yk1",
                     field_name="deposit_balance", old_value="0", new_value="1000",
                     reason="test")
    assert a.employee_id == 1
    assert a.field_name == "deposit_balance"
    assert a.new_value == "1000"
