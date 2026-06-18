from __future__ import annotations
import base64
import json
from dataclasses import dataclass
from typing import Protocol, Optional
from . import config


@dataclass
class SlipReadout:
    is_slip: bool
    amount: Optional[float]
    recipient_name: str
    memo: str
    ref_code: str
    slip_time: str
    direction: str


class SlipEngine(Protocol):
    def read(self, image_bytes: bytes) -> SlipReadout: ...


_PROMPT = (
    "You are reading a Thai bank transfer slip image. Return ONLY JSON with keys: "
    "is_slip (true if this is a bank transfer/bill-pay slip, false for job orders, "
    "work plans, or summary tables), amount (number or null), recipient_name "
    "(from 'ไปยัง' or memo, Thai), memo (บันทึกช่วยจำ text), ref_code "
    "(รหัสอ้างอิง), slip_time ('HH:MM' or ''), direction ('out' normally; 'in' if "
    "money is received into petty cash). No prose, JSON only."
)


class ClaudeSlipEngine:
    def __init__(self):
        import anthropic
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self._model = config.CLAUDE_MODEL

    # JSON schema constrains the response — no ```json fences to strip, no
    # free-form parsing. Haiku 4.5 supports structured outputs.
    _SCHEMA = {
        "type": "object",
        "properties": {
            "is_slip": {"type": "boolean"},
            "amount": {"type": ["number", "null"]},
            "recipient_name": {"type": "string"},
            "memo": {"type": "string"},
            "ref_code": {"type": "string"},
            "slip_time": {"type": "string"},
            "direction": {"type": "string", "enum": ["out", "in"]},
        },
        "required": ["is_slip", "amount", "recipient_name", "memo",
                     "ref_code", "slip_time", "direction"],
        "additionalProperties": False,
    }

    def read(self, image_bytes: bytes) -> SlipReadout:
        b64 = base64.standard_b64encode(image_bytes).decode()
        msg = self._client.messages.create(
            model=self._model, max_tokens=400,
            output_config={"format": {"type": "json_schema", "schema": self._SCHEMA}},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64",
                 "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": _PROMPT},
            ]}],
        )
        # A safety refusal returns stop_reason="refusal" with no usable content.
        # Treat as "not a readable slip" — caller will skip (no guessed amount).
        if msg.stop_reason == "refusal":
            return SlipReadout(False, None, "", "", "", "", "out")
        text = next((b.text for b in msg.content if b.type == "text"), "").strip()
        d = json.loads(text)  # output_config guarantees valid JSON, no fences
        return SlipReadout(
            is_slip=bool(d.get("is_slip")),
            amount=(float(d["amount"]) if d.get("amount") not in (None, "") else None),
            recipient_name=d.get("recipient_name", "") or "",
            memo=d.get("memo", "") or "", ref_code=d.get("ref_code", "") or "",
            slip_time=d.get("slip_time", "") or "",
            direction=d.get("direction", "out") or "out",
        )


def get_engine(name: str = None) -> SlipEngine:
    name = name or config.SLIP_ENGINE
    if name == "claude":
        return ClaudeSlipEngine()
    raise ValueError(f"unknown slip engine: {name}")
