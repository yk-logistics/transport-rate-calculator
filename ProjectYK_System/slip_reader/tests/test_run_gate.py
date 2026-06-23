"""The money gate: when the MVP says the reader is disabled, run_once must NOT
construct the engine or call engine.read — i.e. zero Anthropic spend."""
import slip_reader.run_once as ro


class SpyEngine:
    created = 0
    reads = 0

    def __init__(self):
        SpyEngine.created += 1

    def read(self, data):
        SpyEngine.reads += 1
        raise AssertionError("engine.read must not run when disabled")


def _reset():
    SpyEngine.created = 0
    SpyEngine.reads = 0


def test_disabled_skips_engine_entirely(monkeypatch):
    _reset()
    monkeypatch.setattr(ro.mvp_config, "fetch_config",
                        lambda: {"enabled": False, "since": "", "run_now": False})
    monkeypatch.setattr(ro, "get_engine", lambda name: SpyEngine())
    # If the gate works, get_engine/company_slips are never reached.
    monkeypatch.setattr(ro.slip_source, "company_slips",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not query slips")))
    assert ro.main() == 0
    assert SpyEngine.created == 0 and SpyEngine.reads == 0


def test_config_unreachable_is_treated_as_disabled(monkeypatch):
    _reset()
    monkeypatch.setattr(ro.mvp_config, "fetch_config",
                        lambda: {"enabled": False, "since": "", "run_now": False, "error": "boom"})
    monkeypatch.setattr(ro, "get_engine", lambda name: SpyEngine())
    assert ro.main() == 0
    assert SpyEngine.created == 0


def test_run_now_overrides_disabled(monkeypatch):
    _reset()
    # enabled is false but a "check now" was requested → it must run.
    monkeypatch.setattr(ro.mvp_config, "fetch_config",
                        lambda: {"enabled": False, "since": "", "run_now": True})
    monkeypatch.setattr(ro, "get_engine", lambda name: SpyEngine())
    monkeypatch.setattr(ro.slip_source, "company_slips", lambda *a, **k: [])
    reported = {}
    monkeypatch.setattr(ro.mvp_config, "report",
                        lambda result, ack_run_now=False: reported.update(result=result, ack=ack_run_now))
    assert ro.main() == 0
    assert SpyEngine.created == 1            # engine WAS built (run proceeded)
    assert reported["ack"] is True          # run_now acked so it fires once


def test_mvp_since_overrides_arg(monkeypatch):
    _reset()
    monkeypatch.setattr(ro.mvp_config, "fetch_config",
                        lambda: {"enabled": True, "since": "2026-06-01", "run_now": False})
    monkeypatch.setattr(ro, "get_engine", lambda name: SpyEngine())
    captured = {}

    def fake_slips(db, group, since=None):
        captured["since"] = since
        return []

    monkeypatch.setattr(ro.slip_source, "company_slips", fake_slips)
    monkeypatch.setattr(ro.mvp_config, "report", lambda *a, **k: None)
    ro.main(since="2026-06-22 00:00:00")    # arg should be overridden by config since
    assert captured["since"] == "2026-06-01 00:00:00"
