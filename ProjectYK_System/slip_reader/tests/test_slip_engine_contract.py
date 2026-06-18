import os
from slip_reader.engine import SlipReadout, get_engine, ClaudeSlipEngine


class FakeEngine:
    def read(self, image_bytes):
        return SlipReadout(is_slip=True, amount=428.0, recipient_name="วิโรจน์",
                           memo="วิโรจน์ รับตู้ดรอป", ref_code="REF", slip_time="08:54",
                           direction="out")


def test_readout_shape():
    r = FakeEngine().read(b"")
    assert r.is_slip and r.amount == 428.0 and r.direction in ("out", "in")


def test_get_engine_returns_claude(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "dummy-key-for-construction")
    e = get_engine("claude")
    assert isinstance(e, ClaudeSlipEngine)
