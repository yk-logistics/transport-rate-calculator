"""
Central alias map for site and person-name normalization.

Goal: keep import/link logic consistent across tools and prevent cross-site mix.
"""
from __future__ import annotations

import re


def _norm_text(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[()\[\]\"'`._\-]", "", s)
    s = re.sub(r"\s+", "", s)
    return s


def normalize_site_code(raw: str) -> str:
    key = _norm_text(raw)
    aliases = {
        "bigc": "BIGC",
        "bigcsite": "BIGC",
        "bigcบางปะอิน": "BIGC",
        "ayu": "AYU",
        "อยุธยา": "AYU",
        "ayuอยุธยา": "AYU",
        "lcb": "LCB",
        "แหลม": "LCB",
        "แหลมฉบัง": "LCB",
    }
    if key in aliases:
        return aliases[key]
    return (raw or "").strip().upper()


def normalize_person_name(raw: str) -> str:
    s = (raw or "").strip()
    for pfx in ("นาย", "นาง", "น.ส.", "น.ส", "พี่"):
        if s.startswith(pfx):
            s = s[len(pfx):].strip()
    return _norm_text(s)


# Global aliases not tied to a single site.
GLOBAL_PERSON_ALIASES: dict[str, str] = {
    normalize_person_name("ณัชพล."): "ณัชพน",
    normalize_person_name("ณัชพล"): "ณัชพน",
    # ชื่อในสดย่อยยาว vs ใน Employee — link_drivers_safe ไม่มี site_code ในบางแถว
    normalize_person_name("สมพร โม่งปราณีต"): "สมพร BIG-C",
    normalize_person_name("สมพร โม่งปรำณีต"): "สมพร BIG-C",  # typo เดียวกับ bigc_bank_seed
}

# Site-specific aliases (to avoid cross-site mixing of same short name).
PERSON_ALIASES_BY_SITE: dict[str, dict[str, str]] = {
    "BIGC": {
        normalize_person_name("สมัย BIG C"): "สมัย",
        normalize_person_name("สมัย BIG-C"): "สมัย",
        normalize_person_name("สมพร โม่งปราณีต"): "สมพร BIG-C",
        # พนักงานถูกบันทึกชื่อไม่มีนามสกุลในระบบ — map เป็นชื่อเต็มเพื่อจับคู่ seed เลขบัญชี / PDF โอนเงิน
        normalize_person_name("บุญชอบ"): "บุญชอบ พูลสวัสดิ์",
    },
    "AYU": {
        normalize_person_name("สมัย อยุธยา"): "สมัย อยุธยา",
        # legacy data sometimes only writes 'สมัย' for AYU rows; canonicalize it
        # so dedup logic can match cross-source rows correctly.
        normalize_person_name("สมัย"): "สมัย อยุธยา",
        # short nicknames used in book2 that don't match full_name lookup
        normalize_person_name("เอ๊ะ"): "บรรเจิด คุ้มพงษ์ (เอ๊ะ)",
        normalize_person_name("ช่างน้อย"): "วิชัย ชื่นชม (ช่างน้อย)",
        normalize_person_name("ข้าวฟ่าง"): "พิชญา บุญชู (ข้าวฟ่าง)",
    },
}


# Site-hint token table — ordered BigC → AYU → LCB (site priority per playbook).
# Each entry: (tuple-of-substrings-to-check, canonical_site_code)
_SITE_HINT_TOKENS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("big c", "big-c", "bigc", "บิ๊กซี"), "BIGC"),
    (("อยุธยา", "ayu"),                     "AYU"),
    (("แหลม", "lcb", "แหลมฉบัง"),           "LCB"),
)


def site_from_requester(raw: str) -> str:
    """Detect canonical site_code from a requester name that carries a site suffix.

    Examples (old_value → canonical):
      'สมัย BIG C'   → 'BIGC'
      'สมพร BIG-C'   → 'BIGC'
      'สมัย อยุธยา'  → 'AYU'
      'สมพร แหลม'   → 'LCB'
      'พ่อ'           → ''  (no hint — do not guess)

    Returns '' when no recognisable site suffix is found.
    """
    if not raw:
        return ""
    low = raw.lower()
    for tokens, site in _SITE_HINT_TOKENS:
        if any(t in low for t in tokens):
            return site
    return ""


def canonical_person_name(raw: str, site_code: str = "") -> str:
    site = normalize_site_code(site_code)
    key = normalize_person_name(raw)
    if site and site in PERSON_ALIASES_BY_SITE and key in PERSON_ALIASES_BY_SITE[site]:
        return PERSON_ALIASES_BY_SITE[site][key]
    if key in GLOBAL_PERSON_ALIASES:
        return GLOBAL_PERSON_ALIASES[key]
    return (raw or "").strip()

