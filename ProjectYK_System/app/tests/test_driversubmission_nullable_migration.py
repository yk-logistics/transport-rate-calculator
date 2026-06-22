"""Regression: a pre-existing app.db has driversubmission.employee_id NOT NULL
(created before the magic-link feature). create_all does not relax it, so a
login-less weekly check (employee_id=None) would 500 with an IntegrityError.

The fresh-schema conftest can't catch this — it builds the table already nullable.
Here we deliberately recreate the LEGACY table, run _drop_not_null, and assert a
NULL insert now succeeds.
"""
from db_config import engine
import main as appmod
import pytest


@pytest.mark.skipif(engine.dialect.name != "sqlite",
                    reason="SQLite-only table rebuild")
def test_drop_not_null_relaxes_legacy_employee_id(client, monkeypatch):
    # _drop_not_null short-circuits on `if not IS_SQLITE`. Under tests conftest
    # sets an explicit DATABASE_URL, which makes db_config.IS_SQLITE False even
    # though the engine IS sqlite. Force the guard true so we exercise the rebuild.
    monkeypatch.setattr(appmod, "IS_SQLITE", True)
    with engine.begin() as conn:
        # Simulate the legacy schema: drop the (nullable) table the fixture made,
        # recreate driversubmission with employee_id INTEGER NOT NULL.
        conn.exec_driver_sql("DROP TABLE IF EXISTS driversubmission")
        conn.exec_driver_sql(
            "CREATE TABLE driversubmission ("
            " id INTEGER PRIMARY KEY,"
            " employee_id INTEGER NOT NULL,"
            " submitted_at DATETIME, kind VARCHAR, vehicle_id INTEGER,"
            " plate_raw VARCHAR, daily_job_id INTEGER,"
            " gps_lat FLOAT, gps_lng FLOAT, gps_accuracy_m FLOAT,"
            " photo_paths VARCHAR, data_json VARCHAR,"
            " review_status VARCHAR, review_note VARCHAR,"
            " reviewed_by VARCHAR, reviewed_at DATETIME, device_info VARCHAR)"
        )
        # sanity: legacy column is NOT NULL
        info = conn.exec_driver_sql("PRAGMA table_info(driversubmission)").fetchall()
        emp = next(r for r in info if r[1] == "employee_id")
        assert emp[3] == 1  # notnull

    # Run the migration under test.
    appmod._drop_not_null("driversubmission", "employee_id")

    with engine.begin() as conn:
        info = conn.exec_driver_sql("PRAGMA table_info(driversubmission)").fetchall()
        emp = next(r for r in info if r[1] == "employee_id")
        assert emp[3] == 0  # now nullable

    # a NULL-employee insert via the ORM must now succeed (this is what 500'd before).
    from models import DriverSubmission
    from sqlmodel import Session, select
    with Session(engine) as s:
        s.add(DriverSubmission(employee_id=None, kind="vehicle_check",
                               review_status="pending"))
        s.commit()
        rows = s.exec(select(DriverSubmission).where(
            DriverSubmission.employee_id == None)).all()  # noqa: E711
        assert len(rows) == 1
