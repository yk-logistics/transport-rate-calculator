# -*- coding: utf-8 -*-
"""
Valorant Spike Timer Overlay
ได้ยินเสียงปลูก Spike → กด 5 เริ่มนับ | กู้ครึ่งแล้ว → กด 6
เตือนสองระดับ: เตรียมตัว (12 วิ/8 วิ) → ถึงเวลา (9 วิ/5 วิ)

เวอร์ชันทดลอง: มีตัวดู HUD ด้านบนแบบ resource ต่ำ
- จับภาพเฉพาะบริเวณเล็กๆ กลางด้านบน
- ตรวจทุก 500 ms ว่ามีสีแดงของ Spike HUD หรือไม่
"""
import sys
import platform
import time
from threading import Thread, Event
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

if platform.system() == "Windows":
    try:
        import winsound
        HAS_BEEP = True
    except ImportError:
        HAS_BEEP = False
    try:
        import mss
        import numpy as np
        import cv2
        HAS_MSS = True
    except ImportError:
        HAS_MSS = False
else:
    HAS_BEEP = False
    HAS_MSS = False


SPIKE_SECONDS = 45
DEFUSE_FULL = 7.5   # วินาทีที่ต้องกู้เต็ม
DEFUSE_HALF = 3.75  # วินาทีที่ต้องกู้ถ้าทำครึ่งแล้ว
# เตือนสองระดับ: เตรียมตัว (ก่อนถึง) → ถึงเวลา (deadline)
BEEP_PREPARE_FULL = 12  # เหลือ 12 วิ = เตือนเตรียมตัวไปกู้ (กู้เต็มใช้ 7.5 วิ)
BEEP_AT_FULL = 9        # เหลือ 9 วิ = ถึงเวลา ต้องกู้แล้ว (เผื่อที่คุณกดปุ่มเริ่มช้าประมาณ ~1 วิ)
BEEP_PREPARE_HALF = 8   # เหลือ 8 วิ = เตือนเตรียมตัวกู้ครึ่ง (ใช้ 3.75 วิ)
BEEP_AT_HALF = 5        # เหลือ 5 วิ = ถึงเวลากู้ครึ่ง
# ปุ่ม: เลข 5 กับ 6 แถวบน | F10 = ปิด | F11 = ซ่อน/แสดง overlay (ไม่ให้คลิกโดนแล้วเด้งออกเกม)
VK_5 = 0x35   # Main keyboard 5
VK_6 = 0x36   # Main keyboard 6
VK_F10 = 0x79 # F10 = ออกจาก overlay
VK_F11 = 0x7A # F11 = ซ่อน/แสดง

# ตัวเลือก auto-detect จาก HUD (ทดลอง)
AUTO_DETECT_SPIKE = False  # ถ้าอยากปิดให้เปลี่ยนเป็น False
CAPTURE_INTERVAL_MS = 500  # จับภาพทุก 500 ms


def play_beep(warning_type):
    """warning_type: prepare = เตือนเตรียมตัว (เสียงสั้น), full/half = ถึงเวลา (เสียงชัด)"""
    if not HAS_BEEP:
        return
    try:
        if warning_type == "prepare":
            winsound.Beep(600, 80)
        elif warning_type == "full":
            winsound.Beep(900, 180)
        else:
            winsound.Beep(1200, 120)
    except Exception:
        pass


def detect_spike_in_frame(frame: "np.ndarray") -> bool:
    """
    ตรวจว่าบริเวณด้านบนตรงกลางของ frame มีสีแดงเยอะพอที่จะคิดว่าเป็น Spike HUD หรือไม่
    frame: รูปแบบ BGRA/BGR จาก mss (numpy array)
    """
    if not HAS_MSS:
        return False
    h, w = frame.shape[:2]
    if h == 0 or w == 0:
        return False

    # เอาเฉพาะแถบบน 18% ตรงกลางจอ (กว้าง ~30% ของจอ)
    top_h = int(h * 0.18)
    cx = w // 2
    half_w = int(w * 0.15)
    left = max(0, cx - half_w)
    right = min(w, cx + half_w)
    roi = frame[0:top_h, left:right]

    # mss.grab คืน BGRA
    if roi.shape[2] == 4:
        bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)
    else:
        bgr = roi
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    # ช่วงสีแดงใน HSV
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

    # ใช้ threshold แบบหยาบ (บริเวณเล็ก + ตรวจแค่ HUD กลางบน)
    return red_ratio > 0.03


