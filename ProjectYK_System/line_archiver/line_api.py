"""LINE Messaging API: ตรวจ webhook signature + ดึง content/ชื่อกลุ่ม/โปรไฟล์"""
import base64
import hashlib
import hmac

import httpx

API = "https://api.line.me/v2/bot"
API_DATA = "https://api-data.line.me/v2/bot"


def verify_signature(channel_secret: str, body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    mac = hmac.new(channel_secret.encode(), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature)


class LineClient:
    def __init__(self, access_token: str):
        self._headers = {"Authorization": f"Bearer {access_token}"}

    def get_content(self, message_id: str) -> tuple[bytes, str]:
        """ดาวน์โหลดไฟล์จริงของ message (รูป/วิดีโอ/เสียง/ไฟล์) — ต้องรีบทำก่อนหมดอายุ"""
        r = httpx.get(f"{API_DATA}/message/{message_id}/content",
                      headers=self._headers, timeout=60)
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "")

    def get_group_summary(self, group_id: str) -> dict:
        r = httpx.get(f"{API}/group/{group_id}/summary", headers=self._headers, timeout=30)
        r.raise_for_status()
        return r.json()  # {"groupId":..., "groupName":..., "pictureUrl":...}

    def get_member_profile(self, group_id: str, user_id: str) -> dict:
        r = httpx.get(f"{API}/group/{group_id}/member/{user_id}",
                      headers=self._headers, timeout=30)
        r.raise_for_status()
        return r.json()  # {"displayName":..., "userId":...}
