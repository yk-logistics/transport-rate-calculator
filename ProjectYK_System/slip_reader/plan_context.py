from __future__ import annotations
import re

_DRIVER = re.compile(r"-\s*นาย([^\d\n]+?)\s+\d{3}-\d{3}-\d{4}")
_AGENT = re.compile(r"Agent\.\s*([A-Z][A-Z0-9 ]+)")
_YARD = re.compile(r"คืนลาน([^\s\[\]]+)")
_JOB = re.compile(r"Job\.\s*([0-9\-]+)")
_HEAD = re.compile(r"หัว\s*([0-9\-]+)")


def parse_plan(plan_text: str) -> dict:
    """Split into job blocks by 'Job.'; attach driver(s) found in each block.

    Returns {first_name: [{job, agent, return_yard, plate_head}]}.
    """
    out: dict[str, list[dict]] = {}
    blocks = re.split(r"(?=Job\.)", plan_text)
    for b in blocks:
        if "Job." not in b:
            continue
        m_job = _JOB.search(b)
        job = m_job.group(1) if m_job else ""
        m_agent = _AGENT.search(b)
        agent = m_agent.group(1).strip() if m_agent else ""
        m_yard = _YARD.search(b)
        yard = m_yard.group(1).strip() if m_yard else ""
        m_head = _HEAD.search(b)
        head = m_head.group(1).strip() if m_head else ""
        for m in _DRIVER.finditer(b):
            full = m.group(1).strip()
            first = full.split()[0] if full.split() else full
            out.setdefault(first, []).append(
                {"job": job, "agent": agent, "return_yard": yard, "plate_head": head})
    return out


def plan_lookup(plans_text_by_time, day: str) -> dict:
    """plans_text_by_time: list[(sent_at_str, text)]. Pick the LATEST whose body
    contains the target day token (e.g. '16.06.26'), parse it. Empty dict if none.
    """
    candidates = [(t, txt) for (t, txt) in plans_text_by_time if day in txt]
    if not candidates:
        return {}
    candidates.sort(key=lambda x: x[0])
    return parse_plan(candidates[-1][1])