def run_spike_watcher(start_callback, stop_event: Event) -> None:
    """
    เธรดเบาๆ ตรวจ HUD กลางบนทุก CAPTURE_INTERVAL_MS
    ถ้าเจอ spike HUD จากไม่มี → มี ครั้งแรก จะเรียก start_callback() (เช่น เริ่มนับเวลา)
    """
    if not (AUTO_DETECT_SPIKE and HAS_MSS):
        return
    try:
        with mss.mss() as sct:
            mon = sct.monitors[1]  # primary monitor
            width = mon["width"]
            height = mon["height"]
            cx = mon["left"] + width // 2
            top = mon["top"]
            cap_height = int(height * 0.18)
            cap_half_width = int(width * 0.15)

            region = {
                "top": top,
                "left": cx - cap_half_width,
                "width": cap_half_width * 2,
                "height": cap_height,
            }

            last_has_spike = False
            interval = CAPTURE_INTERVAL_MS / 1000.0

            while not stop_event.is_set():
                img = np.array(sct.grab(region))
                has_spike = detect_spike_in_frame(img)
                # trigger เฉพาะตอนเปลี่ยนจาก False -> True
                if has_spike and not last_has_spike:
                    start_callback()
                last_has_spike = has_spike
                stop_event.wait(interval)
    except Exception:
        # ถ้ามีปัญหาเรื่อง capture ให้เงียบไป ไม่ให้ล้มทั้งโปรแกรมหลัก
        return


class SpikeOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.remaining = 0
        self.half_defuse_mode = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.beeped_prepare_full = False
        self.beeped_full = False
        self.beeped_prepare_half = False
        self.beeped_half = False
        self.setup_ui()

    def setup_ui(self):
        flags = (
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        try:
            flags |= Qt.WindowTransparentForInput  # คลิก/คีย์ทะลุไปเกม (คลิกโดนแล้วไม่มีผล)
        except AttributeError:
            pass
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.NoFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.label_main = QLabel("5=ปลูก" if HAS_PYNPUT else "Click to test", self)
        self.label_main.setAlignment(Qt.AlignCenter)
        self.label_main.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self.label_main.setMinimumHeight(24)
        self.label_main.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.label_main.setFocusPolicy(Qt.NoFocus)
        self.label_sub = QLabel("6=กู้ครึ่ง  F10=ปิด  F11=ซ่อน", self)
        self.label_sub.setAlignment(Qt.AlignCenter)
        self.label_sub.setFont(QFont("Segoe UI", 9))
        self.label_sub.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.label_sub.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.label_main)
        layout.addWidget(self.label_sub)

        self.apply_style("idle")
        self.setFixedSize(145, 58)

    def apply_style(self, state):
        base = (
            "background-color: rgba(0, 0, 0, 200); "
            "border-radius: 6px; "
            "padding: 2px 6px; "
        )
        if state == "idle":
            style = "color: #00ff88; border: 1px solid #00ff88;"
        elif state == "warn":
            style = "color: #ffaa00; border: 1px solid #ffaa00;"
        else:
            style = "color: #ff4444; border: 1px solid #ff4444;"
        self.label_main.setStyleSheet(base + style)
        self.label_sub.setStyleSheet(base + style)

    def start_countdown(self):
        self.remaining = SPIKE_SECONDS
        self.half_defuse_mode = False
        self.beeped_prepare_full = False
        self.beeped_full = False
        self.beeped_prepare_half = False
        self.beeped_half = False
        self.timer.start(1000)
        self.update_text()

    def set_half_defuse(self):
        if self.timer.isActive():
            self.half_defuse_mode = True
            self.beeped_prepare_half = False
            self.beeped_half = False
            self.update_text()

    def tick(self):
        self.remaining -= 1

        if not self.half_defuse_mode:
            if self.remaining <= BEEP_PREPARE_FULL and not self.beeped_prepare_full:
                self.beeped_prepare_full = True
                play_beep("prepare")
            if self.remaining <= BEEP_AT_FULL and not self.beeped_full:
                self.beeped_full = True
                play_beep("full")
        else:
            if self.remaining <= BEEP_PREPARE_HALF and not self.beeped_prepare_half:
                self.beeped_prepare_half = True
                play_beep("prepare")
            if self.remaining <= BEEP_AT_HALF and not self.beeped_half:
                self.beeped_half = True
                play_beep("half")

        self.update_text()
        if self.remaining <= 0:
            self.timer.stop()
            self.label_main.setText("BOOM!")
            self.label_sub.setText("")
            self.apply_style("boom")
            QTimer.singleShot(2000, self.reset_display)

    def update_text(self):
        self.label_main.setText(str(self.remaining))
        if self.half_defuse_mode:
            self.label_sub.setText("กู้ครึ่ง 3.75 วิ")
        else:
            self.label_sub.setText("กู้เต็ม 7.5 วิ")
        if not self.half_defuse_mode:
            use_warn = self.remaining <= BEEP_PREPARE_FULL
        else:
            use_warn = self.remaining <= BEEP_PREPARE_HALF
        if use_warn:
            self.apply_style("warn")
        else:
            self.apply_style("idle")

    def reset_display(self):
        self.label_main.setText("5=ปลูก" if HAS_PYNPUT else "Click")
        self.label_sub.setText("6=กู้ครึ่ง  F10=ปิด  F11=ซ่อน")
        self.apply_style("idle")

    def showEvent(self, event):
        super().showEvent(event)
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 16, 16)

    def toggle_hide(self):
        """กด F11 สลับซ่อน/แสดง overlay เพื่อไม่ให้เมาส์คลิกโดนแล้วเกมเด้ง"""
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def mousePressEvent(self, event):
        if not HAS_PYNPUT:
            self.start_countdown()
        super().mousePressEvent(event)


def main():
    app = QApplication(sys.argv)
    overlay = SpikeOverlay()
    overlay.show()

    def on_start():
        QTimer.singleShot(0, overlay.start_countdown)

    def on_half():
        QTimer.singleShot(0, overlay.set_half_defuse)

    def on_quit():
        QTimer.singleShot(0, app.quit)

    def on_toggle_hide():
        QTimer.singleShot(0, overlay.toggle_hide)

    # สำหรับ stop watcher thread ตอนปิดโปรแกรม
    stop_event = Event()

    # callback สำหรับ watcher: เรียก start_countdown บน main thread
    def watcher_start():
        QTimer.singleShot(0, overlay.start_countdown)

    if HAS_PYNPUT:
        def on_press(key):
            try:
                if hasattr(key, "vk"):
                    if key.vk == VK_5:
                        on_start()
                    elif key.vk == VK_6:
                        on_half()
                    elif key.vk == VK_F10:
                        on_quit()
                    elif key.vk == VK_F11:
                        on_toggle_hide()
            except Exception:
                pass

        def run_listener():
            with keyboard.Listener(on_press=on_press) as listener:
                listener.join()
        Thread(target=run_listener, daemon=True).start()
        print("5=ปลูก 6=กู้ครึ่ง | F10=ปิด | F11=ซ่อน/แสดง overlay (กดซ่อนเวลาเล่นจะได้ไม่คลิกโดน)")
    else:
        print("Install pynput for hotkeys. Or click overlay to test.")

    # เริ่มเธรดตรวจ HUD ถ้าเปิด AUTO_DETECT_SPIKE ไว้
    Thread(target=run_spike_watcher, args=(watcher_start, stop_event), daemon=True).start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
