"""สร้าง alarm.wav (stdlib only) — เสียงบี๊บสองโทนสลับ ดังพอปลุก."""
import wave
import struct
import math
import os

SAMPLE_RATE = 44100
AMPLITUDE = 26000  # /32767 — ดังแต่ไม่ clip
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alarm.wav")


def tone(freq, dur):
    n = int(SAMPLE_RATE * dur)
    for i in range(n):
        # square-ish ผ่าน sign(sin) ทำให้แสบหู/ปลุกง่ายกว่า sine ล้วน
        s = math.sin(2 * math.pi * freq * i / SAMPLE_RATE)
        val = AMPLITUDE if s >= 0 else -AMPLITUDE
        yield struct.pack("<h", val)


def silence(dur):
    for _ in range(int(SAMPLE_RATE * dur)):
        yield struct.pack("<h", 0)


def main():
    frames = []
    # บี๊บ-บี๊บ: 880Hz / เงียบ / 1175Hz / เงียบ
    for chunk in (tone(880, 0.35), silence(0.12),
                  tone(1175, 0.35), silence(0.12),
                  tone(880, 0.35), silence(0.20)):
        frames.extend(chunk)
    with wave.open(OUT, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(b"".join(frames))
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
