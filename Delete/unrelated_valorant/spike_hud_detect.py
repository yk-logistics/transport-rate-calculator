"""
Prototype: ตรวจจับ HUD ด้านบนว่ามี "SPIKE PLANTED" หรือไอคอนแดงหรือยัง

- ใช้รูปตัวอย่าง 2 รูปที่คุณให้มา ทดสอบจากไฟล์ภาพก่อน (ยังไม่จับจากเกมจริง)
- หลักการง่ายๆ: ดูแถบด้านบนของหน้าจอแล้วเช็คว่ามีสีแดงเยอะผิดปกติหรือไม่

คำเตือน: ถ้าจะเอาไปใช้กับเกมจริงด้วยการจับภาพหน้าจอแบบ real-time
ควรเช็คกฎ/anti-cheat ของเกมเองก่อน ว่ายอมให้โปรแกรมภายนอก capture ได้แค่ไหน
"""

from pathlib import Path

import cv2
import numpy as np

# ปรับ path ให้ตรงกับไฟล์ภาพตัวอย่างในเครื่องคุณ
BASE = Path(__file__).resolve().parent

IMG_PLANTED = BASE.parent / "assets" / (
    "c__Users_Home_AppData_Roaming_Cursor_User_workspaceStorage_9cb5b93c6bf6765e18a716428876439d_images_"
    "image-ede1172d-eca7-40a2-882f-08464b3c3ca2.png"
)
IMG_NORMAL = BASE.parent / "assets" / (
    "c__Users_Home_AppData_Roaming_Cursor_User_workspaceStorage_9cb5b93c6bf6765e18a716428876439d_images_"
    "image-10db5a97-026b-4657-99ff-a4386f71d571.png"
)


def detect_spike_from_image(path: Path, debug: bool = False) -> bool:
    """
    คืนค่า True ถ้าคิดว่ารูปนี้มี HUD "Spike planted" อยู่ด้านบน (มีสีแดงเด่น)
    """
    img = cv2.imread(str(path))
    if img is None:
        raise FileNotFoundError(path)

    h, w, _ = img.shape

    # เอาเฉพาะแถบบนของจอ (เช่น 15% บนสุด) ที่มีแถบ HUD
    top_bar = img[0 : int(h * 0.18), :]

    # แปลงเป็น HSV แล้วกรองสีแดง
    hsv = cv2.cvtColor(top_bar, cv2.COLOR_BGR2HSV)

    # สีแดงใน HSV จะอยู่ประมาณสองช่วง 0-10 และ 160-180
    lower_red1 = np.array([0, 120, 120])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 120, 120])
    upper_red2 = np.array([180, 255, 255])

    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)

    red_pixels = int(np.count_nonzero(mask))
    total_pixels = mask.size
    red_ratio = red_pixels / float(total_pixels)

    if debug:
        print(f"{path.name}: red_ratio(top_bar) = {red_ratio:.4f}")

    # เกณฑ์แบบหยาบ: ถ้าสีแดงมากกว่า 0.02 ของแถบบน ถือว่ามี HUD spike
    return red_ratio > 0.02


def main() -> None:
    for p in [IMG_NORMAL, IMG_PLANTED]:
        exists = p.exists()
        print(f"Test on: {p.name} (exists={exists})")
        if not exists:
            continue
        has_spike = detect_spike_from_image(p, debug=True)
        print("  -> has_spike_hud? ", has_spike)


if __name__ == "__main__":
    main()

