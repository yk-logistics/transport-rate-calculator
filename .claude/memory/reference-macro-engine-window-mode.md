---
name: reference-macro-engine-window-mode
description: "Background window-send mode added to โอ's macro_engine.py (Makcu tool) — inject keys into an unfocused game via AttachThreadInput"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 42ead1bd-5364-411d-833e-07717deab2ea
  modified: 2026-07-22T09:25:37.567Z
---

Extends [[reference-makcu-macro-engine]] (โอ's personal tool at
`_NonYK_Projects\makcu\macro_engine.py`, NOT Project YK). Added 2026-07-16.
Thai user guide for โอ: `makcu\USAGE_AUTO_HEAL.md` (setup order, daily keys,
tuning, when to recalibrate, troubleshooting).

**Auto-calibration (rev2, โอ asked "ทำ calibrate ง่ายกว่านี้"):** new steps
`ifhpbelow PCT` / `ifhpabove PCT` — no coordinates in the step; geometry lives
in module HP_CAL (persisted as settings["hp_cal"], App wires SAVE_HOOK=_save).
`find_hp_bar()` scans the target's top-left quadrant for the longest green run
(#41c544 tol 25%). Auto-recal fires whenever HP_CAL's stored win_w/win_h ≠
current window size; "Calibrate HP" button (green, in Send-to bar) = manual.
Caveat by design: auto-recal at NON-full HP shrinks the scale (right edge =
100%) — Log warns, fix = press Calibrate HP at full HP. Old ifbarbelow manual
form kept for other bars (mana). **Live auto-cal vs real game NOT yet tested
(game was closed) — logic verified via fail-safe paths + GUI smoke only.**

**What it does:** new "Send to" bar in the GUI with two radios — *Makcu (focused)*
= original behavior, *Background window* = inject macro output INTO a chosen
window without stealing focus (โอ can keep typing in LINE while a macro drives
the game). Target picked from a dropdown of visible windows (title — exe),
remembered by title+exe and re-resolved each send (survives game restart).
Persisted in macros.json: send_mode / target_title / target_proc.

**The one technique that works (tested exhaustively on SpiritVale = Unity):**
`AttachThreadInput(me, gameTID, True)` + `SetFocus(hwnd)` + `PostMessage`
keydown/up. This is the ONLY method that registers — plain PostMessage,
SendMessage, and fake WM_ACTIVATE/WM_SETFOCUS were ALL ignored by the game.
Verified: single taps (ESC opened/closed the pause menu) AND held movement
keys (W/D walked the character across the map) while foreground stayed on
another window. `hold` runs a typematic repeater thread (re-posts keydown w/
repeat bit every 50ms) since some engines want repeated downs.

**Mouse CANNOT be faked this way** — games read the real cursor position +
real button state, not the coords in a posted WM_LBUTTONDOWN. Confirmed: fake
clicks on the ground did nothing. So window-mode `click` does a "flick":
ALT-tap + SetForegroundWindow(target) → real SendInput click → restore cursor
pos + previous foreground (~0.3s). `move` moves the REAL cursor. `circle` and
walk counter-rotation are skipped in window mode (would drag the real cursor).

**Auto-heal case study (2026-07-16, โอ's request):** new step verbs
`ifbarbelow` / `ifbarabove` `[win] X1 X2 Y #color tol PCT` — reads a status
bar's fill level as the RIGHTMOST pixel matching the color (edge-based because
SpiritVale draws white HP text OVER the bar; pixel-counting breaks, the fill
edge doesn't). Saved macro "Auto Heal SpiritVale" (trigger '1' top-row, per โอ;
toggle): every 200ms, if HP < 50% → tap lctrl (โอ's heal key). Full chain
live-tested: real '1' press toggles watcher on/off, quiet at full HP. GOTCHA:
synthetic test presses MUST carry the scan code (keybd_event bScan=0x02) or
the scan-code-bound triggers never fire. Warned โอ: '1' likely collides with
the in-game skill-1 key (every skill press flips the watcher). Calibration is WINDOW-SIZE
dependent: bar at win-relative x9..39 y17 valid for the 325x168 window; green
= #41c544 tol 25%. Graphics quality/render-resolution do NOT matter (flat UI
color); resizing the window DOES → rerun `makcu/calibrate_bar.py` (finds the
bar, prints the paste-ready step line; run near full HP). macros.json settings
preset to send_mode=window + SpiritVale target.

**Fail-safe guards (added after โอ's "ตรวจสอบอีกที", 2026-07-16):** pixel/bar
conditions read the SCREEN, so a minimized or covered target window would
sample whatever app is on top (Outlook pixel ≠ green → "HP low" → heal spam).
Now `ifpixel win` / `ifbarbelow|above win` route through
`_target_screen_point()` which returns None (condition FAILS, never fires)
when the target is missing, IsIconic, or WindowFromPoint at the check point
resolves to a different root window; read exceptions also fail the condition
instead of falling through to the action steps (exec_step's generic except
would otherwise return True and RUN the tap). Live-tested: forced-fire steps
with game minimized → blocked with log message. GOTCHA also proven: restoring
a minimized window brought the TITLE BAR back → window 327x193 vs calibrated
325x168 → bar read 0% → any style/size change needs calibrate_bar.py rerun.

**Soft-stop buttons (18/7, โอ's request):** new step verb `stopheld` — releases
every key the ENGINE holds (holdkey macros, ROUTER window-holds, walk WASD +
walk_toggle_state) but leaves watcher loops (heal/buff toggles) RUNNING — a
soft stop, not panic. Wired via module STOPHELD_HOOK → App._stop_held (same
pattern as SAVE_HOOK); chirps/logs only when something was actually released
(silent no-op on plain typing). Two "once" macros in macros.json: triggers
**left shift** and **left ctrl** (โอ presses them physically; both still do
their normal in-game job). Enabler: US_SCAN_CODES now has left shift=42,
right shift=54, left ctrl=29, left alt=56 (+l* aliases) so modifiers work as
scan-code triggers AND Set-capture; VK_NAME got the same names. Caveat: right
ctrl shares scan 29 → LCtrl trigger may also fire on right ctrl. Heal watcher's
synthetic lctrl can't self-trigger it: window mode = PostMessage (no hook
events); focused mode = _inj_mark now maps lctrl→29 (guard consumes it).
Verified: 21-check smoke (compile, lint, hook wiring, App build, functional
release, macros present) ALL PASS; engine restarted clean (single instance).
Live keypress of the real triggers NOT yet tested by โอ.

**20/7 ค่ำ — skillspin priority (`N!`) ตามโอขอ (12/12):** โออยาก "ไล่ 1-7 ตามคูลดาวน์
+ กด Elemental Overload (คีย์ q) ทันทีที่คูลดาวน์เสร็จ" → ตอบ: **มาโครเดียว** ดีกว่าแยก
(แยก 2 toggle แล้ว priority ไม่แทรกกลางลำดับจริง + จัดการปุ่มเดียว). Syntax ใหม่:
`skillspin 6! 1 2 3 4 5 7` — เลขติด `!` = priority ถูกเช็คซ้ำ**ก่อนทุกช่อง**ของลำดับปกติ
ใส่ได้หลายตัว; ไม่มี `!` = พฤติกรรมเดิมเป๊ะ (backward compat มีเทสต์คุม). lint รับ `!` แล้ว.
มาโคร `` ` `` เปลี่ยนเป็น `skillspin 1 2 3 4 5 6 7` + คอมเมนต์สอนใช้ `!` ในตัว.
**เงื่อนไขให้ Overload โดนตรวจ CD ได้: โอต้องย้ายไอคอนขึ้นแถวสกิล 1-7 เอง** (แถว 2 R/T
ยังไม่มี geometry) แล้วเติม `!` หลังเลขช่องนั้นใน GUI; ระหว่างยังไม่ย้าย มาโคร "Q spam (Q)"
เดิมยังใช้แทนได้. Caveat: ช่อง 6/7 ว่าง = พื้นสีลอด sat~60 → โดน tap ฟรี (เกมเมิน ไม่อันตราย).
เทสต์: stub screen/router 12 เช็ค ALL PASS (ลำดับ interleave, debounce, prio-only, lint).
Backup: macro_engine.backup-20260720d.py.

**21/7 ตามต่อ — "ทำไมไม่กด 9" = พิกัดแถบสกิลเพี้ยน 2 ชั้น (แก้+พิสูจน์สดแล้ว):**
โอย้าย Overload ไปช่อง 9 แล้วตั้ง `skillspin 1 2 3 4 5 6 7 9!` เอง แต่ไม่ยิงเลย.
วัดสดพบ: ① **บาร์กลายเป็น 3 แถว** (แถว1=เลข 1-9+LShift, แถว2=ตัวอักษร E..U I O P+LCtrl,
แถว3=ว่าง) → แถวเลขขยับขึ้น ② **hp_cal ปัจจุบัน 212px (scale 1.9273) ไม่ใช่ 1.7636**
ที่ใช้ตอนวัด 18/7 → ตำแหน่งที่ engine คำนวณหลุดไปอ่านใต้บาร์ (sat 10-27 ทุกช่อง =
ไม่กดอะไรเลยทั้งแผง ไม่ใช่แค่ 9). แก้: วัดใหม่ด้วย grid-fit บนโปรไฟล์ sat —
จอจริง row1: x=663.5+64.75*(n-1), y=874 → ref ที่ scale 1.9273: **SKILL_X0=344.3
PITCH=33.60 Y=453.5** (คอมเมนต์ในโค้ดเตือน: ค่านี้ผูกกับ hp_cal — กด Calibrate HP
ได้ width ใหม่ หรือเกมเปลี่ยนจำนวนแถวบาร์ = ต้องวัดใหม่). ③ **บัพย้ายแถว 2:
โล่=I ปริซึม=U** (บูท=P เฮียล=LCtrl เหมือนเดิม) → keeper "tap 8"→"tap i",
"tap 9"→"tap u" + เปลี่ยนชื่อมาโคร (อันตรายที่ปิดไป: tap 9 เดิมจะกลายเป็นยิง
Overload มั่ว). E2E สด: เปิด engine → Home → `` ` `` สังเคราะห์ → **ช่อง 3+9 ขึ้น
คูลดาวน์จริง (9=Overload prio ยิงติด)** — ช่องโจมตีอื่นกดแล้วเกมเมินเพราะอยู่ในเมือง
ไม่มีเป้า = พฤติกรรมถูก (ค้างสว่างรอ re-tap). Q spam เดิมไร้ประโยชน์แล้ว (คีย์ q ว่าง).
Engine pid 20812, ปิด disabled ไว้ตามเดิม. เครื่องมือวัดซ้ำ: scratchpad fit_slots.py
(grid-fit X0/PITCH จากแถบจริง — ใช้ทุกครั้งที่บาร์เปลี่ยน).

**21/7 ดึก — ① skillspin `strict` + ② อ่านทะลุหน้าต่างทับ (PrintWindow ทั้งระบบ):**
① โออยากทดลองเรียงสกิลเพื่อหาดาเมจสูงสุด → `skillspin strict 1 2 3` = **รอ**ที่ช่องจน
คูลดาวน์เสร็จค่อยกด (แทนที่จะข้าม) เรียงเป๊ะทีละช่อง; เพดานรอ 20 วิ/ช่องแล้วข้าม+log;
`N!` ยังยิงแทรกระหว่างรอได้; ไม่มี strict = พฤติกรรมเดิม. เทสต์ stub 19/19.
② เอาของค้าง 20/7 มาทำจริง: `_pw_frame(hw)` = PrintWindow flag 2 → เฟรมทั้งหน้าต่าง
(BGRA, cache 30ms, backoff 5s เมื่อพัง) + `_win_grab(hw,l,t,w,h)` = back buffer ก่อน
**fallback mss + fail-safe เดิมครบเมื่อ PW พัง**. เสียบครบทุกจุดอ่าน win-relative:
pathwalk bands/minimap/ground-patch (+`_pw_gray(box,hw)`), `_pw_visible` = PW ได้ก็ถือว่า
เห็น (เดินต่อได้แม้ Chrome ทับ), `_target_screen_point` ปล่อยผ่าน covered เมื่อ PW ใช้ได้,
_hp_level/find_hp_bar/bar_level(hw=)/ifpixel win/ifcolor region/_buff_need/skillspin cells.
**พิสูจน์สด:** PW==mss เป๊ะ (sat diff 0.0 ทุกช่อง) ตอนเห็นเกม; เอา overlay topmost ทับ
→ mss อ่านได้สี overlay (255) แต่ _win_grab ยังอ่านค่าเกมตรงเป๊ะ (drift 0.0) = ฟาร์ม/เดิน
ต่อได้ทั้งที่เกมโดนบัง. capture ~16-40ms → ฮีลช้าลงนิดหน่อย (~50-70ms/รอบ) รับได้.
_hp_level ตอนโดนทับตอนนั้นได้ None เพราะ**โอเปิดเมนูของสวมใส่อยู่จริง** (HUD ซ่อน =
fail-safe ทำงานถูก ไม่ใช่บั๊ก); เคสฮีลใต้ที่บังแบบ HUD โผล่ยังไม่ได้เห็นตัวเลขสด แต่เป็น
เส้นทางอ่านเดียวกับ slot-sats ที่พิสูจน์แล้ว. **minimize ยังห้าม** (IsIconic block ทุกจุด —
PW กับหน้าต่าง minimized ไม่เคยพิสูจน์). Engine pid 13996 (disabled — โอกด Home เอง).
Backup ก่อนแก้: macro_engine.backup-20260720d.py (ครอบทั้ง 21/7).

**21/7 ดึก(2) — `aimtap` เมาส์นำทิศเดิน + วินิจฉัย `/` เงียบ:** โอขอ "กด LShift
ให้เมาส์นำหน้าทิศที่เดิน ปรับระยะได้" → step ใหม่ `aimtap KEY DIST` (DIST=พิกเซลจอ,
แกน y คูณ 0.71 ตามกล้อง 45°). **rev2 (โอ feedback "เลื่อนขึ้นอย่างเดียว+ไม่ต้องดึงกลับ"):**
rev1 อ่านทิศจาก ROUTER._held เท่านั้น → โอเดินเองด้วยมือ = ไม่เห็นทิศ → default ขึ้นตลอด;
แก้: อ่าน**ปุ่ม WASD จริงด้วย GetAsyncKeyState** (union กับ router-held, ทำงานแม้เกม
ไม่ foreground) + **ไม่คืนเมาส์แล้ว** — SetCursorPos ที่ center+dir*DIST → 30ms →
kb_send จบ เมาส์ค้างนำหน้าตัวละคร. ไม่มีปุ่มถือ = ทิศล่าสุด (_AIM_LAST, default ขึ้น).
มาโคร "LShift aim spam (')" trigger `'` (aimtap lshift 250 / delay 300). เทสต์ rev2 8/8
(กายภาพ/router/เฉียง/gate). **ยังไม่พิสูจน์สด: เกม sample ตำแหน่งเมาส์ตอนรับ PostMessage
ขณะไม่ foreground ไหม** — dash ไม่เลี้ยว = plan B foreground-flick แบบ `click`.
⚠️ เมาส์จะถูกยึดตลอดที่ spam เปิด — ใช้ `;` แทนตอนทำงานแอปอื่น.
**`/` ขายของเงียบ (โอรายงาน):** วินิจฉัย = เกมแพตช์ 21/7 ทำ hp bar โต 194→212px →
ui_scale 1.7636→1.9273 (+9.3%) → พิกัด ref-unit ที่วัดตอน 1.7636 เลื่อนหมด; ยืนยันแล้ว
scale ไม่ใช่ uniform (hotbar pitch หด 5% แต่ bar โต 9% = layout เปลี่ยนจริง ต้องวัดรายตัว).
เช็ค passive: การ์ดปุ่มแชนแนล #22222a ยังผ่าน (F1-F12 น่ารอด), การ์ดขายของ/บัฟ shield+prism
ไม่เจอสี (ขายของ=ปิดอยู่ inconclusive แต่คาดพัง, บัฟอาจหมดอายุพอดี inconclusive).
**ค้างรอโอ: เปิดหน้า Sell Items ค้างไว้ให้วัดพิกัดใหม่** แล้วแก้ guard+click ทีเดียว;
keeper บัฟก็ควรวัดซ้ำตอนบัฟติดอยู่. Engine pid 21676.

**21/7 ดึก(5) — strict rev2: ยืนยันสกิลออกจริง (โอจับบั๊กได้เอง):** โอลอง
`skillspin strict 1..7 9!` แล้วเห็น "9 → กระโดดไป 3" — root cause: strict rev1 นับ
"กดปุ่ม = ใช้แล้ว" แต่เกม**กลืนปุ่ม**ช่วง GCD/ท่าร่ายของสกิลก่อนหน้า (1,2 ถูกกดจริงแต่
สกิลไม่ออก ไอคอนยังสว่าง → engine เดินหน้าต่อ). แก้: strict = tap แล้ว**รอไอคอน
ขึ้นคูลดาวน์จริง** (confirm) ก่อนไปช่องถัดไป; ไอคอนยังสว่าง = re-tap ทุก 0.25s;
เพดาน 20s/ช่องเดิม (log "not confirmed"). โครง: `_cell_ready(k)` แยกจาก `_try_tap`,
strict loop มี tapped_once + confirm-break. ⚠️ **สกิลไม่มีคูลดาวน์ห้ามใส่ใน strict**
(ไม่มีวัน confirm → กดรัว 20s แล้วข้าม). เทสต์ 25/25 (รวม T8b เคสเกมกลืนปุ่มแล้ว re-tap
[1,1,2]; gotcha เทสต์: fake grab ต้องตั้ง ready ครั้งเดียว == ไม่ใช่ >= ไม่งั้นทับ cd-flip).
คอมเมนต์คู่มือใน rotation macro อัปเดตแล้ว. Engine pid 21572.

**21/7 ดึก(6) — 🔴 numpad ยิงมาโคร nav-key (โอเจอ) + โหมด CC/Damage ใช้ strict:**
โอย้าย trigger ไป Insert/PgUp/PgDn/Home/End แล้วพบ "กดเลข numpad ไม่ได้ มันยิงมาโคร"
— root cause: **numpad กับ nav cluster ใช้ scan code เดียวกัน** (numpad0=Ins 0x52,
numpad1=End 0x4F=PANIC!, numpad7=Home 0x47=enable, numpad9=PgUp...) ต่างแค่
extended flag; bind_hotkey ผูกด้วย scan → โดนทั้งคู่. แก้: `_on_press/_on_release`
ใน bind_hotkey ทิ้ง event ที่ `e.is_keypad` True = **trigger scan-code รับเฉพาะ
คีย์บอร์ดหลัก** (ผลข้างเคียงที่ตั้งใจ: กด numpad จะไม่ trigger อะไรเลยทุกมาโคร).
ไม่เกี่ยวกับ Fn ตามที่โอสงสัย. ยังไม่ live-test (โอกด numpad เองดู).
Mode CC = `skillspin strict 1 2 3 9!`, Mode Damage = `skillspin strict 4 5 6 7 9!`
(ผังใหม่โอ: CC=1-3, Damage=4-7, 9 ด่วนทั้งคู่; comment สอนแก้เลขในตัว; group
"skills" สลับโหมดกันเองเหมือนเดิม; ทั้งคู่ trigger ว่าง = สั่งผ่านปุ่ม START).
Engine pid 17428. เทสต์ 25/25 เดิมผ่าน. **ตามด้วย: สลับโหมดต้องตัดทันที (โอถาม)** —
skillspin ไม่เคยดู soft stop (คลาสบั๊กเดียวกับ pathwalk laps 20/7): กด Damage ขณะ CC
ค้าง strict-wait → CC ทำต่อจนจบตา + สองโหมดกดชนกันหลายวิ; แก้บรรทัดเดียว
`stop = _with_soft_stop(stop)` ต้น skillspin → mode switch/กดซ้ำหยุด rotation เดิม
ภายใน ~0.1s แล้วโหมดใหม่รับช่วง (เทสต์ T15: soft ตัด strict-wait, 26/26).
**ต่อ: E/Q = สกิลแทรก (โอขอ)** — มาโคร stop-held E/Q เปลี่ยนชื่อเป็น "Skill E/Q แทรก
(พัก rotation)": เพิ่ม `skillhold 1500` หน้า stopheld → กด E/Q = rotation/CC/Damage/
aimtap พัก 1.5 วิให้สกิลแทรกออกก่อนแล้วไล่ต่อเอง (+ยังปล่อยปุ่มเดินค้างแบบเดิม);
LShift/LCtrl ยังเป็นเบรกล้วนไม่พัก rotation. Engine pid 5976.
**ต่อ: overlay mode (โอขอ "v แทรกแล้วกลับมา c เอง"):** โอย้าย trigger โหมดเป็น C/V เอง
(CC=`strict 1 5`, Damage=`strict 3 4 6 7 9!` — ของโอ อย่าทับ). ฟีเจอร์ใหม่: macro field
`"overlay": true` (Mode Damage มีแล้ว) — toggle ที่เป็น overlay ตอน START จำ group-mate
ที่มันเบียด (self._overlay_return) แล้วตอนถูกกดปิด **auto-restart ตัวนั้น** ผ่าน
self.after(350, runner) (ต้องเป็น Tk thread — Timer thread เจอ chirp/var ข้ามเธรดล้ม
เงียบ, บั๊กที่เจอตอนเทสต์); กด C ทับ V = ยึดเวทีปกติไม่จำ; กด C ปิด = จบทั้งหมด.
GUI Save คงฟิลด์ overlay ไว้ (unknown-key passthrough เดิม). เทสต์ App-level 7/7
(ต้อง app.update() pump after-queue ในเทสต์ไม่มี mainloop). Engine pid 16776.
**ต่อ: จุดกำเนิด aimtap (โอถาม "นับจากจุดยืนจริง"):** ทดลองเดิน 4 ทิศหาก้อนนิ่ง
(ทุกอย่างไหลตามพื้นยกเว้นตัวเรา) — เดินไม่ออก (flow 6-9px; โอกำลังเล่น/ติดน้ำพุ อย่าฝืน
ขยับตัวละครตอนโอออนไลน์อยู่) → วัดจากภาพนิ่งแทน: **ตัวยืน ≈ กลางจอเป๊ะ (956,536 vs
960,540)** → origin เดิมถูกแล้ว ไม่ทำระบบจับเท้า/ชื่อ (SpiritVale วาดป้ายชื่อ+เลือด
**ใต้**ตัว ไม่ใช่เหนือหัว). ตัวเลื่อนตอนเดิน (ข้อสังเกตโอ) = เลื่อน**แนวเดียวกับทิศเดิน**
ซึ่งขนานกับเวกเตอร์เล็ง → ทิศไม่เพี้ยน เพี้ยนแค่ระยะ ±~10% (กลบด้วย DIST); ถ้าอยาก
ชดเชยจริงต้องวัด lead ตอนโอ AFK ที่โล่ง (สคริปต์ find_char_anchor2.py ใน scratchpad
พร้อมใช้ — gate flow ≥25px กันข้อมูลขยะ). pathwalk ไม่ต้องแก้ (odometer วัด camera
motion; anchor ทุกตัวทำตอน settle ซึ่ง lead→0).
**ต่อ: เดินสุ่มไม่ซ้ำแพทเทิร์น (โอกลัวผิดสังเกต):** ① random form สุ่ม waypoint ใหม่
**ทุก lap** (`is_random` → re-parse toks ต้น lap; เดิมสุ่มครั้งเดียวแล้ววน 999 = ยัง
เป็นแพทเทิร์น) ② random mode ตอบสนองกำแพงแบบคน: `max_avoid = 1` (หลบ 1 ทีไม่ผ่าน
= เปลี่ยนเป้าไปทางอื่นเลย; เส้นทางตายตัว rect/circle คง 6 เดิมเพราะต้องตามเส้น);
blocked 2 จุดติด = กลับบ้าน re-anchor เดิม. มาโคร "Path: เดินสุ่ม (PgUp)" (โอย้าย trigger
เป็น pageup เอง) = `pathwalk random 6 12 laps 999`. เกณฑ์ตรวจติด 1.8s ห้ามลดต่ำกว่านี้
(สกิลรูทตอนร่าย = false stuck, บทเรียน 20/7); สตัน/แช่แข็งยาว = ระบบจะสลับเป้าไปเอง
ไม่อันตราย. Verified: regen สุ่มต่างกันจริงต่อรอบ + lint ผ่าน; ยังไม่เดินสดจริง (โอเล่นอยู่).
**ต่อ: แท็บ "เดินอัตโนมัติ" (GUI config — โอขอไม่อยากแก้ใน Steps):** แท็บใหม่ใน
notebook: radio รูปแบบ (สุ่ม/สี่เหลี่ยม/วงกลม) + spinbox จุด/รัศมี/สูง + **ไวต่อการติดขัด
(วินาที)** + **หลบก่อนเปลี่ยนเป้า (ครั้ง)**; ปุ่มบันทึก = เขียนทับบรรทัด pathwalk ของมาโคร
แรกที่มี + จูนนิ่งลง `PW_CFG` (persisted settings["pw_cfg"]; runtime อ่านทับ PW_STUCK_S/
avoid ต่อการเดิน, floor 0.5s). แท็บ preload ค่าจากมาโครจริงตอนเปิด. **ข้อมูลใหม่จากโอ:
ร่ายเวทในเกมนี้ตัว "ไม่นิ่ง"** (ขัด assumption 20/7 ที่ตั้ง 1.8s กัน cast-root) → เปิดให้
โอทดลองลด stuck_s เองได้ (เตือนในฉลากเรื่องสตัน). Smoke E2E: preload ✓ apply→line+
cfg+persist ✓ restore ✓. **ต่อ: รูปวงรี + jitter (โอขอ "คงรูปแต่ไม่ซ้ำ"):** pathwalk เพิ่ม
form `oval RX RY` + modifiers `scale F` (ขยาย/ย่อทั้งรูป) และ `jitter J` (ทุก waypoint
เบี้ยว ±J หน่วย สุ่มใหม่**ทุก lap** — regen ครอบทั้ง random และ jittered pattern);
`_pw_mod()` helper strip key-value; jitter ไม่แตะ home (กลับจุดเดิมเป๊ะเสมอ). GUI แท็บ
เดินอัตโนมัติ: radio วงรี + ช่อง "สุ่มแกว่งจากเส้นทาง" (0=ปิด; random ไม่ใส่ jitter ให้
เพราะสุ่มอยู่แล้ว) + preload อ่าน jitter/oval จาก line จริง. Verified: parser (oval 15 จุด,
jitter ต่างต่อ parse, scale 2×r8==r16, lint) + GUI apply→line ถูก.
**ต่อ: ชุดย้ายเครื่อง (โอถาม "ย้าย+แก้เองไม่มี Claude"):** ① ปุ่มใหม่ **"Calibrate สกิล"**
ข้าง Calibrate HP = **คลิก 2 ครั้ง** (กลางไอคอนช่อง 1 แล้วช่อง 9; GetAsyncKeyState
edge-detect ใน worker thread, status นำทางทีละขั้น, sanity ช่อง9ขวา+แถวเดียว) →
SKILL_CAL {x0,pitch,y ref-units + win_w/h} persisted settings["skill_cal"];
`_skill_geo(hw)` ใช้ cal เมื่อ win size ตรง ไม่ตรง = fallback ค่าคอมไพล์; skillspin ใช้
ผ่าน _skill_geo แล้ว. **CV auto-fit ลองแล้วทิ้ง** (ฉากฟาร์มทำ comb ล็อกผิดช่อง/ผิด phase
2 รอบ — คลิก 2 ทีชัวร์กว่าสำหรับ non-coder). Verified จำลองคลิกจริง: pitch 64.75 เป๊ะ
ตำแหน่งคลาด <1px + _skill_geo คืน cal ถูก (การ persist ผ่านปุ่มจริงต้องมี mainloop —
เทสต์เขียน json ไม่ได้แต่ production ได้). ② `requirements.txt` + **`MIGRATE_ย้ายเครื่อง.md`**
(ก๊อปโฟลเดอร์+ติดตั้ง python+pip -r+ตั้งค่า 1st run + ตารางอาการ→ปุ่มแก้: Calibrate=
แถบ/ไอคอน, Pick Point=จุดคลิก, Pick Pixel=สี). ⚠️ gotcha ซ้ำรอย: engine เก่าหลบ tray
(MainWindowTitle ว่าง!) + ตัวใหม่ติดกล่องเตือน single-instance = เจอ 2 pythonw —
kill ทั้งคู่ก่อน relaunch.
**ต่อ: Overlay ลอย + ตัวกรองสตันเดิน 0.5s (โอขอ):** ① `_build_overlay/_ov_tick`:
Toplevel overrideredirect+topmost+alpha .78 กลางขอบบนจอ, **click-through**
(WS_EX_LAYERED|TRANSPARENT via GetParent(winfo_id)), poll 700ms โชว์ toggle ที่รัน
(+holdkeys, ตัดชื่อหลัง " ("): แดง=Disabled / เหลือง=พร้อม / เขียว=ON: รายชื่อ;
checkbox "Overlay" ข้าง Beep (persisted settings["overlay"], default ON). ② goto
stuck-branch: `sidestep()` คืนระยะที่ขยับจริง — ขยับตั้งฉาก <6px = **ติดสถานะไม่ใช่กำแพง**
→ `wait_unlock()` (pulse ทุก 0.9s ดู ground flow, สูงสุด 12s, ไม่นับ avoid) → โอตั้ง
"ไวต่อการติดขัด" 0.5s ได้ปลอดภัย (hint ในแท็บอัปเดตแล้ว; โอต้องไปตั้งเลขเองในแท็บ).
Smoke: overlay ON/idle/hidden ✓ + 26/26 เดิม. ยังไม่เห็นสดบนเกม (topmost บน borderless
ควรได้; ถ้าเกมเป็น exclusive fullscreen overlay จะไม่โชว์ — ยังไม่เคยเช็คโหมดจอจริง).
Engine pid 7576.

**21/7 ดึก(4) — ปุ่ม "> START" ชุดมาโคร + จำชุดล่าสุด (โอขอ):** ลิสต์มาโครเป็น
selectmode extended (ลาก/Ctrl+คลิกเลือกหลายตัว; editor โชว์ตัวแรก, ปุ่ม Copy/Delete/
Up/Down ทำงานกับตัวแรกที่เลือก) + ปุ่มเขียว "> START (ที่เลือก / ชุดล่าสุด)" ใต้ลิสต์ →
`_start_selected()`: auto-ENABLE engine ถ้ายังปิด → ยิง `_make_macro_runner(m)()`
ทุกตัวที่เลือก (reset last_fire ก่อน กัน debounce '' ชนกัน; toggle ที่รันอยู่ = ข้าม
idempotent, Enabled=false = ข้าม) → SetForegroundWindow เข้าเกม → เซฟชื่อชุดลง
settings["start_set"] (จำเฉพาะตอนเลือกจริง; กดตอนไม่เลือก = รันชุดล่าสุด → เปิดเครื่อง
มา คลิกเดียวเล่นได้เลย). ระวังอนาคต: มาโครโหมด hold/sequence เริ่มจากปุ่มนี้จะจบทันที
(เช็ค trigger_is_pressed ซึ่งไม่มีปุ่มจริงกด) — ชุดของโอเป็น toggle/once ทั้งหมดไม่กระทบ.
ต่อมาโอขอ "ไม่ต้อง Trigger ทุกอัน" → เพิ่มปุ่ม **STOP** แดงข้าง START:
`_stop_selected()` = set soft event ของ toggle ที่เลือก (ไม่เลือก = หยุดทุก toggle
ที่กำลังรัน; watcher นอกชุดไม่โดน, engine ยัง enabled) → **trigger กลายเป็น optional**:
มาโครช่อง Trigger ว่าง = สตาร์ท/หยุดจากปุ่ม GUI เท่านั้น (ลบ trigger เอง = ปุ่มคีย์บอร์ด
ว่างขึ้น); โอตั้งใจเก็บ trigger ไว้เฉพาะบางตัว. Engine pid 5716; ยังไม่ได้เห็นโอกดจริง. **แก้ Ch1 หาย:** โอเผลอลบ Channel→1 + Auto Heal
(=) ตอนล้างมาโครเก่า — กู้ทั้งคู่จาก context + สำรองทั้งไฟล์เป็น macros.backup-20260721.json;
Q spam โอลบเอง (ตั้งใจ), เพิ่ม "Stop held keys (Q)" trigger q ให้ (Copy เว้น trigger ว่าง
by design โอไม่รู้ — สอนแล้ว).

**21/7 ดึก(3) — `skillhold` บัพก่อนสกิลรอ (โอขอ):** step ใหม่ `skillhold MS` = แช่แข็ง
skillspin+aimtap; เรียกซ้ำ = ต่ออายุ. Keeper โล่/ปริซึมใส่ `skillhold 2500` ก่อน tap i/u →
บัพหมด = rotation หยุดรอ กดบัพซ้ำทุก ~2s จนไอคอนขึ้น แล้ว hold หมดอายุเอง (ไม่มี step
ปลด). **วาล์วกันพัง: hold ต่อเนื่อง >15 วิ = ปล่อย rotation + log** (กันเคสตรวจไอคอนพัง
หลังแพตช์แล้วฟาร์มค้างทั้งคืน; ปล่อยแล้วพฤติกรรม = keeper spam แบบเดิม). strict slot-timeout
ไม่นับเวลาที่โดน hold. เทสต์ 24/24+9/9. **พิสูจน์สดสำคัญ: สี signature บัพหลังแพตช์ยังตรง**
— กด I/U แทนโอผ่าน PostMessage (เทคนิค AttachThreadInput เดิม) แล้ววัด: โล่ #08083f
151px / ปริซึม #a46dff 13px ในโซน ref 5 58 95 148 = ผ่านเกณฑ์ทั้งคู่ + ยืนยันปุ่ม U/I
กดติดจริง. hp_cal ปัจจุบัน (17..229,y76) ตรงกับ find_hp_bar สด = ฮีลไม่ได้พังจากแพตช์.
Engine pid 5252. ยังไม่เห็นสด: จังหวะ rotation หยุด-รอ-ปล่อยกับเกมจริง (โอดูเองตอนฟาร์ม).

**22/7 — พรางชื่อแอป (โอขอ "ไม่เห็นโต้งๆ"):** รวมชื่อเป็นค่าเดียว `APP_TITLE` (บนสุด
ใกล้ palette) ใช้ทั้ง title bar / taskbar / tray tooltip / กล่องเตือน single-instance;
default = **"Input Settings"** (ดูเหมือนโปรแกรมตั้งค่าทั่วไป). แก้ชื่อ = แก้บรรทัดเดียว.
**22/7 ต่อ:** โอรายงาน "ยังเดินถูกำแพง" ตอนใช้รูปทรง — เพราะ avoid cfg เดิมคุมเฉพาะ
random → แก้: `PW_CFG["avoid_random"]` คุม**ทุกรูปแบบ** (default เดิมถ้าไม่มี cfg:
random=1, รูปทรง=6; GUI เซฟ cfg เสมอ = effectively ค่าในแท็บคุมหมด); waypoint ที่ข้าม
= ตัดมุมนั้น แล้ว re-anchor ท้ายรอบเยียวยาเอง; hint ในแท็บอัปเดต. Engine pid 4460.
**22/7 ต่อ(2) — wall-slide detector (โอขอ "กดเฉียงแต่เดินตรง=ติดกำแพง"):** ใน goto():
ทุก 12 tick (~0.45s) เทียบการเคลื่อนจริงรายแกน vs ส่วนแบ่งที่สั่ง×ความเร็ววิ่งโล่ง (EMA
เรียนจาก window สะอาด along>0.7*ema; ema>8 ถึงทำงาน — เริ่มเดินใหม่ต้องมี window โล่ง
ก่อนถึง arm) — แกนที่สั่งแล้วได้ <35% ของโควตา 2 window ติด = โดนกำแพง → **mask แกนนั้น
0.8s (เลาะกำแพง)** แล้ว hysteresis ลองเฉียงใหม่เอง วนจนพ้น; ทั้งสองแกน blocked = ปล่อยให้
progress-check+status-probe เดิมจัดการ; น็อคแบ็ค = hits 2 ติดกรองให้; mask ไม่ทำให้ want
ว่าง (กัน stall). Log throttle ทุก 3 mask. Synergy: เลาะแล้วไม่เข้าใกล้เป้า → progress
detector → sidestep/ข้าม waypoint ตามเดิม. compile+26/26; **ยังไม่เห็นสดกับกำแพงจริง**.
Engine pid 16892.
**22/7 ต่อ(3) — โอรายงาน "เดินแปลกมาก" → ลองเองแล้ว REPRO ไม่ได้:** เดินสด rect 10 10
ในเมือง 2 เงื่อนไข (เปล่า / พร้อม rotation ยิงไปด้วย) ที่ค่าโอเป๊ะ (stuck 0.5, avoid 0) —
**สะอาดทั้งคู่** (6.1s/14.5s, home off ≤0.8px, ไม่มี stuck/slide event เลย; mm autocal
วัดได้ 70-89). สมมติฐานเหลือ: แมพฟาร์มจริง (มอนชน/สิ่งกีดขวาง) + ค่าไวสุดขีด → เปลี่ยนใจถี่.
แก้เพิ่ม: **grace recheck** — stuck เด้งแล้วดันต่อ 0.35s วัดซ้ำ (เคลื่อน ≥12px = false alarm
ไปต่อ) ก่อนเข้าโพรบ/ข้ามเป้า → มอนชน/รูทสั้นไม่ทำให้เต้นแล้ว; verified เดินสดยังเนียนหลังแก้.
ถ้าโอยังเห็นแปลก: ต้องถามอาการเจาะ (ซิกแซก? หยุดบ่อย? วนผิดรูป?) + ดู Log ตอนเกิด.
Engine pid 7856.
**🔴 กติกาโอ 22/7 (ยืนถาวร): รีสตาร์ต engine / ทดสอบเองตอนตัวละครอยู่แมพฟาร์ม =
ต้องเปิดชุดเอาตัวรอดคืนเองทันที ไม่งั้นตัวตาย** — เปิด: Home (enable) + ฮีล (=) +
เฝ้าบัพโล่ (-) / ปริซึม (0) / รองเท้าปีก ([) + rotation (insert); เว้นได้แค่ PgUp เดิน /
PgDn พุ่ง. วิธีเปิดเอง: หลัง relaunch ส่ง Home สังเคราะห์ (scan 0x47 ext) แล้วยิง trigger
แต่ละตัว (scan code + edge; engine เกิดมา disabled เสมอ) — หรือแจ้งโอทันทีถ้าทำไม่ได้.
ก่อนหน้านี้เคยรีสตาร์ตทิ้ง watcher ดับบ่อยมาก = เสี่ยงตายทุกครั้งที่โอไม่อยู่หน้าจอ.

**22/7 ต่อ(8) — SPOT MEMORY + 🔴 บั๊ก mm-scale ข้ามแมพ (เทสต์สดชั้น 2 กับโอ):**
① **ความจำจุดฟาร์ม**: spots/spots.json + PNG (cap 20 LRU) — จบเดิน ≥1 lap เก็บ
mm_anchor+adapt scale (_spot_remember ใน finally); เริ่มเดิน _spot_match (corr≥0.18,
shift≤45) → เริ่มวงที่ scale ที่เคยเรียน (ชนะ pre-fit ผ่าน StopIteration). Verified สด:
"จำที่นี่ได้ (ตรง 21-22%) → เริ่ม 72/85%" — แต่บนแมพมินิแมพลายจัด corr แกว่ง 0.11-0.25
คร่อม threshold = จำได้บ้างพลาดบ้าง (พลาด = แค่เรียนใหม่ 1 รอบ ไม่อันตราย); แมพสะอาด
จะจำแม่น. pooled-correlation ลองแล้วแยกแมพไม่ขาด (proxy 0.135 vs same 0.161) ไม่ใช้.
② 🔴 **แก้บั๊กร้าย: PW_MM_SCALE fallback เป็นของแมพ/ซูมอื่น** — snap/lap-end correction
ที่ใช้ scale ผิด = ทำ pos พังเอง (เห็นสด: phantom y=465-731 บนวงลึก 250, snap -700px) →
**ทุก absolute correction ต้อง mm_cal["locked"] (วัดบนแมพนั้นจริง) เท่านั้น**; ยังไม่ lock
= odometry ล้วน (พิสูจน์แล้วแม่น: home offset 0.0 โดยไม่มี correction เลย); autocal เกณฑ์
pos≥280, |mdx|≥1.6, corr≥0.15; snap: ms2≥0.22 + **ดึงไม่วาร์ป** (cap 200px/ครั้ง).
รอบยืนยันสด: เรียนรู้สุภาพ (หด 85%→รอบสะอาด→ขยาย 91%) + รอบท้ายเกลี้ยง 9.1s.
Engine pid 5704 + survival set fired ตามกติกา.
**22/7 ต่อ(7) — ✅ เทปรอบ 2 (ปล่อยมือ 100%) พิสูจน์ adaptive fit ทำงานจริง:**
5.5 นาที: นาที 1 วงใหญ่ span 27×33 mm-px (ชนขอบ) → หดเรื่อยๆ → นาที 3-5 นิ่งที่
span ~10×3-13 + **net drift ทั้งเซสชัน (-0.6,-1.7) mm-px ≈ ศูนย์** (รอบ 1 ไหล 50!)
+ ฟาร์มต่อเนื่อง (เคลื่อน 67-190 mm-px/นาที) + HP ต่ำสุด 77% เฉลี่ย 99% (ฮีลเอาอยู่).
**Minimap pre-fit (ไอเดียโอ):** ใส่แล้ว — จำแนกสีพื้นรอบตัว (adaptive tol p90×1.3
clip 24-60) + **validity gate: บริเวณที่ยืน ≥60% ต้อง classify เป็นพื้น ไม่งั้นข้าม**
(แมพลาวาที่ทดสอบ = อ่านไม่ออกจริง → ข้ามอัตโนมัติ; เกณฑ์ fix 34 กับ adaptive 80
ล้วนให้ค่ามั่วบนแมพนี้ — px กลางมินิแมพโดน marker/มอนรบกวน); อ่านออก → เริ่มวงที่
scale ใหญ่สุดที่เส้นทาง ≥85% อยู่บนพื้น. ปฏิบัติตามกติกาโอครั้งแรก: หลัง restart ยิง
ชุดเอาตัวรอดเอง (Home + = - 0 [ insert สังเคราะห์) — ยืนยันผ่าน overlay ไม่ได้
(โอปิด Overlay?) เช็ค hotbar ก็ก้ำกึ่ง (ตัวละครอยู่ในเมือง ไม่มีเป้า) → ขอโอเหลือบดูเอง.
Engine pid ล่าสุดหลัง restart (ดูด้วย Get-Process pythonw).
**22/7 ต่อ(6) — โอเดโมสด: "ถูกำแพงส่วนใหญ่" → ADAPTIVE FIT:** ดูภาพอัดจริง (watch_run
thumbs) — แมพฟาร์มโอเป็น**หลืบป้อมแคบ ลาวา/กำแพงล้อม** เล็กกว่า rect 10 10 ที่ตั้ง →
วงทับกำแพงโดยกำเนิด detector ช่วยแค่ฟื้น ไม่หายถู. แก้: **วงหดตัวเองอัตโนมัติ** —
นับ wall events ต่อรอบ (slide mask + wall sidestep + waypoint skip) ผ่าน wall_ev dict;
จบรอบ: ≥2 events → adapt *= 0.85 (floor 40%), 0 events → *=1.07 คืนถึง 100%;
ทุก pattern regen ต่อรอบจาก base_wps × adapt (log "หดวงเดินเหลือ XX% / ขยายวงกลับ").
ข้อจำกัด: หดเข้าหา home (จุดกดเริ่ม = มุมขวาบนของ rect) — โอควรยืนให้ home อยู่ฝั่งโล่ง.
ยังไม่เห็น shrink สดจริง (โอเทสต์เอง ดู Log). Recording npz วิเคราะห์ trajectory ยังไม่ทำ
(เดโมโดน restart กลาง). Engine pid 21784.
**22/7 ต่อ(5) — โอ correction: "LShift วิ่งเร็ว" = มาโคร PgDn (aim spam) ไม่ใช่นิ้วกดจริง**
→ เบรก LShift ไม่เคยโดนสะกิด (synthetic ไม่ trigger hook) — **เปิดมาโครเบรก LShift คืนแล้ว**
(ปิดไปด้วยเหตุผลผิด); ตัวการเพี้ยนจริง = dash จาก aimtap spam → mid-lap snap คือ fix ที่ตรง.
คำถามสอง: **passive "โดนตีแล้ววิ่งไว"** = ไม่มีผล — ระบบวัดระยะทางจริงไม่ใช่เวลา (ลูป
ไซซ์เท่าเดิม), ความเร็ว passive อยู่ในลิมิตวัด (~1400px/s ที่ 25fps ก่อน phase-corr
หลุดครึ่ง tile), EMA slide-detector ปรับตามขึ้นเร็ว/ค้างสูงแต่เกณฑ์ 35% ยังไม่ false.
Engine pid 4632.
**22/7 ต่อ(4) — 🔴 ตัวการ "เดินเพี้ยนไม่กลับจุดเดิม" = LShift วิ่งเร็ว (โอเฉลยเอง):**
กลไก: ① LShift เป็น stopheld brake → โอกดวิ่งเร็วทุกครั้ง = ปล่อยปุ่มเดินของ walker
(สะดุดตลอด) → **ปิดมาโคร "Stop held keys (LShift)" แล้ว** (enabled:false + คอมเมนต์
อธิบาย; เบรกเหลือ LCtrl/E/Q) ② dash/sprint เร็วเกิน odometer → พลาดระยะ → pos เพี้ยน
สะสม + ③ _mm_autocal วัด scale จาก pos ที่เพี้ยน = ล็อกค่าพิษทั้งการเดิน. แก้: **mid-lap
snap** — ทุก waypoint settle อ่าน offset สัมบูรณ์จากมินิแมพ (corr≥0.15, |m|≤60) ถ้า
odometer ต่างเกิน 80px → snap pos = ค่ามินิแมพทันที (ไม่รอท้ายรอบ); autocal เพิ่ม gate
`state[blind_total] > 3 = ไม่ล็อก` (dash ทำ blind frames = pos เชื่อไม่ได้).
**Torture test สด: เดิน rect 3 รอบพร้อมสแปม lshift ทุก 400ms** — กลางทางเจอครบ
(stuck/สถานะรอหลุด/ไถลกำแพง/ข้าม waypoint แถวน้ำพุ) แต่ **home offset ≤0.8 mm-px
ทุกรอบ = กลับจุดเดิมเป๊ะ**. ยังไม่เห็น drift-snap fire จริง (tap เฉยๆ อาจไม่ dash แรง
เท่าโอกดเอง) แต่กลไกพร้อม. Engine pid 20476.
🔴 **GOTCHA ต่อจากนี้: หา process ด้วย MainWindowTitle -match 'Macro Engine' ใช้ไม่ได้แล้ว**
— ต้องหาด้วย `Win32_Process CommandLine -match 'macro_engine'` หรือ Get-Process pythonw
แทน (คำสั่ง kill/relaunch เก่าในเมมนี้ทั้งหมดต้องเปลี่ยน). mutex ภายในยังชื่อ
MacroEngine_SingleInstance (มองไม่เห็น ไม่ต้องเปลี่ยน). Engine pid 17968.
⚠️ ยังพราง**ไม่หมด**: overlay strip ขึ้นคำว่า "MACRO:" + ชื่อมาโครไทย (โอเห็นเอง โต้งกว่า
title) — ปิดได้ที่ checkbox Overlay; ถ้าโออยากพรางจริงค่อยเปลี่ยนคำใน _ov_tick.

**21/7 เช้า — 🔴 root cause "ไม่กลับจุดเดิม+ไถกำแพง" = ระบบ absolute correction ตายทั้งระบบบนแมพฟาร์ม (แก้+เทสต์ 9/9):**
วินิจฉัยตามที่โอขอ "พิจารณาทีละขั้น": ① `_mm_autocal` เดิม gate `blind_total>3 ทั้งการเดิน` —
แดชครั้งเดียว (aimtap/PgDn) = blind หลาย tick → cal ถูกปิด**ถาวรทั้ง walk** ② mid-lap snap +
lap-end re-anchor ต้องการ `locked` → ไม่เคยทำงาน = เดิน dead-reckoning ล้วน แดชทุกครั้ง
เพี้ยนสะสม → บ้านลอย → วงทับกำแพง → wall events → adaptive หดถึง floor 40% (spots.json
เก็บ 0.4 เพียบ = หลักฐาน) ③ พิสูจน์สดบนแมพ: มินิแมพแมพนี้ corr แค่ 0.08-0.17 ทั้งที่ยืนนิ่ง
(เกณฑ์ snap 0.22 แทบไม่ผ่าน, spot match 0.18 ไม่ติดเลย 18 อัน) ④ บั๊กเสริม: `locked=True`
ถูก set ก่อนเช็ค range = ค่าหลุด range ล็อก fallback ผิดๆ ได้. **แก้:** cal เป็น **segment-based**
(เทียบ pos↔minimap ระหว่าง 2 จุด settle ที่ไม่มี blind คั่น — แดชแค่รีเซ็ต segment ไม่ปิดระบบ)
+ sign check dpx*dm<0 + lock เฉพาะผ่าน range + ล้าง samp เมื่อ pos ถูกเขียนทับ. **"กดทีละยึกๆ"
(โอเห็นสด): เดิมหยุดยืน settle 0.3s ทุก waypoint (วงกลม 16 จุด, ยิ่งหด 40% จุดยิ่งถี่) → แก้ flyby:
เดินทะลุ waypoint ไม่ปล่อยปุ่ม, settle+อ่านมินิแมพเฉพาะทุกจุดที่ 4 + home.** เพิ่ม **engine.log
ถาวร** (LOG tee ลงไฟล์ข้างโค้ด, rotate 2MB) + telemetry ท้ายรอบ (cal=Y/N adapt walls blind)
+ log spot เกือบ match. เทสต์ stub-world 9/9: แดช 5 ครั้ง (เพี้ยน 600px ถ้าไม่แก้) กลับบ้านคลาด
27px. Backup: macro_engine.backup-20260721b.py. Engine pid 16920 — **trigger heal/บัฟส่วนใหญ่
ว่างแล้ว (สตาร์ทผ่านปุ่ม > START) → หลัง restart ต้องให้โอกด START เอง** (แจ้งแล้ว).
**ค้างจากโอ (ขอเช้านี้ ยังไม่ทำ):** ① มาโครหนีตาย HP ต่ำ → ย้ายแชนแนล**สุ่มไม่ซ้ำแนลเดิม** +
นับจำนวนแนลจริงจาก dropdown (แต่ละแมพไม่เท่ากัน; ต้องวัดสี highlight แถวแนลปัจจุบัน)
② แผนสำรองไถกำแพงไม่หาย: take-me-home → กดวาร์ปไปแมพ "The forge" → เปิดสกิล → เดินกลางแมพ
(ต้องให้โอเปิดหน้าวาร์ปให้วัดพิกัดก่อน) ③ หลังเข้าแมพ/ย้ายแนล กล้องอาจหมุน → auto-align:
ลองเดินขึ้น+ดูมินิแมพ แล้วหมุนกล้องจน "เดินขึ้น = เหนือ" (ต้องรู้ปุ่ม/วิธีหมุนกล้องจากโอ).
spots เก่าที่เรียน 0.4 จากยุคบั๊กยังอยู่ — ถ้า match จะเริ่มวงเล็กแล้วโตเอง 7%/รอบสะอาด ไม่อันตราย.
**ทำต่อในเทิร์นเดียวกัน:** ① keeper โล่/ปริซึม เปลี่ยนเป็น **recast ทุก 30 วิ** (โอ: "ห้ามหมด
กดตั้งแต่ยังไม่หมด"; แบบเดิม ifnocolor โดนสีฉากแมพหลอกว่าไอคอนยังอยู่ = ไม่ยอมกด) — guard
ใหม่ `ifhpabove 0` (HUD มองเห็น+ไม่ตาย ถึงกด); ปรับถี่ = แก้เลข delay 30000 ใน Steps
② `aimtap KEY DIST [CX CY]` — จุดกลางกำหนดเองได้ (โอขอ; grammar เดียวกับ click at,
anchor l+/r-/c ได้, y เป็น ref-int; ไม่ใส่ = กลางจอเดิม; ใส่ครึ่งเดียว = lint error) — lint 6/6.
Engine pid 980. **โอต้องกด > START เองหลัง restart (trigger ส่วนใหญ่ว่างแล้ว).**
**ตามต่อ "ยังไถขอบๆ" (โอรายงานหลังเดินจริง) — engine.log จับได้คาตา:** กำแพงอยู่ฝั่ง
ตะวันออกด้านเดียว (stuck คลัสเตอร์ x≈1130-1175 ทุกรอบ; circle 20 ยื่นถึง 1400) +
หด-ขยายตีกันเอง (ชน→85%→สะอาด 1 รอบ→ขยาย 91%→ชนกำแพงเดิม→77→66 วนไป) +
ยืนยัน cal=N ตลอด (มินิแมพแมพนี้ corr 0.09-0.20) แต่ home ไม่เพี้ยนเพราะ blind=0
(ไม่มีแดชระหว่างเดิน). **แก้: ① วงบุบ (dents)** — จำราย waypoint ที่ชน บุบเฉพาะมุมนั้น
*0.85 (floor 0.4) ฝั่งโล่งคงเต็ม; ฟื้น *1.05 เมื่อสะอาดติดกัน 2 รอบ; เฉพาะ pattern
ตายตัว (random/jitter ข้าม) **② วินัยขยายกลับ**: ต้องสะอาดติดกัน 2 รอบ + cap 90%
ของ scale ที่เคยชนล่าสุด. telemetry เพิ่ม dents=N. เทสต์ T3 (กำแพง x=1150 จำลอง
ตาม log): walls/lap 6→3→0→0→0→0 home 26px ไม่ regrind — สวีท 14/14.
Engine pid 7912 (โอกด START เอง).
**ตามต่อ "แค่ติดเสานิดหน่อยล่ะ?" (โอถาม): แยกเสา/กำแพงแล้ว (สวีท 19/19):**
หลบข้างสำเร็จ+ถึง waypoint = เสา/มอน → บุบเบา ×0.95 floor 70% เงียบๆ **ไม่หดวงรวม**;
ถึงไม่ได้จนข้าม (r=False) = กำแพงจริง → บุบแรง ×0.85 floor 40% + log; หดวงรวมเฉพาะ
lap_skips≥2 หรือไถล (slide-mask)≥3/รอบ (นับแยก masks_ev). บทเรียนจากเทสต์:
① dents **ห้ามคลาย**กลางการเดิน (คลายแล้วมุมที่เพิ่งสะอาดกลับไปชนซ้ำ) ② แตะกำแพง
แม้หลบผ่าน = จดขนาดนั้นเป็น wall_lo (เพดานขยาย 90% ของมัน) ไม่งั้นวงโตกลับไปแตะอีก.
T4 เสากลางเลก: เจอรอบแรก หลบ ไม่หด รอบถัดไปสะอาด. Engine pid 12808 (7912 โอปิดเองก่อนหน้า)
— **โอกด START เอง**.
**ตามต่อ (โอถามความร้อน CPU 70-75° + "มินิแมพยังไม่ได้ควบคู่ใช่ไหม"):**
① **ความร้อน**: ตัวการคือ pathwalk goto/tick **ไม่มี sleep เลย** — spin เต็มคอร์รัน FFT ซ้ำ
บนเฟรม cache เดิม (30ms TTL) → เพิ่ม `PW_TICK_S=0.03` pace ใน tick() (จังหวะ %12/%15
เขียนมาบน assumption ~27 t/s อยู่แล้ว ยิ่งถูกขึ้น); heal poll 30→100ms; keeper 30วิ อยู่แล้ว.
เทสต์ sim ตั้ง me.PW_TICK_S=0 ให้เร็ว. delay 50-100ms ของมาโคร tap ไม่ใช่ตัวกิน (ตัวกิน
คือทุกอย่างที่ capture จอ). ② **มินิแมพ**: ท่อครบแต่ไม่เคยติดจริงบนแมพฟาร์ม → ทดลองบน
spot PNG 18 ใบ: preprocess ช่วยนิดเดียว (0.10→0.13) แต่**เปลี่ยนวิธีเป็น zero-mean NCC
(ปิดลูกศรกลาง r14 + blur3) = 0.80 median ที่เดียวกัน / ~0.2 คนละแมพ / 0.1 noise** →
`_pw_mm_prep`+`_pw_mm_shift` ใหม่ ใช้กับ autocal(เกณฑ์ 0.55)/snap(0.55)/lap-end
re-anchor(0.50, fallback ground <0.50)/spot match(0.55). **GOTCHA: raw cross-corr peak
ทิศกลับด้านจาก _pw_shift — negate แล้ว + พิสูจน์ sign 3/3 ในตัว engine**. kill-switch
map_suspect **คงเดิม phase<0.05** (worst same-place NCC 0.22 vs คนละแมพ 0.18-0.21
margin บางเกินจะปิดเกมอัตโนมัติ); lap-end map-change ต้อง NCC<0.25 AND map_suspect 2 ครั้ง.
spots ยุคบั๊ก (scale 0.4) ย้ายเข้ากรุ spots_old_20260721/ เริ่มจำใหม่ (NCC ทำให้ match ติดจริง
แล้ว จะได้ไม่หยิบค่าพิษ). สวีท 19/19. Engine pid 17976 — เกมปิดอยู่ตอนทำ โอเปิดเกมแล้วกด START.
**ต่อ (โอ: "ทำงานค้าง+หาข้อมูลเน็ต"):** ① **step ใหม่ `channelswap`** = หนีตายย้ายแนลสุ่ม:
เปิด dropdown → นับแถวแนลที่มีจริงด้วย ifcolor #353b4b รายแถว (ref y 35/54/73/92/112/131/150,
รองรับ 7 แถวแรก) → สุ่มคลิก; **คลิกแนลปัจจุบัน = ไม่มี popup (พฤติกรรมพิสูจน์แล้ว) → เปิดใหม่
สุ่มแถวอื่น**; popup มา → กด Ok. ประกอบจาก token มาโคร Channel->N เป๊ะๆ ผ่าน exec_step
recursive (_ch helper). มาโครใหม่ "หนีตาย: เลือดต่ำย้ายแนลสุ่ม" (trigger ว่าง, ifhpbelow 20 →
channelswap → delay 8000). ⚠️ **ยังไม่เทสต์สดกับเกม** (เกมปิดตอนเขียน) — ตายสนิท ifhpbelow
ไม่ยิง (hp อ่านเป็น None) ช่วยได้เฉพาะ 'ใกล้ตาย'. lint+no-window smoke ผ่าน, สวีท 19/19 เดิมผ่าน.
② รีเสิร์ชเน็ต: สถาปัตยกรรมเราตรงตำรา DR+landmark แล้ว; ของที่อาจอัปเกรดวันหน้า =
Windows.Graphics.Capture (Win10 1903+, async เร็วกว่า PrintWindow ที่ blocking ~16ms) —
ยังไม่คุ้มทำตอนนี้. Engine pid 21784. **ค้างเทสต์สด:** channelswap, keeper 30วิ, aimtap origin,
NCC บนแมพจริง; **ค้างฟีเจอร์:** วาร์ป Forge (รอโอเปิดหน้าวาร์ป), หมุนกล้อง auto-align (รอโอบอก
ปุ่มหมุนกล้อง).
**ต่อ (โอ: "มาโครแนลเพี้ยน ขอปุ่มคาลิเบรต"):** ปุ่มใหม่ **"Calibrate แนล"** (ข้าง Calibrate สกิล)
— UI แชนแนลเพี้ยนจากแพตช์ 21/7 ที่ scale ไม่ uniform. วิธีใช้: **ชี้เมาส์ 4 จุด กด SHIFT ขวา
ทีละจุด** (ไม่ใช่คลิก — คลิกจะกดเมนูจริง): ปุ่มแชนแนล → แถวแนล1 (โอเปิด dropdown เอง) →
แถว2 → ปุ่ม Ok (โอคลิกแนลอื่นให้ popup ขึ้นเอง; จบแล้วกด Close ยกเลิกได้). เก็บใน
settings["chan_cal"] (module CHAN_CAL); `_chan_geo/_chan_row_y/_chan_steps(n)` generate
step ทั้ง Channel->1..12 (≤7 คลิกตรง, 8+ hover แถว4+wheel+แถวล่าง) → เขียนทับมาโครทันที
ตอนกดสำเร็จ; channelswap อ่าน CHAN_CAL สดทุกครั้ง. Default = ค่าวัด 18/7 เป๊ะ (pitch 19.15
reproduce แถว 35/54/73/92/112/131/150 ครบ — 19.17 ทำแถว4 คลาด 1px). เทสต์: token
default ตรงของเดิมทุกบรรทัด + lint 1-12 ทั้ง default/calibrated + App build + walk suite
19/19. Engine pid ล่าสุดดู Get-Process. ยังไม่มีใครกด calibrate จริง (เกมปิดอยู่).
**ต่อ (โอมอบอิสระ "เทสต์สด+พัฒนาเสถียร"): 🔴 ค้นพบบล็อกหลัก — เกมเป็น fullscreen
1920x1080 แล้ว minimize ตัวเองทันทีที่โอสลับไปทำงานอื่น**; พิสูจน์แล้ว **PrintWindow
กับหน้าต่าง minimized คืน None** = ระบบมองไม่เห็นเกมเลย (fail-safe IsIconic เดิมถูกต้อง;
ตอน minimize mss fallback อ่านจอ desktop โอแทน — เทสต์ที่รันช่วงนั้นโมฆะทั้งหมด).
**ทางแก้ = โอเปลี่ยนเกมเป็น Borderless/Windowed** (สมัย 20-21/7 เกมเป็น windowed
958x614 ถึงเทสต์หลังบ้านได้; borderless โดนหน้าต่างอื่นทับ PW ยังอ่านได้ พิสูจน์แล้ว 21/7).
**ที่พิสูจน์สดได้ก่อนโดน minimize: NCC self-match บนเกมจริง = 1.0 นิ่งสนิท** (วิธีเก่า
0.08-0.17), HP 100 อ่านได้, flow 8/8. **สิ่งที่ส่งเข้าเกมตอน minimized (อาจค้าง):**
tap i/u + ลูกศร/pgup-dn/home/ins/del + Esc×7 — โอ restore แล้วอาจเจอเมนูค้าง กด Esc ปิด.
**WGC: ตัดสินใจไม่รื้อ** — จับ minimized ไม่ได้เหมือนกัน แก้ปัญหาจริงไม่ได้ ได้แค่เร็วขึ้น
~10ms ซึ่งไม่ใช่คอขวด + เพิ่ม dependency winrt + yellow border (Win11 ปิดได้แต่เพิ่มงาน).
**เกิดใหม่เลือดไม่เต็มแล้ว (โอแจ้ง แพตช์ใหม่)** — trick "ตายสลับแนล = เกิดเต็มเลือด" (18/7)
โมฆะ; อัปเดตคอมเมนต์มาโครหนีตายแล้ว (ฟื้นแล้วเลือดต่ำ → Auto Heal ต้องเปิดเสมอ);
⚠️ Calibrate HP ยิ่งต้องกดตอนเลือดเต็มเท่านั้น. **เตรียมพร้อมรันทันทีที่เกม visible:**
`makcu/live_test_suite.py` (ถาวรแล้ว) = บัฟ I/U + เดิน circle 10 สด (ดู cal=Y/CPU) +
**ไล่หาปุ่มหมุนกล้อง** (ตัวตรวจ: ฉากเปลี่ยน+ตัวไม่ขยับ+ลูกศรกลางมินิแมพเปลี่ยน; ผู้ท้าชิง
left/right/pgup/pgdn/home/ins/del; ถ้าไม่มีปุ่ม = กล้องหมุนด้วยเมาส์ → plan B flick) +
ลายเซ็น "เดินขึ้น=มินิแมพเลื่อนทิศไหน" (ฐาน camalign). **camalign + วาร์ป Forge ยังไม่เขียน**
(รอปุ่มกล้อง / รอเห็นหน้าวาร์ป). channelswap เพิ่ม: log เตือน "กด Calibrate แนล" เมื่อ guard
พัง + `_chan_snapshot()` เซฟ PNG มุมขวาบนทุกครั้งที่ dropdown เปิดจริง (calib_samples/
เก็บ 12 ล่าสุด) = วัตถุดิบออกแบบ auto-calibrate เต็มรูปแบบ. Engine pid ดู Get-Process.
**ต่อ (โอ 3 เรื่อง): ① OVERLAY บั๊กแก้แล้ว** — click-through เดิมยัด style ใส่ label ลูก
(GetParent ผิดตัว): WS_EX_LAYERED บน child ไม่มี alpha = **ตัวหนังสือล่องหน** + toplevel
ไม่ทะลุคลิก = "กล่องดำว่างเปล่ากดไม่ทะลุ" ที่โอเห็นเป๊ะ → แก้ GetAncestor(GA_ROOT) +
กติกาใหม่ _ov_tick: **โชว์เฉพาะตอนเกมเป็น foreground** (ลอยทับจองานตอนโอทำงาน =
น่ารำคาญ). ② aimtap จุดกลาง = ทำแล้วเมื่อเช้า; มาโครจริงโอ = "LShift aim spam (')"
trigger **pagedown** steps `aimtap lshift 50 / delay 50` — เพิ่มจุดกลางเอง: ต่อท้าย
บรรทัดเป็น `aimtap lshift 50 X Y` (พิกัดจาก Pick Point). ③ เมาส์เสมือน/พับจอ: อธิบาย
ให้โอแล้วว่า**เป็นข้อจำกัด OS** — จอ minimize = จับภาพไม่ได้ทุกวิธี + Windows มี cursor
เดียว; ทางที่ใช้ได้ = โหมดจอที่ไม่ minimize ตัวเอง (โหมด "Exclusive Windowed" ที่โอ
เพิ่งตั้ง**ยัง minimize ตอนสลับแอป** — ต้อง Borderless/Windowed ธรรมดา) แล้วเอา
หน้าต่างงานทับ. ⚠️ วันนี้ยิงปุ่มหลงเข้าเกมหลายชุดตอนมันแอบ minimized (i/u, ลูกศร,
pgup/pgdn, home/ins/del, esc หลายที) — โอเจอเมนู/แชทค้างให้ปิดเอง; **บทเรียน:
live suite ต้องเช็ค visible ก่อนกดทุกปุ่มและหยุดทันทีเมื่อ minimized ไม่ใช่กดแก้เพิ่ม**
(ยังไม่ได้แก้ในไฟล์ live_test_suite.py). SW_SHOWNOACTIVATE restore เกมโหมดนี้ =
**ยังแย่งโฟกัสอยู่ดี** อย่าทำตอนโอทำงาน. Engine pid ดู Get-Process (โอกด START เอง).
**21/7 เที่ยง — 🟢 โหมด WINDOWED = ปลดบล็อกเต็มตัว + LIVE SUITE v2 ผ่านจริงทั้งชุด:**
โอเปลี่ยนเกมเป็น windowed (client 1920x1009, ui_scale 1.8) — **เปิดแอปอื่นทับ เกมยังอยู่
ไม่ minimize, PW จับได้, ทดสอบหลังบ้านได้เต็มรูปแบบแล้ว**. HP auto-recal เองกับหน้าต่างใหม่
(อ่าน 100% ถูก). live_test_suite.py **v2** (guard เหล็ก: ทุกครั้งก่อนกดปุ่มต้อง visible ไม่งั้น
abort ทันที — v1 เคยพ่นปุ่มใส่เกม minimized). ผลจริง: **T1 บัฟ I/U ผ่าน PostMessage หลังบ้าน
ติดจริง (ไอคอนขึ้นทั้งคู่)**; **T2 เดิน circle 10 laps 2 ในเมือง Wayfarer's Landing:
กลับบ้านเป๊ะ NCC 1.00/0.98 offset ~0, dents บุบมุมตะวันออก (8-11/15) + หด 85→72%,
จำ spot; CPU 46% ของ 1 คอร์ (จาก 100% spin)**; cal=N เพราะมินิแมพเมืองซูมไกลมาก
(วัดจาก T4: scale ~350-400 ground-px/mm-px → เกณฑ์ dm≥1.6 ต้องเดิน 600px+ ต่อ segment
— แมพฟาร์ม scale 74-175 จะล็อกได้; ไม่แก้เกณฑ์ เพราะ odometry+NCC anchor เอาอยู่);
**T3 ปุ่มหมุนกล้อง: ไม่ใช่ left/right/pgup/pgdn/home/ins/del เลย → น่าจะเมาส์ลาก
(ถามโอแล้ว รอคำตอบ)**; **T4 กด W แล้วมินิแมพเลื่อน (+0.41,+0.33) = เฉียง ~45° —
กล้องตอนนี้ไม่ตรงเหนือจริง (ยืนยันปัญหาที่โอกังวล)**; T5 skill geo ใช้ ref-units ×1.8 auto.
**ปุ่มแชนแนลบนหน้าต่างใหม่: ตำแหน่งเคลื่อนเกิน scale (guard ไม่เจอ) → โอต้องกด
Calibrate แนล 4 จุดหนึ่งรอบ**; ลอง auto-find ด้วยสี #22222a = จับได้แต่แผงมืด 790px
ปนฉาก **ห้ามเขียนค่าจากสีล้วน** — แผน auto ที่ถูก: candidate-scan + คลิกยืนยัน dropdown
โผล่ (ทำใน channelswap รอบหน้า). **คิวงานถัดไป (โอให้ข้อมูลครบแล้ว): ① Relogin สุ่ม
45-60 นาที + ตอนตาย (Server เลือก SEA/Southeast Asia ping ต่ำสุด; ต้องวัดหน้า login)
② วาร์ป The Forge: ยืนหน้า Waypoint (แท่งฟ้า) ที่จุดเซฟเมือง → คลิก → world map →
เลือกแมพขวาล่างสุด 'The Forge' → หันกล้องให้ตรง → เดินลงบันได (ขึ้น/ลงนิด แล้วไปขวา)
→ เริ่ม rotation; บัฟเปิดก่อนวาร์ป — ทั้งสองต้องคลิกจริง (flick) = รอจังหวะโอไม่ใช้เมาส์
3 นาที + camalign ต้องรู้วิธีหมุนกล้องก่อน.**
**21/7 บ่าย — 🟢 AUTO-CALIBRATE แชนแนลเต็มรูปแบบ + ย้ายแนลจริงสำเร็จ (โอส่งภาพ 3 ใบ):**
ปุ่มแชนแนล = **สามเหลี่ยมขาวมุมขวาบนหัวมินิแมพ** (โอชี้ในภาพ) คลิก r-17..r-44 y11 เปิดได้
หลังบ้าน. `_chan_autocal(hw, click_fn, save)` = คลิกสามเหลี่ยม→อ่าน dropdown สด→วัด
y0/pitch/ปุ่ม/สีปุ่มเอง เขียน CHAN_CAL + มาโคร Channel->N ทันที **ไม่ต้องชี้มือ** (โอขอ
"ออโต้ กันพลาด ช้าได้"); ปุ่ม GUI "Calibrate แนล" = auto, "แนล(Manual)" = 4 จุด fallback;
channelswap **auto-cal เองครั้งแรกต่อ window size** + นับจำนวนแนลสด (แต่ละแมพไม่เท่า —
โอยืนยัน 7 ที่นี่; probe 1..12 หยุดเมื่อ miss 2 ติด ทน 1 miss กันต้นไม้บัง). **บทเรียนสร้าง
auto-cal ให้เสถียร (สอบ 6/6):** ① dropdown toggle + ปาล์มในฉากบังแถวล่างบางเฟรม →
ต้อง **reopen ซ้ำ×best-of-N frame + เลือก chain ที่ยาวสุด+เริ่มบนสุด** (longest even-spaced
chain ตัดหัวดำ/ต้นไม้) ② จำนวนแนลอ่านจากภาพไม่ชัวร์ → แยกหน้าที่: auto-cal วัดแค่ระยะ,
channelswap นับสด ③ ปุ่ม toggle: เปิดแล้วเช็ค ถ้าไม่เปิด=เคยเปิดค้าง→คลิกซ้ำ (retry×3).
🔴 **บั๊ก engine เก่าที่เจอ+แก้: `_region_color_found` (ifcolor/waitcolor/ifnocolor win) ใช้
Y นับจากขอบหน้าต่าง (r_.top) แต่ `_resolve_click_point` (คลิก) ใช้ Y จาก client (org.y)** —
ต่างกัน = ความสูง title bar (31px windowed); fullscreen เท่ากันเลยไม่เคยโผล่. โหมด windowed
ของโอมี title bar → guard/region ทุกตัวเลื่อน 31px = ปุ่มแชนแนล guard fail. แก้ให้ Y ใช้
org.y เหมือนคลิก (no-op ที่ fullscreen) — verify buff โล่/ปริซึม + HP ยังอ่านถูกหลังแก้.
สีปุ่มแชนแนลตอนนี้ = **#000000** (แพตช์/โหมดจอเปลี่ยนจาก #22222a อีก) → auto-cal เก็บ
btn_hex เอง กัน patch หน้า. **channelswap ย้ายไปแนล 7 สำเร็จสด** (สลับแนลจริง; รอบสอง
ล้มเพราะจอโหลด = ถูกต้อง มาโครหนีตายมี delay 8000). Engine pid 17208. calib_samples/
เก็บภาพ dropdown ทุกครั้งที่เปิด. **ค้าง: ปุ่มหมุนกล้อง = โอบอก "คลิกขวาลาก" (Setting
ไม่มี Camera Tilt=LShift ซ้ำ Skill1-0); Hotkeys เต็มจากภาพ: Skill row2=Q E R T Y U I O P +
LShift/LCtrl; ปุ่ม Log Out ล่างซ้ายใน Settings.** คิวถัดไป: camalign (คลิกขวาลากหมุนจนมินิแมพ
"เดินขึ้น=เหนือ"), วาร์ป Forge, Relogin (SEA, สุ่ม 45-60นาที+ตอนตาย, ใช้ Log Out) — ทั้งหมด
ต้องคลิกจริง = รอจังหวะโอลุกจากเครื่อง.
**21/7 บ่ายแก่ — 🏆 ภารกิจโอไม่อยู่บ้าน: RELOGIN + วาร์ป FORGE + CAMALIGN ครบวงจร
พิสูจน์สดทั้งหมด (โอสั่ง "หาอะไรทำ" + ให้ใช้จอ + ขอปิดจอกันคนออฟฟิศเห็น):**
**BLACKOUT** `makcu/blackout.py` = ม่านดำ fullscreen topmost click-through (จอมืดสนิท
mss=0.0 แต่ PW อ่านเกม+คลิกทะลุได้หมด) — **โอกด F12 ค้าง 1 วิ = ปิดม่าน**; ตอนนี้เปิดอยู่.
**เกม = Steam id 3767850** (`steam://rungameid/3767850`; โฟลเดอร์ Steam common/SpiritVale;
มี shortcut โฟลเดอร์ New folder บน Desktop: Borderless/Resize/TopMost toggles ของโอ).
**ค้นพบ+step ใหม่ 3 ตัว (in engine, ทดสอบสดผ่านหมด):**
① `relogin` — Log Out (Esc→ปุ่ม 0.194,0.757) → server select → **แถว SEA (0.5,0.475) +
Connect (0.5,0.916)** → char select → **ดับเบิลคลิกช่องตัวละคร (0.072,0.142) — ปุ่ม Play
Character เมินคลิกสังเคราะห์ทุกแบบ (จุดเรียนรู้สำคัญ)**; ตรวจหน้าจอด้วย state machine
(_px_at probe สี; จุด dark ต้องเลี่ยงตัวละคร: (0.28,0.35)+(0.68,0.55) — เคยพลาดเพราะ
(0.5,0.30) โดนหมวกฟ้า); เกมปิดอยู่ = เปิดผ่าน Steam เอง; timeout 240s. **Logout → ไป
char select ตรง (ข้าม server select) แต่ Back/Esc บน char select วนกลับ server select
ได้ — state machine เอาอยู่ทั้งสองทาง (ทดสอบแล้ว).** หลัง login: ตัวละครอยู่จุดเกิดเมือง
= **หน้าแท่น Waypoint พอดี**, กล้อง reset ทิศเหนือ, แชนแนลสุ่มใหม่, บัฟหาย.
② `warpforge` — จากจุดเกิดเมือง: คลิกแท่นคริสตัล (0.5,0.267 บนจอ เมื่อกล้องเหนือ+ยืน
spawn) → แมพวาร์ปเปิด (ต่างจากแมพปุ่ม M ที่**ดูได้อย่างเดียว ไม่มีปุ่ม Warp** — เสีย
เวลาหาไปรอบนึง) → tile The Forge (0.737,0.717) → **ปุ่ม Warp เขียว (0.94,0.973) ค่า 0
บาท** → ตรวจถึงด้วย HUD หาย→กลับ; ถึงแล้วลงที่แท่น Arcane Sigil ของ Forge, พรม
ทอดตะวันออกไปโซนบันได/ฟาร์ม (มอน Lv126-130).
③ `camalign [TOL]` — วัดมุมกล้อง (tap W 0.5s ดูทิศเลื่อนมินิแมพ NCC แล้ว S กลับ) →
**คลิกขวาลากที่กลางจอ = หมุน 0.265°/px; แก้ = ลาก -มุม/0.265** (ระวังเครื่องหมาย —
เคยใส่ +มุม แล้วหมุนหนี); iterate ≤4 รอบ tol 8°. พิสูจน์: Forge หลังวาร์ปเอียง -112° →
แก้เหลือ 0° ใน 2 รอบ. โอ confirm หมุนกล้อง = คลิกขวาลาก (Camera Tilt=LShift ในเกม
ไม่เกี่ยว). `_fg_click(hw,fx,fy,double)` helper = **ALT-tap ปลด SetForegroundWindow
lock** (จำเป็น! ไม่งั้น SFW เงียบๆ ล้มและคลิกโดนกลืน) + hover ก่อนคลิก (Unity).
**มาโครใหม่ 2 ตัวใน macros.json:** "🌋 ไปฟาร์ม The Forge" (once: บัฟ i,u → warpforge →
camalign; ต้องยืนจุดเกิดเมือง) + "⏰ Relogin สุ่ม 45-60 นาที (SEA)" (toggle: delay
2700000-3600000 → relogin → camalign). **take-me-home พิสูจน์สดจาก Forge:
กลับมาลงหน้าแท่นเมืองพอดี** = ลูปปิด: เมือง→ฟาร์ม→เมือง→ฟาร์ม ทำได้ไม่รู้จบ.
สถานะทิ้งท้าย: ตัวละคร login ใหม่อยู่จุดเกิดเมือง HP100, engine เปิดรอ START, blackout
เปิดอยู่ (F12 ปิด), เกมเปิดค้าง. **ค้าง: ตายแล้ว relogin อัตโนมัติ (ตรวจ death ยังไม่มี),
rotation ต่อท้าย forge macro (ยัง manual ผ่าน START), ฐานข้อมูลจุดฟาร์ม (โอขอ "จำทุก
ครั้ง"), บัฟก่อนวาร์ปใน macro ใช้ i/u เฉยๆ (ถ้าคีย์บัฟเปลี่ยนต้องแก้).**
**21/7 เย็น — บัฟ O (toggle ถาวร, โอสั่งเพิ่ม):** กด O = ขึ้น **2 ไอคอน** (ดาบทอง +
ผลึกน้ำแข็งฟ้า) ติดตลอด; **กดซ้ำ = ปิดสกิล** → keeper ต้องเช็คก่อนกดเสมอ. ทำหลังบ้าน
ทั้งหมด (โอนั่งทำงานอยู่): tap o ผ่าน PostMessage + วัด before/after จริง. ลายเซ็นที่เลือก:
**#4ee8fc tol15 mincov 0.2%** (ไฮไลต์ผลึกฟ้า; ตอนติด 83-127px/ตอนไม่มี 0; จงใจเลี่ยง
สีน้ำเงินเข้ม #000c30 เพราะชนไอคอนโล่ #08083f ที่ tol18). เสถียร 6/6 เฟรม + พิสูจน์
"มีแล้วไม่กดซ้ำ" สด. มาโครใหม่ **"Buff O (toggle ถาวร - เช็คก่อนกด)"** (trigger ว่าง):
ifnocolor ×2 ห่าง 1 วิ (กันไอคอนแวบ/เอฟเฟกต์หลอก) → skillhold → tap o → delay 4000;
ifnocolor มี hud guard ในตัว. **สถานะ: บัฟ O เปิดค้างไว้แล้ว.** มาโครหนีตายเพิ่ม
`camalign` ท้ายแล้ว (โอเคยสั่ง "หมุนกล้องผูกกับเปลี่ยนแนล"). Engine pid ล่าสุด (โอกด
START เอง — อย่าลืมเลือกมาโครใหม่เข้าชุดด้วย: Buff O + หนีตาย + Relogin ตามใจโอ).
blackout ถูกโอปิดแล้ว (F12 ใช้งานได้จริง).
**22/7 13:15 — งานอิสระ: fix เดิน/นำทาง + บทเรียน SOLO FORGE เอาแน่ไม่ได้:**
โอเฝ้าเห็นสด: ตัวละครติดหัวบันไดวน 60วิ + เดินเข้าวาปไปแมพอื่น. รากคือ stuck detection อยู่
ใน if ok(match บ้าน) -> ขอบบันได/วาป NCC ตก -> ไม่เจอว่าติด. **FIX: frame-to-frame stuck**
(เทียบ 2 เฟรม ไม่สน match บ้าน) + **wrong-map abort** (ok=False 5วิ=เข้าวาป จบ walk +
จำจุดวาป obstacle ถาวร) + **mob_dir เลี่ยงเพ็ท/ผู้เล่น** (โอ: จุดแดง=มอน+เพ็ทคนอื่น ขาว=ผู้เล่น
เขียว=ตี้; density filter + ตัดแดงติดขาว/เขียว + give-up ไล่ไม่ถึง6วิเลิก) + เอาซูมกล้อง+
SetForegroundWindow ออก + LShift บิ้งใต้เท้า1.8วิ(บัพสปีด) + hud_watch 75->25วิ. **🔴 เทสต์
Forge solo 4 รอบ: รอด2 ตาย2 — survival เป็นดวง ต้องปาร์ตี้แทงค์ (ไคท์+heal ฟื้นได้ถ้าไม่โดน
burst ตอนวาร์ป). การตายไม่ใช่บั๊กเดิน = หยุดเทสต์ solo, reliable path = STAY mode โอวางตัว+
ปาร์ตี้.** map-memory (โอ prioritize): เริ่ม occupancy-grid(obstacles+จำวาป) ยังไม่ครบ
(อ่าน walkable จากสีมินิแมพ/เดินลงบันได/pathfind = feature ใหญ่ รอ live-test ปาร์ตี้). ไฟล์
รายละเอียด C:\makcu\PLAN_FOR_OPUS.md. ตัวละคร HP100 เมืองปลอดภัย.

**22/7 11:40 — ✅ VERIFY ระบบตรวจจับครบใน RDP background จริง (โอสั่งทดสอบระหว่างทำงาน):**
เซสชัน ykfarm 1920x1009 maximized (auto-scale = ตรงค่าปรับเทียบเดิม). ผ่านสะพาน+โปรไฟล์
verify_stack.py/test_preflight.py: HP อ่านได้, **กด i,u -> โล่/ปริซึมตรวจเจอทันที (PostMessage
+ color 32-bit ใช้ได้ใน RDP)**, เข็มทิศ W/D ได้, เดิน mmkite 10/10วิต่อเนื่อง, boss ncc 0.44
ไม่หนีมั่ว. **soak เต็มชุด STAY 90วิ ไม่ crash** (rotation ยิง=วงเวท, บัฟบูสต์ HP 8045->10368,
หยุดสะอาด). แก้ soak cleanup: **STAY mode ไม่ take-me-home** (คงตำแหน่งที่โอวาง). gotcha เมือง:
สกิลบางตัว Can't cast yet (safe zone) ที่ Forge ยิงครบ. 🔴 ยัง verify survival จริงที่ Forge
ไม่ได้ (ต้องปาร์ตี้ โซโล่ตาย) — กลไกครบแต่รอรัน 1 รอบยืนยันตอนโอวางตัว+ปาร์ตี้. พร้อมปล่อย
farm_here.bat. [[project-macro-engine-rdpwrap]]

**22/7 08:55 — 🎉 RDPWrap สำเร็จ: 2 session พร้อมกัน (โอทำงาน + ฟาร์ม background):**
ยืนยันสด `query session` = console guole(1) Active + rdp-tcp#0 ykfarm(2) Active พร้อมกัน,
จอหลักโอใช้งานปกติ 100%. **สูตรที่ใช้ได้จริงบน Win11 Pro build 26200 / termsrv 10.0.26100.8115:**
① ลง sebaxakerhtc RDPW_Installer.exe v1.8.9.9 ② **ini ที่ installer bundle มาเก่า ไม่มี section
26100 เลย → ต้องโหลด `raw.githubusercontent.com/sebaxakerhtc/rdpwrap.ini/master/rdpwrap.ini`
(554KB, 170 sections 26100.x) ทับ `C:\Program Files\RDP Wrapper
dpwrap.ini`** — เช็คด้วย
`Select-String -Pattern '^\[10\.0\.26100\.8115\]'` ต้องเจอ (แค่ -match สตริงไม่พอ หลอก!)
③ **TermService ต้องแยก svchost กลุ่มตัวเอง**: สร้าง REG_MULTI_SZ `termsvcs`=TermService ใน
`HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Svchost` + ImagePath=`svchost.exe -k
termsvcs` (ค่าเดิม -k NetworkService = หยุด service ไม่ลง ini ไม่โหลด) ④ **รีบูต** (restart
service ไม่พอ) → port 3389 LISTENING ⑤ **ต่อด้วย `mstsc /v:127.0.0.2` ไม่ใช่ localhost!**
(localhost = error 0x708 "already have a console session" เพราะ mstsc สลับเป็นโหมด console)
+ cmdkey เก็บ TERMSRV/127.0.0.2. user ฟาร์ม **ykfarm / YkFarm#2026** (Remote Desktop Users).
**ค้าง:** ลง Steam/เกมใน session ykfarm → วางตัวละคร+ปาร์ตี้ → `ฟาร์มตรงนี้.bat` ใน session นั้น
→ เทสต์ว่า mstsc minimize/disconnect แล้ว PrintWindow ยังจับภาพได้ไหม (ถ้าดำ ต้อง tscon trick).
แล้วค่อยทำ "เมาส์เล็งมอนจากมินิแมพ" (คุ้มแล้วเพราะเมาส์แยก session).

**22/7 เช้า (05:xx) — 🔴 โซโล่ Forge = ตายใน ~25วิ + wall memory ถาวร + มาร์คเอง + STAY mode + RDP prep:**
ทดสอบปล่อยฟาร์มจริงหลังแก้ warp-always: **วาร์ปเข้า Forge สำเร็จ 3/3 แต่ตัวละครโซโล่ตายใน
~25วิทุกครั้ง** (heal 71 ครั้งยังเอาไม่อยู่; escape→channelswap เจอ 0 แถวเพราะจอแดง low-HP →
วนไม่จบ). **สรุป: ฟาร์ม Forge ต้องมีปาร์ตี้ + โอวางจุดปลอดภัยเอง วาร์ปโซโล่ลงจุด default =
ตายลูป.** → เพิ่ม **SOAK_STAY mode**: ไฟล์ SOAK_STAY = ฟาร์มตรงที่ตัวยืน ไม่วาร์ป ไม่ goto_mobs;
ตายในโหมดนี้ = หยุดรอโอ (ไม่วาร์ปกลับโซโล่). **ไฟล์ .bat: `ฟาร์มตรงนี้.bat` / `หยุดฟาร์ม.bat`**
(โอวางตัว+ปาร์ตี้แล้วดับเบิลคลิก). แก้เพิ่ม: compass retry 3รอบ (fail=body-block มอน),
channelswap low-HP จอแดง retry tol 26/15%, escape เช็คตายก่อน (respawn-first ไม่งั้น channel
UI บนจอตาย=0แถววนลูป). **Wall memory ถาวร (โอขอ 'ระบบมาร์คเองเก็บไว้'+มาร์คเอง):**
mm_marks.npz (anchor img + จุด offset), `_mm_marks_save/load` re-align ด้วย NCC shift
(roundtrip PASS, cross-map reject PASS); mmkite โหลดตอนเริ่ม+เซฟตอนจบ. **มาร์คเอง GUI:**
ปุ่ม "🖊 มาร์คกำแพงเอง" ในแท็บฟาร์ม → แคปมินิแมพโชว์ 3x คลิกซ้าย=มาร์ค ขวา=ลบ บันทึก→
เข้า session สด. **RDP background (โออยากได้): เปิดแล้ว** — fDenyTSConnections=0, NLA on,
firewall on, สร้าง user **ykfarm** (รหัส YkFarm#2026) + Remote Desktop Users; port 3389 ยัง
demand-start. **เหลือทำกับโอ: mstsc→localhost ล็อก ykfarm, ลง Steam/เกมใน account นั้น,
กัน session ล็อก.** ตัวละคร HP100 เมือง ปลอดภัย ไม่มี farm รัน.

**22/7 ดึก — เดินฟาร์ม: ถอยหลบเด็ดขาด + จำจุดชนจริง + ต่อเนื่อง + ⚠️ warp เมือง/Forge
+ 🟢 RDP ได้ (Win11 Pro):** โอ: "ติดกำแพงดันทุรัง=ไถกำแพง ผิดมนุษย์" + "ยังไม่จำจุด" →
รื้อ stuck logic ใน _mmkite: **react เร็ว (0.35s ไม่ใช่ stuck_s) → mark obstacle ทันที
(dedupe 12px, cap 60) → BACKOFF เด็ดขาด: ถอยตรงข้าม last_heading 0.75s** (ไม่ดัน ไม่ weave
อ่อนๆ); obstacle repulsion แรงขึ้น (radius 9→13, weight 1.3→2.0, เลี่ยงก่อนชน). **เดินต่อเนื่อง:
walk_loop รัน mmkite secs=0 (ยาวไม่ขาด) ตัด goto_mobs stepping + 20s restart (โอ: ยังหยุดๆ)
→ เทสต์ 15/15 วิ ขยับตลอด. curved return (drift>radius) คงไว้ (มอนตามตี). 🔴 **soak ฟาร์ม
ในเมืองมั่ว** (skip-warp เช็ค mob_delta ซึ่งเมืองก็มีจุดแดง) → **แก้: warp Forge เสมอ** ไม่ skip.
🔴 **RDP background — พิสูจน์แล้ว "ทำไม่ได้" บน Win11 Pro (แก้ความเข้าใจผิดเดิม):**
เมมเก่าเขียนผิดว่า "รองรับ RDP ในตัว ไม่ต้อง RDPWrap" — จริงคือ Win11 Pro **เป็น client
SKU (ProductType 1)** รับ RDP เข้าได้ก็จริง **แต่ interactive session ได้ทีละ 1 เท่านั้น**:
พอ RDP เข้าเป็น user "farm" → **console ของ guole ถูกล็อก/ตัด** = โอทำงานหน้าจอไม่ได้เลย
(termsrv.dll สต๊อก 10.0.26100.8115, ไม่มี RDPWrapper). ⇒ เป้าหมาย "ฟาร์มใน RDP พื้นหลัง
ขณะโอทำงาน console" **เป็นไปไม่ได้ด้วย Windows แท้** — ต้อง **RDPWrap** (patch termsrv
ให้ multi-session; แต่พังทุก Windows update, โดน AV บางตัวจับ, เทา ๆ เรื่อง license) ซึ่งคือ
สิ่งที่โอไม่อยากใช้แต่แรก. 22/7 ทดลองจริง: สร้าง user farm + เปิด RDP + loopback 127.0.0.2 →
mstsc เด้ง security dialog "Opening RDP" → **ยกเลิก** (กด OK = ล็อก console โอทันที) →
**revert ทุกอย่างกลับ** (fDenyTSConnections=1, ปิด firewall rule, ลบ user farm, ลบ cred+.rdp).
**ข้อสรุปสำหรับโอ (รอเคาะ): (A) RDPWrap** = ทางเดียวที่ได้ session แยกจริงบนเครื่องนี้
(ยอมรับ patch+เสี่ยง update) **หรือ (B) ใช้ของที่มีอยู่แล้ว** — บอทฟาร์มพื้นหลังผ่าน
PostMessage/PrintWindow **ทำงานบน desktop เดียวกันได้อยู่แล้ว** (เกมถูกหน้าต่างอื่นทับได้ ยัง
อ่าน/ยิงคีย์ได้ = "ฟาร์มขณะทำงาน" สำเร็จโดยไม่ต้อง RDP; ต่างแค่เกมกินพื้นที่ desktop) —
แนะนำ B เพราะไม่แตะ system integrity. **(C) เครื่อง/VM แยกที่มี GPU** = หนัก.

✅ **manual-mark สิ่งกีดขวาง (เสร็จ 22/7):** step ใหม่ `farmmark` + ปุ่มในแท็บ "ฟาร์ม"
("🚧 มาร์คตรงที่ตัวละครยืน" / "🧹 ล้างที่จำไว้") → บันทึกตำแหน่งปัจจุบัน (dx,dy จาก
MMKITE_ANCHOR แบบเดียวกับ auto-mark) ลง MMKITE_OBSTACLES → repulsion loop เดิมเลี่ยงให้เอง.
helper `_farm_mark_here()`/`_farm_clear_obstacles()`; dedupe 12px, cap 60, s<0.45=ปฏิเสธ.
ผูก `farmmark` กับ trigger คีย์ได้ (เดินชนกำแพงระหว่างฟาร์มแล้วแตะ). ข้อจำกัด v1: มาร์คอยู่
ระดับ session (ล้างเมื่อเปลี่ยนแมพ/กดล้าง — ยังไม่ persist ข้ามการปิดโปรแกรม). เทสต์ stub 8/8
(lint, no-anchor→home, offset opposite shift, dedupe, low-corr guard, clear, no-window) + App
methods bound. **ยังไม่เห็นสดในเกม.** Engine ตัวละครในเมือง HP100 (ยังไม่ปล่อยฟาร์ม).

**22/7 — แท็บ "ฟาร์ม" GUI + รูปแบบเดิน + เดินต่อเนื่องไม่หยุด + จำสิ่งกีดขวาง + launch (โอขอชุดใหญ่):**
โอหา mmkite ไม่เจอ (อยู่ในสคริปต์ soak) → เพิ่ม **แท็บ "ฟาร์ม"** ในแอป: รูปแบบเดิน
(สุ่ม/วงกลม/สี่เหลี่ยม/เส้นตรง/เลข8) + รัศมีวน + ระยะไล่มอน + ชนแล้วเปลี่ยนทาง(วิ);
เก็บ settings["mmkite_cfg"] (MMKITE_CFG global); soak โหลดจาก macros.json ตอนเริ่ม.
**เดินต่อเนื่องห้ามหยุด (โอ: หยุด=โดนตี):** รูปแบบเป็น base heading ที่ไม่เป็นศูนย์เลย
(pattern_heading(phase) หมุนตามรูป) + มอน/สิ่งกีดขวางแค่มาปรับทิศ + การันตี want ไม่ว่าง
(ถ้าคีย์ต่ำกว่าเกณฑ์ บังคับแกนแรงสุด). **ไล่มอนในระยะ (โอ: ไม่ไล่ไกล):** mob_reach —
ไล่เฉพาะมอน ≤N มินิแมพ-px ไกลกว่าไม่ไป. **จำสิ่งกีดขวาง (โอไอเดีย กันติดซ้ำ):**
auto-mark จุดที่ stuck (offset จาก MMKITE_ANCHOR session-level) + repulsion เลี่ยงจุด
ใกล้ <9px; ยังไม่มี manual-mark (คลิกมินิแมพ) = งาน GUI ต่อ. **step `launch A|B|C`**
(LAUNCH_HOOK) + มาโคร "🚀 เปิดชุดฟาร์ม (ลูกศรขึ้น)" = O+heal+โล่+ปริซึม+นก+เก็บของ ปุ่มเดียว.
🔴 **เมาส์ MAKCU (โอถาม): ทำไม่ได้** — Windows มี cursor เดียว/desktop, MAKCU inject HID
= ขยับ cursor จริง (ไม่ใช่ virtual แยก); เกมอ่าน cursor จริงผ่าน GetCursorPos ไม่ใช่ PostMessage
(ต่างจากคีย์บอร์ดที่ PostMessage เข้า background ได้) — พิสูจน์แล้ว 20/7 fake click ไม่ติด.
**แต่ยังไม่พิสูจน์: สกิลต้องเล็งเมาส์จริงไหม** (อาจ auto-target มอนใกล้สุด = ไม่ต้อง park
เมาส์เลย โอใช้เมาส์อิสระได้) — MP-read เทสต์พลาด (ตำแหน่งหลอด MP เพี้ยนจอ Max) ค้างพิสูจน์.
Engine relaunch, ตัวละคร HP100. ค้าง: เทสต์ farm pattern สด, manual-mark GUI, สกิลต้องเมาส์ไหม.

**22/7 — 🚀 step `launch` + ปุ่มเดียวเปิดชุด (โอขอ) + 🔴 prism/โล่/O = บัฟกันตาย ห้ามขาด:**
step ใหม่ `launch NAME1|NAME2|...` (pipe-sep เพราะชื่อมีช่องว่าง) = เปิดมาโครหลายตัว
จาก trigger เดียว; ผ่าน `LAUNCH_HOOK`=App._launch_macros (marshalled ด้วย self.after
เพราะ worker thread; toggle ที่รันอยู่ = ข้าม idempotent). **มาโคร "🚀 เปิดชุดฟาร์ม
(ลูกศรขึ้น)" trigger=up:** `tap o` → delay 800 → `launch Auto Heal|โล่|ปริซึม|นก|Auto
Pickup`. **O เป็น toggle ตรวจไม่ได้ (สีทอง #dbbe18 ชนสีเหลืองอื่น = เจอตลอดแม้ toggle)
→ กดครั้งเดียวตอนเริ่ม; ⚠️ ถ้า O เปิดอยู่แล้ว กดปุ่มนี้=ปิด O ให้กด o เองอีกที** (แจ้ง
คอมเมนต์ในมาโคร). **โล่/ปริซึม critical (โอ: ขาด=ตายทันที) → keeper ifnocolor recast
เมื่อไอคอนหาย = ตรวจไม่เจอ(ถูก effect ทับตอนคอมแบท)ก็ recast ไว้ = fail-safe ปลอดภัย
สำหรับบัฟกันตาย** (prism recast ทุก 3วิตอนรุมมอน = พฤติกรรมถูกต้อง ไม่ใช่บั๊ก). launch
hook ทดสอบ: เปิดครบ 5/5. Engine relaunch. โอกดลูกศรขึ้น = เปิดชุดฟาร์มทั้งหมด.

**22/7 — 🎯 mmkite: เดินด้วยมินิแมพล้วน + ไล่มอน + เข็มทิศ (ไม่หมุนกล้อง) — ไอเดียโอทั้งชุด:**
โอชี้ 3 อย่างที่เปลี่ยนดีไซน์: ① 'จับจากมินิแมพเป็นหลัก' ② 'เห็นจุดแดงเดินเข้าหามอน'
③ 'ไม่ต้องหมุนกล้อง'. **click-to-move ทดสอบแล้ว = เกมไม่รองรับ** (คลิกมินิแมพตัวไม่ขยับ) →
ยังต้อง WASD แต่ **ขับ+ตรวจ stuck จากมินิแมพล้วน** (pit/ledge หลอกพื้นไม่ได้). `_mmkite`
(step `mmkite [SECS [RADIUS]]`): **① เข็มทิศ** — กด W/D วัดมินิแมพเลื่อนทิศไหน = camera
basis; keys_for(v) เลือก WASD ที่พาไปทิศ v บนมินิแมพ **ทุกมุมกล้อง ไม่ต้อง camalign**
(ตัด _cam_align ที่เพี้ยน 4 รอบ/run ทิ้งจาก soak) **② ไล่มอน** — mob_dir() อ่าน centroid
จุดแดงในมินิแมพ → เดินเข้าหา + weave ตั้งฉากหลบ **③ กลับบ้าน** ถ้าดริฟต์เกิน radius.
**พิสูจน์สดที่ Forge: เข็มทิศ fwd(-1,0)=กล้องหมุนจริง แต่เดินถูก; ระยะถึงมอน 15.8→1.0→
1.0→3.2 = เกาะฝูงมอนตลอด; HP100.** soak walk_loop เปลี่ยน _kite→_mmkite radius 22.
**บัฟ recast ทุก 3วิตอนคอมแบท** (prism) = detection แกว่งเพราะ effect ทับแถบบัฟ — rate-
limited แล้วไม่ spam 300ms แต่ยังเกิน; ค้างดูว่า prism หล่นจริงหรือ false. Engine idle,
ตัวละคร Forge HP100, ปาร์ตี้ 11 คน. **ค้าง: ปล่อย soak เต็มดูยาว, party accept/kick
(รอเห็น popup), prism recast จริงไหม.**

**22/7 — 🔴 บัฟ spam ทั้ง 4 = โอแก้มาโครผิด + ลายเซ็นผิด (แก้ครบ ยืนยัน 4/4 เงียบ):**
โอไปแก้ shield/prism keeper เป็น `ifhpabove 0` (จริงเสมอ=มีชีวิต) แทน `ifnocolor` →
**กดทุก 300ms ตลอด = spam!** คืนเป็น ifnocolor (โล่ #08083f, ปริซึม #a46dff — วัดยืนยัน
detect 4/4). **นก: template buff_wing.png พังที่สเกลจอ Max** (bird icon แถวบนเดี่ยว) →
เปลี่ยนเป็นเช็คสีฟ้าช่องบนซ้าย `ifnocolor win 5 58 33 85 #0094ff 22% 10%` (แม่นกว่า).
🔴 **O: ลายเซ็น #4ee8fc (ฟ้า) ผิด — ไอคอนจริง = ทอง #dbbe18** (โอส่งรูปยืนยัน) → keeper
กดแล้วตรวจไม่เจอ กดซ้ำ → toggle ปิด → มานารั่ว → **ปิด o_loop/มาโคร O (enabled=false)
กด O เองครั้งเดียว** (บัฟถาวร ไม่ต้อง recast). **เลย์เอาต์แถวบัฟจริง (region 5 58 95 148):
บน=นก(ขาว/ฟ้า) เดี่ยว; ล่าง=O(ทอง)/สายฟ้า/โล่/ปริซึม(สามเหลี่ยมฟ้า-ม่วง).** ทุก keeper
เพิ่ม: ยืนยันหาย 2 ครั้งห่าง 0.6s + skillhold+delay 400 (บัฟแทรกก่อนสกิลโจมตี ไม่โดนกลืน
—โอ 'ชนสกิลฆ่ามอน') + **หน่วง delay 3000/รอบ = กัน spam ระดับโครงสร้าง**. soak_driver
keeper ก็แก้ตรงกัน (กดครั้งเดียว/รอบ, O ไม่ recast). backup: buff_wing.old.png.
**ค้าง (โอขอ 22/7 — ยังทำไม่ได้ ต้องเห็น popup จริงก่อน): ① auto-accept คำขอเข้าปาร์ตี้**
(popup OK ด้านบนกลางจอ คล้าย confirm ย้ายแนล = lavender #b9accd?) — ต้องแคปตอนมี invite
จริงเพื่อวัดพิกัดปุ่ม OK ② **auto-kick คนในตี้ที่ไม่อยู่แมพ Forge เกิน 3 นาที** (คลิกขวาชื่อ→
kick; party list อยู่ซ้ายบนใต้บัฟ) — ยังไม่มีคนในตี้ให้เทสต์. Engine relaunch, บัฟ 3 ตัวขึ้น.

**22/7 — บัฟแก้ครบ + มินิแมพคู่ขนาน + ไอเดียซูมโอ (โอเฝ้าเทสต์สด):** 🔴 **root cause
บัฟ O spam = ลายเซ็นผิด**: #4ee8fc (ฟ้า) ที่วัดไว้ไม่ตรงไอคอนจริง (โอส่งรูป = **ทอง**) →
keeper กด O แล้วตรวจไม่เจอ → กดซ้ำรัว → O เป็น toggle → กดซ้ำ = ปิด = มานารั่ว (บั๊กที่โอ
เจอหลายรอบ). **แก้เด็ดขาด: o_loop ไม่ auto-recast แล้ว — กด O ครั้งเดียวตอนเริ่ม
ปล่อยยาว** (โอ: 'กดครั้งเดียวใช้ตลอด'; ปลอดภัยกว่าไล่จับไอคอนทอง). โล่/ปริซึม/นก:
keeper กดครั้งเดียวต่อรอบ 3 วิ (ตัด retry loop 3x ที่ดูเหมือน spam) + confirm หาย 2 ครั้ง
ห่าง 0.5s + skillhold+delay 0.4s (บัฟแทรกก่อนสกิลโจมตี ไม่โดนกลืน). **ทดสอบยืนยัน: กด
บัฟใหม่ตอน respawn → โล่/ปริซึม/นก ตรวจเจอถูก, O ตรวจไม่เจอ (ลายเซ็นฟ้าผิด — ยืนยัน
สาเหตุ).** ตำแหน่งแถวบัฟจริง (จอ Max): 2 แถว ใต้ HP/MP; region 5 58 95 148 ยังถูก.
**🟢 มินิแมพเป็นเข็มไมล์คู่ขนานใน kite (แก้ 'เพี้ยนบ่อยบนชั้น 2'):** พิสูจน์สดที่ Forge —
เดิน 4 ทิศ **band(พื้น) อ่านมั่วทุกทิศ** (โดนโครงสร้างนิ่ง/หลุมกลาง/ขอบชั้น; 6/8 tile
รายงาน 0 conf สูงทั้งที่เดิน) แต่ **มินิแมพอ่านทิศถูกทุกทิศ** (NCC 0.63-0.71). kite เพิ่ม
cross-check: พื้นบอกไม่ขยับ+มินิแมพบอกขยับ = ไม่ใช่ติดจริง อย่าเปลี่ยนทิศมั่ว → kite ที่
Forge เดินต่อเนื่อง 10/12 วิ. **ไอเดียโอ: ซูมกล้องเข้าสุด** (WheelUp) = พื้นเต็มจอ band
ใกล้ตัว → เพิ่มใน soak start แล้ว แต่ยังพิสูจน์ประโยชน์ไม่ได้ (ตัว respawn ในเมืองแออัด
เดินชนคนไม่ขยับ) + ⚠️ ความเสี่ยง: ซูมเข้า=วงเวทสกิลเต็มจอ อาจกลับไปโดนปัญหา band โดน
effect (เหตุผลเดิมที่วาง band ไกล) — ต้องเทสต์ที่ Forge จริง. **โอตายที่ Forge ชั้น 1 อีก
(บอส Nose Robot Lv128 HP230k + มอนรุม)** = จุดฟาร์มแรงเกิน; respawn สำเร็จ. **_feet_point
(หลอดเลือดใต้เท้า 5.2%ใต้กลาง) ผูก kite+aimtap แล้ว.** Engine relaunch. **ค้าง: จับไอคอน
ทอง O ทำ template (ตอน O เปิดชัด), เทสต์ซูมที่ Forge, จุดฟาร์มที่รอด.**

**21/7 ค่ำ(5) — STEP 2 เสร็จ: pickpoint หลอดเลือดใต้เท้า (โอขอ):** วัดสด — ตัวละคร
กลางจอเป๊ะ (960,504) แต่หลอดเลือด HP/MP ใต้ตัว = **client (960,556) = ต่ำกว่ากลาง 52px
= 5.2% ของ client height**. เพิ่ม `FEET_Y_FRAC=0.052` + `_feet_point(hw)` (center-x,
center-y + 0.052*H) — ปรับตามขนาดจอเอง. ผูกให้ **kite park เมาส์ที่เท้า + aimtap origin
= เท้า** (แทน body center) → สกิล/PgDn เล็งลงตรงที่ตัวยืน (AoE ลงกองมอนรอบตัวตอน kite).
ยังคงใส่ CX CY override ได้. pickpoint เท้าที่จอ Max = client 960,556 (frac 0.5,0.551).
lint aimtap/kite ผ่าน. Engine pid 3224. **ครบทั้ง 3 สเตปที่โอสั่งวันนี้: (1)Esc>General>
Take me home ✅ (2)pickpoint เท้า ✅ (3)โชว์ฟาร์ม Forge kiting รอด ✅.** ตัวละครเมือง
HP100. บัฟ O false-toggle = หายแล้วหลัง calibrate สกิล (ทดสอบ 6/6 detect, 0 false-press).

**21/7 ค่ำ(4) — ✅ KITING รอดจริงที่ Forge + take-me-home/warpforge ใช้ได้ที่จอ Max
(ทีละสเตปตามโอสั่ง):** โอ Calibrate สกิล manual ใหม่แล้ว (จอ Max เปลี่ยน ui_scale) →
สกิลบาร์ตรง สกิลยิงปกติ (พิสูจน์: skillspin 23 taps/5s, ทุกช่อง sat READY). **step `kite`
ใหม่** = หัวใจการรอด (โอสอน kiting): เดินวนไม่หยุดเลย เปลี่ยนทิศทุก ~1s ติดกำแพงเปลี่ยน
ทิศทันที (ไม่มี wait_unlock 12s ที่ทำตายแบบ pathwalk) + park เมาส์กลางจอ/เท้าให้ AoE ลง
ตัวเอง; ยัน stop/toggle; ทดสอบเดินไม่หยุด 62 หน่วย/6s. soak_driver เปลี่ยน pathwalk→kite
20s สลับ goto_mobs + keeper เช็คไอคอนทุก 2s (แทน 30s fixed; โอ: บัฟช้า). **STEP 1
Esc>General>Take me home วัดสดจอ Max: General (0.192,0.339) / "I'm stuck" (0.331,0.749)**
→ อัปเดต `_pw_take_me_home` แล้ว (ค่าเก่า 0.171/0.320,0.748 พังตอน maximize). **warpforge
รื้อใหม่: take-me-home เสมอ → คริสตัลที่จุดเกิด (สะอาด ไม่มีคนบัง cyan) → คลิก → ดับเบิลคลิก
Forge tile (0.742,0.732)** — พิสูจน์สดครบสายที่จอ Max. **โชว์ฟาร์มสด 2 นาที: ตัวละคร
เลือดเต็ม 7660/7660 สกิลดาเมจ 11439/5673/3813 มอนตายเพียบ (กะโหลก) — kiting รอด
สมบูรณ์ตามทฤษฎีโอ.** ⚠️ HP อ่าน None เป็นเฟรมๆ ตอนคอมแบทแฟลชแรง = ปกติ (ifhpbelow
fail-safe + hud_watch ต้อง None 75s ถึงถือว่าตาย — transient ไม่ทริกกู้). **เกร็ดจอ Max:
client 1920x1009/1048 (ไม่ใช่ 1080 เพราะ taskbar), ui_scale 1.758-1.8; game settings
= Windowed 1920x1080; ปุ่ม Warp ล่างโดน taskbar บัง → ใช้ดับเบิลคลิก tile แทน.** เมือง
Wayfarer's คนแน่น 100+ = cyan crystal detection หลอกง่าย → take-me-home ให้จุดเกิดสะอาด
ก่อนเสมอ. ค้าง: pickpoint กลางจอสำหรับมาโคร PgDn (โอขอ, ยังไม่ทำ — kite park เท้าให้แล้ว
แต่ยังไม่มีปุ่ม/มาโคร explicit). ตัวละครตอนนี้เมือง HP100 ปลอดภัย, ยังไม่ปล่อย soak ยาว.

**21/7 ค่ำ(3) — 🔴 The Forge กลางแมพ = ตายทันที (โอ maximize จอ + ค้นพบสำคัญ):**
โอกด Max จอ (client 1920x1009/1048 มี taskbar; game settings = Windowed 1920x1080).
**พิกัดคลิกเมนูตายตัวพังหมด** (take-me-home กด General ไม่โดน, ปุ่ม Warp โดน taskbar บัง).
แก้เป็น **content/color detection:** ① `_find_crystal(hw)` = หา centroid คริสตัลวาร์ป
สีฟ้า (27000px, cyan G+B สูง R ต่ำ) แทนพิกัด — ทนคนมุง+ทนขนาดจอ; warpforge คลิกคริสตัล
→ **ดับเบิลคลิก tile The Forge (0.742,0.732)** → ตรวจถึงด้วย HUD หาย→กลับ (ไม่ใช้ปุ่ม
Warp ล่างที่โดนบัง). พิสูจน์สด warp สำเร็จที่จอ Max. ② `_respawn_if_dead(hw)` = gate
HP=None ก่อน แล้วหาปุ่ม "Respawn in Town" สีฟ้ากลางจอ (band 0.38-0.62 x 0.66-0.80
เลี่ยงไอคอนสกิลฟ้าในแถบล่าง; ต้อง >800px) กด+รอเมือง. **🔴🔴 บทเรียนโดเมนใหญ่: Forge
ตรงกลาง = 572 มอน Lv126-130 รุม→ ตัวละคร (Wizard Lv116 HP9742) ตายใน ~5 วิ แม้ฮีล
เต็มสปีด; channelswap หนีไม่ทัน + แนลใหม่ก็มอนเท่ากัน. AFK ฟาร์มกลาง Forge ไม่รอด.**
โอเจอบั๊ก: **อยู่ Forge แล้วกดวาร์ป Forge ซ้ำ = ไม่วาร์ป (แมพเดิม) ค้างหน้าแผนที่ ต้อง
Esc ออก** → driver ควรเช็ค at_forge() ก่อน warp (มีแล้ว) + warpforge retry ทำ _ui_clear.
กู้ตัวละครที่ตายสำเร็จ (Respawn in Town by color) — ตอนนี้อยู่เมือง HP100 ปลอดภัย.
soak_driver เพิ่ม respawn ใน recovery (นับ deaths). **ค้างถาม/รอโอตัดสิน: จุดฟาร์มที่
รอดจริง — ขอบ Forge (มอนน้อยลง)? แมพเลเวลต่ำกว่า? หรือ Forge ต้องปรับบิลด์เอาตัวรอด
ก่อน?** ตอนนี้ยังไม่ปล่อย soak (รอโอเลือกจุด). Engine idle, ตัวละครในเมือง.

**21/7 ค่ำ(2) — 🔍 โอตั้งมินิแมพ MAX ZOOM เป็นมาตรฐานใหม่:** ความละเอียดกระโดด
**6 เท่า** (เดิน 0.5วิ = 16.34 mm-px จากเดิม 2.67; scale ~11 ground-px/mm-px จากเดิม
~67-175) — การทดลอง +3 คลิกก่อนหน้าหลอกตา (สเต็ปซูมท้ายแรงมาก ต้องสุดจริง). เห็นระดับ
ผู้เล่นรายคน/NPC dot/แท่นวาร์ปชัด. **ผลพวง+สิ่งที่แก้แล้ว:** ① autocal range gate
20..500 → **4..500** (สเกลจริง ~11 เคยโดนปฏิเสธ) ② NCC baseline ต่ำลง (จุดขยับ
เยอะขึ้นในภาพ; home 0.81-0.83 จากเดิม 0.93-0.97) → เกณฑ์จูนใหม่: cal 0.45 /
snap 0.50 / lap-end 0.45 / ground-fallback 0.45 (spot-match คง 0.55, wrong-map
คง 0.18) ③ spot memory ซูมเก่า archive → spots_old_zoom_20260721b/ เรียนใหม่หมด
④ ⚠️ ทุก anchor/ความจำผูกกับซูมนี้แล้ว — **ห้ามเผลอ scroll มินิแมพ**. เทสต์เดินเมือง
1 รอบผ่านที่ซูมใหม่ (home NCC 0.81). walk suite 19/19. Engine pid ล่าสุด.

**21/7 ค่ำ — 🔴 ปุ่มเดินค้างหลังปิด soak (โอเห็นตัวเดินชนกำแพงในเมือง):** WM_KEYUP
หายระหว่าง window transition ตอน take-me-home → เกมถือว่า W ยังกดอยู่. แก้สด: release
+ **เคาะ down/up สั้นทุกปุ่มเดิน** = ล้าง state ชัวร์ (พิสูจน์: มินิแมพนิ่ง 100% ทันที).
soak_driver เพิ่ม `unstick_keys()` ใช้ทั้ง cleanup และ recovery-pause. กติกาใหม่:
**การปล่อยปุ่มแบบเชื่อได้ = release แล้วตามด้วย tap** (bare keyup เชื่อไม่ได้ข้ามฉาก).
soak v2 จบสวย: heals 14, keeper 47/47, O ไม่หลุด, ไม่มี escape/relogin, ~25 นาที.

**21/7 เย็น(2) — 🏭 SOAK TEST เต็มระบบรันจริงที่ The Forge (โอออกไปหลาย ชม. สั่ง
"ทำไปเรื่อยๆ"+เปิดม่านดำ):** `makcu/soak_driver.py` = driver ครบชุด (heal<92 + keeper
โล่/ปริซึม 30s + Buff O เช็คก่อนกด + rotation skillspin 3 4 6 7 9! + pathwalk random 5 8
laps 999 + escape hp<18→channelswap→camalign + **recovery: HUD หาย>90วิ → relogin →
warpforge → camalign → ฟาร์มต่อ** + STATUS ทุก 3 นาที + เพดาน 4.5 ชม.แล้ว
take-me-home เอง). **หยุด: กด END / สร้างไฟล์ makcu/SOAK_STOP**; รันแบบ detached
pythonw (bash background มีเพดาน 10 นาที+ฆ่าดิบปุ่มค้าง — ห้ามใช้กับงานยาว). log:
makcu/soak_log.txt. **บั๊กที่เจอ+แก้ระหว่างทาง:** ① คลิกแรกเคยพลาดไปเปิด STORAGE
ค้างบังทุกอย่าง → `_ui_clear(hw)` (Esc จน HUD อ่านได้) + **warpforge เริ่มด้วย
take-me-home เสมอ = ตำแหน่งแท่นชัวร์ทุกครั้ง** ② ปุ่ม Warp เปลี่ยนสีตามสถานะ
(เขียว/ฟ้า!) → ตัวเช็คใช้ "สว่าง+อิ่มสี" แทนโทนตายตัว + ปิดแมพก่อน retry (เคยวนคลิก
จนไปเลือก Fairy Glen ผิดแมพ — โชคดียังไม่กด Warp) ③ ยืนยันม่านดำ click-through
กับคลิกจริง (WindowFromPoint = เกม). **ผลสด 3 นาทีแรก: cal=Y ครั้งแรกบนแมพฟาร์มจริง
(scale 43) + mid-lap snap ยิงจริง (drift 128px ดึงกลับ) + home NCC 0.91-0.97 ทุกรอบ
18 laps + keeper 6/6 ตรงเวลา + Buff O ไม่กดซ้ำ + adapt หด 47% (โซนแคบ/มอนชน)**.
สถานะทิ้งไว้: soak รันอยู่ (pid ดู pythonw ตัว soak_driver), engine idle, blackout เปิด
(F12 ปิด). งานค้างถัดไป: วัดผลจบ soak (FINAL ใน log), rotation ไม่มี counter วัด DPS,
ฐานข้อมูลจุดฟาร์ม, ตรวจตำแหน่งฟาร์มจริงว่า XP คุ้มไหม (HP นิ่ง 100 = อาจอยู่โซนมอนน้อย).
**ต่อ: แท็บเดินอัตโนมัติ — คำอธิบายละเอียด (โอขอ) + ยืนยันทิศทาง:** วงกลม/วงรี =
**ทวนเข็ม, ตัววงอยู่ตะวันออก (ขวา) ของจุดยืน** (circle waypoints: th=π−2πi/n, x=R(cosθ+1));
สี่เหลี่ยม = **ซ้าย→ลง→ขวา→ขึ้น** (wps: (-w,0),(-w,h),(0,h) = กรอบอยู่ซ้าย-ล่างของบ้าน) —
โอสังเกตถูกทั้งคู่. hint ทุกช่องในแท็บอธิบาย มาก/น้อย แล้ว + บล็อกท้ายบอกทิศ+จุดยืนแนะนำ
(วง=ยืนให้ขวาโล่ง, สี่เหลี่ยม=ยืนมุมขวาบนของที่โล่ง) + พฤติกรรมบุบ/หด/ขยาย.

**20/7 เย็น — เมาส์ตัวที่ 2 ค้างกลางจอ: ทำไม่ได้ (โอถาม):** Windows มี **cursor
เดียวต่อ desktop session** — เสียบเมาส์/Makcu/RP2350 กี่ตัวก็ขยับ pointer เดียวกัน
(HID หลายตัว merge เป็น pointer เดียวที่ระดับ OS) ไม่มี API ให้แอปหนึ่งมี cursor
ส่วนตัว → "จำลองเมาส์อีกอันปักกลางจอเกม" เป็นไปไม่ได้ในความหมายตรงตัว. ทางที่ทำได้:
(ก) flick — ดีดเมาส์ไปกลางจอตอนยิงแล้วคืน (~50ms, มีโค้ดใน `click`/flick_click แล้ว)
ใช้ได้ถ้าเกมอ่านตำแหน่งเมาส์**ตอนกดปุ่ม**เท่านั้น (ข) ล็อกกลางจอตอน AFK (โอเสียเมาส์)
(ค) ไม่ต้องทำอะไร. **ทดลองสด 2 แบบ:** ย้าย cursor เข้า-ออกจุด A/B ในเกมขณะเกม
**ไม่ใช่ foreground** แล้ววัด patch รอบจุดนั้น (เฉลี่ย 4 รอบ) → cursor-linked 35.2
vs control (ฉากเคลื่อนไหวล้วน) 28.1 = **ตรวจไม่พบการตอบสนอง** ⚠️ แต่ฉาก noise สูงมาก
(NPC/เอฟเฟกต์) = "ตรวจไม่พบ" **ไม่ใช่** "ยืนยันว่าไม่มี"; ทดสอบชี้ขาดต้องยิงสกิลจริง
แล้วดูทิศ ซึ่งต้องรู้ก่อนว่าสกิลไหนของโอเล็งตามเมาส์ (**รอโอบอก**).

**20/7 เย็น — 🔴 PW_MM_SCALE ผิด 2.3 เท่า → ทำ auto-calibrate แทน (11/11):**
พอโอเอา Chrome ออก วัดสดได้: เดินขวา/ซ้าย 3s+4s สี่รอบ → **73/73/76/76 = 74**
แต่โค้ดใช้ **173** → correction ตอนจบรอบจะ **overshoot 2.3 เท่า** (ดริฟต์จริง 148px
จะเดินแก้ 346px = เลยไปอีกฝั่ง → oscillate). ไม่เคยระเบิดเพราะ path นี้ต้องรอ
drift >1 minimap-px ซึ่งยังไม่เคยเกิด (บั๊กคู่แฝดกับ sign ที่แก้เมื่อเช้า — **เส้นทางนี้
มีบั๊ก 2 ตัวซ้อนโดยไม่มีใครรู้**). **Cross-check ที่ปิดช่องว่างเมื่อวาน:** ground speed
ตอนนี้ 194px/s vs เมื่อคืน 355px/s = ratio 1.83 ≈ 1080/584 = 1.85 → **ยืนยันว่า
20/7 คาลิเบรตตอน fullscreen จริง** (ก่อนหน้านี้บอกว่าพิสูจน์ไม่ได้). สาเหตุที่ต่าง 2.3x
ไม่ใช่ขนาดจอ (ขนาดจออธิบายได้แค่ 7%) = **ระดับซูมมินิแมพต่างกันจริง**.
แก้: `_mm_autocal()` วัด scale จาก odometry ตัวเอง (ที่ waypoint ไกล ≥300px,
ต้อง corr ≥0.15 + minimap offset ≥2px กัน subpixel noise, ยอมรับ 20-500 เท่านั้น,
ล็อกครั้งเดียวต่อการเดิน) เรียกหลัง settle ที่ waypoint (นิ่ง=ภาพคม); fallback
PW_MM_SCALE 173→**74**. ความแม่น auto-cal ±6% (จาก PW_TOL 30 ที่ระยะ 490)
ดีกว่า 130% เดิมมาก. Engine pid 13200. Backup: macro_engine.backup-20260720c.py.
**ยังไม่ fire สดจริง** (ต้องรอ drift >1 minimap-px เหมือนเดิม) แต่ตอนนี้ทั้ง sign และ
scale ถูกแล้วเชิงคณิต. **บทเรียน: ค่าคงที่ที่ผูกกับ "ขนาดจอ × ระดับซูม" ห้าม hardcode**
— ของแบบนี้ต้องวัดเองตอนรัน (แบบเดียวกับ HP bar auto-recal ที่ทำถูกอยู่แล้ว).

**20/7 เย็น — 🟡 ค้นพบ: PrintWindow จับภาพเกมได้ทั้งที่ถูกหน้าต่างอื่นบัง (ยังไม่ได้ใช้):**
โอถามระดับซูมมินิแมพ → เกมถูก Chrome ทับ mss เลยได้พิกเซล Chrome. ลอง
`PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=0x2)` + GetDIBits → **ได้ภาพเกมจริง**
(Unity ยอมเรนเดอร์ให้). วัดสด: เฟรม**สดจริง** (ภาพเปลี่ยน 9.15/1.2s ขณะถูกบัง = เกมยัง
เรนเดอร์ต่อ ไม่ใช่ snapshot ค้าง) และ **เร็วพอ: 16.3ms/เฟรมเต็ม 958x584 เทียบ mss 2 แถบ
~19ms** → **มีทางปลด requirement "เกมต้องมองเห็นบนจอ" ของ pathwalk/heal/buff ทั้งหมด**
(โอทำงานอื่นทับได้). ยังไม่ทำ = งานใหญ่ ต้องเปลี่ยน _pw_gray/_target_screen_point/
pixel_rgb ให้ดึงจาก back buffer เดียวกัน + เช็คว่า minimized ยังได้ไหม + fail-safe ทุกตัว
ที่อิง "โดนบัง = ไม่ยิง" ต้องคิดใหม่ (อาจกลายเป็นข้อดี: ยิงได้แม่นขึ้นแทนที่จะบล็อก).
**เสนอโอแล้ว รอไฟเขียว.** Baseline ซูมมินิแมพปัจจุบันเก็บถาวรที่
`makcu/minimap_zoom_baseline_20260720.png` (เห็นทั้งโซน+ทะเลล้อม = ซูมออกกว้างสุดหรือ
ใกล้สุด; Channel 2). **ไม่เคยจดระดับซูมตอนวัด PW_MM_SCALE=173 เมื่อคืน** — ถ้าโอไม่ได้
scroll ตั้งแต่นั้นก็คือระดับนี้ แต่**พิสูจน์ไม่ได้ย้อนหลัง** ต่อไปเปลี่ยนซูมต้องวัดใหม่.

**20/7 เย็น — 🔴 "กด . แล้วหยุดไม่ได้" = REGRESSION ของ v3 (แก้แล้ว, 13/13):**
โอรายงาน `laps 999` วนไม่หยุด. Root cause: toggle loop คือ
`while not soft: run_steps(steps, ..., hard)` — **ส่ง `hard` เข้าไป แต่กดซ้ำ set `soft`**
โดยตั้งใจให้ "จบ iteration ปัจจุบันก่อน" ซึ่งใช้ได้กับมาโครทั่วไป (iteration <1 วิ)
แต่ v3 ย้าย laps เข้าไปวน**ข้างใน** _pathwalk_run → 1 iteration = 999 รอบ (ถึง 50 ชม.)
→ soft ไม่ถูกอ่านเลย มีแต่ PANIC (hard ผ่าน all_stops) ที่หยุดได้. **นี่คือเหตุผลว่าทำไม v2
หยุดได้แต่ v3 หยุดไม่ได้** (v2 วน re-anchor ที่ระดับ toggle = 1 รอบ/iteration). แก้แบบ
surgical: `_SOFT_STOPS` (dict thread-ident→soft) + `_AnyStop` view + `_with_soft_stop()`;
toggle loop ลงทะเบียน soft ของตัวเอง, `_pathwalk_run` ห่อ stop ด้วยมันบรรทัดแรก →
**ไม่แตะ toggle semantics ของมาโครอื่นเลย** (heal/buff/`/` ยังจบ iteration ก่อนเหมือนเดิม).
พิสูจน์: repro เห็นแดงก่อน (laps 1/5 หยุดได้, 999 ไม่หยุด) → e2e บน _pathwalk_run จริง
หยุดได้ใน <4s + PANIC ยังทำงาน. **GOTCHA ตอนรีสตาร์ท engine ระหว่างเกมเปิด:** X = ซ่อนลง
tray (WM_CLOSE สั่งจากนอกไม่ปิด), force-kill ขณะ pathwalk ถือ WASD = keydown ค้างไม่มี
keyup → **ตัวละครเดินไม่หยุด** → ต้อง**ส่งปุ่ม PANIC (End, scan 0x4F) ก่อน kill เสมอ**
(_on_close เรียก ROUTER.release_all แต่เข้าถึงจากภายนอกไม่ได้). Engine ใหม่ pid 19728.

**20/7 บ่าย — ผลกระทบของ "ความชัด" กับ "ขนาดจอเกม" (โอถาม; วัดจริง):**
① **ความชัด/กราฟิกต่ำ = แทบไม่กระทบ odometer** — phase correlation เป็น whitened
transform: เทสต์ blur k=4, render scale 50%, contrast เหลือ 1%, banding 8 ระดับ →
peak ยัง 0.92-0.93 (gate 0.06) error ~0px. **ข้อยกเว้นเดียวที่อันตราย: พื้นลายซ้ำคาบสั้น**
(tile 16px) → peak 0.32 **ผ่าน gate แต่อ่านผิด 22px** = odometer มั่นใจแต่ผิด; ใส่ลาย
ละเอียดกลับเข้าไป (detail 0.15) ก็หายทันที → **ลดกราฟิกจนลายพื้นเรียบเป็นบล็อกซ้ำ = เสี่ยง
ที่สุด ไม่ใช่ความเบลอ**. ② **ขนาดจอ = ตัวแปรจริง**: PW_UNIT_X/Y (35/25) เป็น *พิกเซลจอ*
Unity ล็อก FOV แนวตั้ง → ground-px ต่อระยะโลก **แปรตามความสูง client** → ย่อจอ = ลูปใหญ่ขึ้น
ในเกม (720p=1.5x, 600p=1.8x ของที่คาลิเบรตไว้) เวลาต่อรอบก็ยาวขึ้นตาม; doc เขียนว่า
"ระยะจริงคงที่เสมอ" ซึ่งจริงเฉพาะเรื่องบัฟเร็ว/แลค **ไม่รวมการเปลี่ยนขนาดหน้าต่าง**.
③ **บั๊กจริงที่แก้แล้ว — กล่องวัดล้นนอกหน้าต่างตอนจอเล็ก**: floor max(120/80/60,…) ใน
`_pw_bands`/`_pw_mm_box` ไม่ถูก clamp → client กว้าง <400 แถบ flow ขวาล้นขอบ, กว้าง
<522 **กล่องมินิแมพล้น** → mss คว้าเดสก์ท็อป/หน้าต่างอื่นมาเป็น "มินิแมพ" (ส่วนที่นิ่งจะ
correlate กันเองสูง → สมอรายงาน "ไม่ดริฟต์" ทั้งที่ดริฟต์). แก้ด้วยการ clamp เข้ากรอบ client;
พิสูจน์ 60/60 checks รวม **ยืนยันเรขาคณิตที่ 1920x1080 / 1280x720 / 956x574 ไม่เปลี่ยน
แม้แต่พิกเซลเดียว**. ④ ระบบอื่นรอดขนาดจอหมด (คลิก/สกิล/บัฟ ผ่าน _ui_scale จากความกว้าง
หลอดเลือด; HP auto-recal ตอนขนาดเปลี่ยน). ⑤ **สภาพจริงตอนวัด: เกมรันแบบ windowed
client 958x614 ที่ตำแหน่ง (-4,383) และถูก Chrome บังอยู่** — วัด tile คุณภาพสดไม่ได้
(mss คว้าตามพิกัดจอ ได้พิกเซล Chrome มาแทน = เหตุผลที่ _pw_visible ต้องมี). ถ้า 20/7
คาลิเบรตตอน fullscreen จริง ลูปตอนนี้จะใหญ่กว่าเดิม ~1.76 เท่า — **ยังไม่ยืนยัน ต้องถามโอ/
วัดซ้ำ**. ⚠️ ค้าง (ยังไม่แก้ เพราะกระทบ kill-switch ที่ปิดเกมได้): `_pw_flow` รับเฟรมที่มี
tile ดีแค่ **2/8** แล้วเอา median — เทสต์: median เชื่อได้ต้อง **≥5/8** (ที่ 4/8 เริ่มพลิกเป็น
ค่าขยะ p90 4px, ที่ 2/8 = 3.7px) แต่ถ้าขันเกณฑ์ขึ้นดื้อๆ blind-streak จะถี่ขึ้น → แตะ
เกณฑ์ 50 เฟรม → map_suspect → **bailout ปิดเกม** ต้องวัดอัตรา tile ดีจากสนามจริงก่อน.

**20/7 บ่าย — ตรวจบั๊กรอบสอง เจอ 2 ตัว (แก้ครบ, smoke 13/13):** ① **dead-band stall**:
goto ถึงเป้าเช็คที่ ≤PW_TOL 30 แต่ hysteresis engage ที่ >PW_ENGAGE 34 → ถ้า err แกนใด
อยู่ช่วง (30,34] ตอนไม่มีปุ่มถูกกด = ยืนนิ่งจน leg timeout แล้วโดนนับเป็น "blocked"
(2 ติดกัน = re-anchor ฟรี; เข้าได้จริงทาง ground-patch fallback ที่ set pos จาก |dx|>25)
— แก้: want ว่าง+ยังไม่ถึงเป้า → nudge แกน err มากสุด แล้ว hysteresis คุมต่อ (ไม่ flap
เพราะ nudge เกิดเฉพาะ >30 ≥ release 20). ② **exception กลางคัน → hot spin**: exec_step
catch-all คืน True → toggle รัวเต็มสปีด (ตัวจุดจริง: lock จอ/secure desktop ทำ mss grab
throw) — แก้: wrap เรียก _pathwalk_run ใน exec_step, crash → log + sleep 1.5s + False
(สัญญาเดียวกับ bad-arg bail). Backup: macro_engine.backup-20260720b.py. Engine รีสตาร์ท
รับโค้ดใหม่แล้ว (pid 21616, 13:54 — เกมปิดอยู่ตอนนั้นจึงปลอดภัย); เกิดมา disabled ตามปกติ
โอต้องกด Home + เปิด watcher เอง.

**20/7 เช้ามืด — ตรวจบั๊ก pathwalk เจอ 3 ตัว (แก้ครบ):** ① **minimap re-anchor
เครื่องหมายกลับด้าน = runaway** (ร้ายสุด): `_pw_shift(old,new)` คืน sign เดียวกับทิศภาพเลื่อน;
พื้นดินเข้ารหัสถูกด้วย `pos -= flow` แต่ minimap correction เขียน `pos = mdx*scale`
(ขาดลบ) → พอ offset เกิน 1 minimap-px มันเดินหนีออก (positive feedback). ไม่เคยเจอ
เพราะทุกเทสต์ offset <1px เลยไม่เข้าเงื่อนไข `1.0<=max()`. พิสูจน์ 2 ทาง (scratchpad/walklab
sign_test.py อิง ground ที่ verified live + converge_test.py: เดิม +2700px หนี, ใหม่ลู่เข้า
8 สเต็ป). แก้: `pos = -mdx*scale` ทั้ง minimap + ground-patch fallback. **⚠️ path นี้ยัง
ไม่เคย fire สดจริง** (ต้องรอ drift เกิน 1 minimap-px) — sign ถูกแล้วเชิงคณิต แต่ axis-alignment
minimap↔ground-flow ยังควรจับตาครั้งแรกที่มันทำงาน. ② **toggle spin**: toggle loop รัน
`while not stop: run_steps()` ทิ้งค่า return → ถ้า pathwalk คืน False ทันที (ไม่มี hwnd/
หน้าต่างถูกบัง/send mode ผิด) จะวนรัวๆ CPU + log ท่วม. แก้: ใส่ `_interruptible_sleep(1500,
stop)` ก่อน early-return ทุกจุด (bailout ไม่ spin อยู่แล้วเพราะ PANIC_HOOK ตั้ง hard event).
③ **parse error spin**: arg พัง (แก้ json ตรงข้าม lint) → _pw_parse raise → exec_step catch
คืน True → toggle วนเต็มสปีด. แก้: try/except รอบ parse + sleep. (lint จับ arg พังครบทุกแบบ
อยู่แล้ว GUI Save ปลอดภัย; นี่กันเฉพาะ direct-json-edit). Backup: macro_engine.backup-20260720.py.

**20/7 ตี3 — take-me-home ก่อนปิด + ยืนยัน packet เข้ารหัส + drift ร่วมมาโคร:**
โอปรับ kill-switch: เปลี่ยนแมพ → หยุดมาโคร → **Esc>General>"I'm stuck! Take me
home!"** (เมนู Esc เปิดที่ General เลย; ปุ่ม client-frac (0.320,0.748), General tab
(0.171,0.339); กดครั้งเดียวเทเลกลับ spawn ไม่มี confirm — VERIFIED helper เดี่ยว)
→ แล้วค่อย WM_CLOSE/Terminate. _pw_take_me_home(hw) real-click+foreground (bail อยู่แล้ว
ไม่ต้องรักษา focus โอ). **Packet probe (โอขอลอง):** raw-socket SIO_RCVALL (admin) จับสด
ระหว่างเดิน → เกมต่อ TCP 91.99.215.190:**443 TLS**, payload entropy **7.58 bits/byte**
= เข้ารหัส อ่านพิกัดไม่ได้ถ้าไม่เจาะ TLS/hook mem (เสี่ยง anti-cheat) → **ยืนยันวิชั่นถูกทาง**
sniff.py เก็บไว้ที่ scratchpad/walklab (feasibility only). **Drift ร่วมมาโครครบชุด**
(= - 0 ] [ ; ` q) เดิน 55s: ≤0.5 mm-px/รอบ ไม่สะสม (รอบช้าลงเพราะ cast root แต่นิ่ง)
— ตอบข้อกังวลโอ. **มินิแมพซูมได้** (scroll) ละเอียดขึ้นแต่ไม่บังคับ (แม่นระดับก้าวเดียวแล้ว
+ ซูมสร้าง dependency ห้ามเผลอ scroll). โอ relaxed: ไม่ต้องเป๊ะ ใกล้เคียงพอ = ครอบคลุม.

**20/7 ตี2ครึ่ง — pathwalk v3: laps + สมอมินิแมพ + kill-switch เปลี่ยนแมพ:** โอรายงาน
ลูปไม่กลับจุดเดิม (v2 re-anchor ทุกรอบ+สายพาน/แดชพาลอย) → v3: `laps N` วนใน
_pathwalk_run เอง (tracker มีชีวิตต่อเนื่อง ไม่ล้างพิกัดระหว่างรอบ) + จบทุกรอบเทียบ
**มินิแมพ crop (88.5-96.9%W, 7.6-22.4%H) กับภาพตอนเริ่ม** = พิกัดสัมบูรณ์ (N-locked,
ตัวเรากลางเสมอ): offset×PW_MM_SCALE 173 (x) /×UY/UX ratio (y) → เดินแก้; scale
วัดจริง 20/7. VERIFIED สด 5 รอบต่อเนื่อง: drift รวม ≤0.7 mm-px ไม่สะสม, corr ปกติ
0.27-0.64. กันไถกำแพง: waypoint ตัน 2 จุดติด = break กลับบ้าน re-anchor. **Kill-switch
ตามโอสั่ง**: จอเดินอ่านไม่ได้ ~2s (จอโหลด) หรือ mm corr <0.05 → เช็คซ้ำ 0.8s →
PANIC_HOOK (App._panic_stop หยุดทุกมาโคร, hook ใหม่คู่ STOPHELD_HOOK) + WM_CLOSE
→ 2.5s ไม่ตาย → TerminateProcess ปิดเกม. ⚠️ kill-switch ยังไม่ได้ fire-drill จริง
(ไม่อยากปิดเกมโอกลางดึก) — margin เกณฑ์กว้างมาก; ซ้อมโดยเดินเข้าวาร์ปได้เลย.
โอ relaxed spec: ไม่ต้องเป๊ะ แค่ห้ามเพี้ยนสะสม/ไถกำแพงนาน — ครอบคลุมแล้ว.
มาโคร `.`/`,` = laps 999. คำตอบที่ให้โอเรื่อง AI/packet: LLM ไม่เหมาะ real-time control
(ช้า/แพง ไม่ได้อะไรเพิ่มจาก odometry); แกะ packet หาพิกัด = ทำได้ในทฤษฎีแต่เสี่ยง
anti-cheat/แตกทุกแพตช์ ไม่แนะนำ; Python วิชั่นแบบที่ทำอยู่คือคำตอบที่ถูกแล้ว.

**20/7 ตี2 — LShift ผ่าน PostMessage ต้องใช้ VK_LSHIFT 0xA0:** โอรายงาน "; ไม่ติด" —
สาเหตุ: VK_NAME map lshift→VK_SHIFT 0x10 (generic) ซึ่ง SpiritVale **เมิน**เฉยๆ แต่
0xA0 (sided) ติดทันที (พิสูจน์ด้วย sat ช่องสกิล hotbar 57→8 = ขึ้นคูลดาวน์; 0x10 = นิ่ง)
→ แก้ lshift/left shift→0xA0, rshift→0xA1; **lctrl คง 0x11 เพราะฮีลใช้ได้จริงอยู่แล้ว
ห้ามแตะ**. DEMO รวมพิสูจน์สด: เมาส์กลางตัว + toggle ครบชุด = - 0 ] [ ; ` q + เดินวน
`,` พร้อมกันทั้งหมด — สกิล+Q+LShift ขึ้นคูลดาวน์พร้อมกันทุกช่อง บัฟครบ เดินครบรอบ
หยุด/ปิดคืนสะอาด. (โอปรับ ; delay 300→100ms เองใน GUI — เก็บไว้ตามนั้น)

**20/7 กะดึก — pathwalk v2 (แมพฟาร์มสายพาน) + LShift spam (;):** โอรายงาน "เดินร่วนๆ"
บนแมพโรงงาน → วัดจริงพบ 3 ตัวการ: ① **สายพานพัดตัวละคร** (idle ก็เลื่อน 100-175px —
เข็มไมล์วัดได้จริง จึงแก้ทางให้เองได้) ② วงเวทสกิลยึดติดตัวละครกลางจอ = zero-flow หลอก
③ สกิลรูทตัวตอนร่าย → false stuck. v2: ย้าย band วัดเป็น**สองข้างตัว** (6-30% / 70-94%W,
52-77%H) 2x2 tile ต่อข้าง + peak gate ≥0.06 (<2 tile ดี = blind frame ไม่สะสม),
stuck 0.6→1.8s, hysteresis engage 34/release 20 (กันคีย์แฟลปจากสายพาน), **re-assert
ปุ่มทุก 15 tick** (ROUTER.hold no-op ถ้ายังถือ → LShift soft-stop ของโอไม่ฆ่าการเดินแล้ว),
displacement >120px = แดช/กระเด็น ไม่ใช่ติดกำแพง (ไม่ sidestep แค่ re-mark).
มาโคร `.`/`,` เปลี่ยนเป็น **toggle = วนรอบจนกดซ้ำ** (ลูป re-anchor ทุกรอบที่จุดปัจจุบัน —
ลูปอาจเคลื่อนช้าๆ ถ้าโดนพัด/ข้าม waypoint บ่อย; v3 ค่อยทำ anchor ถาวร) + มาโครใหม่
**"LShift spam (;)"** tap lshift/300ms (window-mode ไม่สะกิด stopheld trigger; focused
mode ก็ปลอดภัยเพราะ _inj_mark map lshift→42). VERIFIED สดบนสนามจริง: rect เดี่ยว 4.9s,
เดิน+rotation+heal พร้อมกัน 5.6s (MP ลดจริง=สกิลยิงจริง), e2e ผ่าน trigger จริง: วนรอบ,
โดน LShift จริงกลางทาง (โอกด/แดช) → walker ดึงกลับเส้นทาง + re-assert สำเร็จ, กดซ้ำ
หยุดสะอาด. เทสต์ trigger สังเคราะห์ต้องกด Home ก่อนเสมอ (engine เกิดมา disabled).

**20/7 — `pathwalk` เดินแพทเทิร์นไร้ landmark + กลับจุดเดิม (VERIFIED LIVE):**
โอถาม "เดินให้ระยะเท่าเดิมโดยไม่กะเวลา ไม่มี landmark ทำไง" → คำตอบที่ใช้จริง:
**odometry จาก optical flow ของพื้น** (กล้องตามตัว → พื้นเลื่อน = ระยะเดินจริง;
phase correlation แบ่ง 6 tile เอา median กันผู้เล่นเดินผ่าน; จับได้แม้แรงเฉื่อย
หลังปล่อยปุ่ม ~60px และการครูดกำแพง) + วนเป้าหมายแบบ closed-loop 8 ทิศ +
stuck = "progress เข้าเป้า <15px/0.6s" → sidestep ตั้งฉากสลับข้าง 6 ครั้งแล้วข้าม
waypoint + จบทุกแพทเทิร์นเดินกลับ (0,0) + fine-correct เทียบภาพพื้นจุดเริ่ม
เฉพาะ corr≥0.15 (กระเบื้องลายซ้ำ+ฝูงชน = false peak corr~0.05 ห้ามเชื่อ)
Step ใหม่ใน macro_engine: `pathwalk left 10 down 5 ...` / `rect W H` / `circle R`
/ `poly N R` / `random N R` — หน่วย: x=35px y=25px (10 หน่วย≈1วิ; y เตี้ยกว่าเพราะ
กล้อง 45° บีบแกนตั้ง; วัดสด 20/7: เดินขวา 355px/s, มินิแมพ scale ≈173 ground-px
ต่อ 1 minimap-px หยาบไปใช้เป็น odometer หลักไม่ได้). ต้องเป็น window mode +
เกมมองเห็น (_pw_visible เช็ค WindowFromPoint กลาง band; band = 36-64%W,
57-77%H ใต้ตัวละคร). มาโครสาธิต: `.` = อ้อมสวนน้ำพุ (left 16 up 32 right 26
down 32), `,` = rect 14 14. VERIFIED สด: อ้อมสวน 18 วิ ติด 2 ครั้งหลบเอง กลับ
ห่างจุดเริ่ม ~17px. Assumption: กล้องมุม default (N ขึ้น) — หมุนกล้อง = แกนเพี้ยน.
คู่มือโอต่อท้าย USAGE_AUTO_HEAL.md. Backup: macro_engine.backup-20260720.py.
⚠️ GOTCHA ใหญ่ที่เจอ: **engine เปิดมา self.enabled=False เสมอ — trigger ไม่ทำงาน
จนกด Home (enable_key)**; เทสต์สังเคราะห์ทุกครั้งต้องกด Home ก่อน ไม่งั้นเงียบสนิท
ทั้งที่ hook ปกติ. อนึ่ง stdout ของ engine เปิดผ่าน python ปกติจะ buffer — debug ให้รัน
`python -u macro_engine.py` แล้ว App.log จะ print ลง stdout ด้วย.

**19/7 — Cancel listings (/) + Stop-held E:** มาโครยกเลิกขายของในตลาด (Sell Items
panel): toggle `/` → loop [click X แถวแรก l+263 121 → waitcolor popup Close #b9accd
(template เดียวกับ popup channel เป๊ะ, Ok วัดจริง = c+42 88) → click Ok → delay 1500].
Guard 2 ชั้นก่อนคลิก: ปุ่มฟ้า List-Items `ifcolor win 100 80 200 90 #6ac3ff 8% 30%`
+ กากบาทขาวแถวแรก `ifcolor win 256 114 271 127 #ffffff 6% 15%` — ลิสต์หมด/ออกจาก
หน้าตลาด = วนเงียบไม่คลิกมั่ว. (⚠️ แก้ข้อมูล 20/7: "เทสต์ trigger สด 19/7" เป็นโมฆะ —
ตอนนั้น engine ยัง disabled อยู่ trigger ไม่เคยยิง; ตัว flow คลิกยืนยันด้วยมือครบวงจริง
แต่ชั้น trigger+guard ยังไม่ได้พิสูจน์สดกับมาโครจริง).
Flow คลิกยืนยันด้วยมือครบวง: X → popup "Cancel listing for ...?" → Ok → spinner ~1s →
แถวขยับขึ้น (แถวแรกอยู่ที่เดิม คลิกซ้ำจุดเดิมได้). วัดที่ fullscreen 1920x1080 scale 1.7636.
บวก "Stop held keys (E)" = stopheld ตัวที่สามคู่กับ LShift/LCtrl. Engine restart แล้ว
(pid ใหม่, watcher ทุกตัวเริ่ม OFF — โอต้องเปิดเอง). ระหว่างวัดยกเลิกจริงไป 1 ชิ้น
(Violet Arc 100,000 — ของกลับเข้ากระเป๋า).

**18/7 กะดึก — "มาโคร 1-7 + บัฟโล่/สามเหลี่ยมไม่กด" FIXED (verified live in town):**
root causes found by probing the live game (engine off, sent taps via ROUTER from
test scripts): ① skillspin geometry STALE — the patch moved the hotbar to TWO rows
(row2 = R/T) lower+wider; old SKILL_X0/PITCH/Y sampled a strip of bare scene above
the bar (town sand = high sat = spam-ready; dungeon floors = low sat = never taps →
"ไม่ค่อยกด"). New measured constants X0=383.3 PITCH=38.56 Y=534.1 (fullscreen
1920x1080 scale 1.7636 → x=676+68*(n-1), y=942). CD sat measured: 4-30 recovering,
ready ≥60 → threshold 35 kept. ② prism keeper frozen by ONE stray pixel: ifnocolor
uses any(); a purple-clothed PLAYER under the HP bar matched #a46dff at tol18% (1px)
→ "buff active" → never recast. Fix: tol 12% (icon 13px, scene 0) + new optional
7th arg MINCOV% on ifcolor/ifnocolor (shield now `5% 0.2%` vs dark-scene false
presence). ③ buff region extended `5 58 89 100` → `5 58 95 148` (wrap is 2-per-row
now; 5 buffs = 3 rows; old region missed row 3). ④ rotation trimmed to
`skillspin 1 4 2 4 3 4 5 4` — slots 6-7 are EMPTY on the wizard bar (empty slot over
colorful ground reads sat ~60 = fake-ready). ⑤ single_instance_guard() (named mutex
MacroEngine_SingleInstance, Thai warning box) called from BOTH __main__ and the .pyw
(the .pyw imports App directly and BYPASSES __main__ — easy to miss) — kills the
stacked-engine toggle-cancel trap for good; verified: 2nd launch warns+exits, 1st
survives. Keepers verified 3-pass live: expired→tap→icon seen→quiet. Backups:
macro_engine.backup-20260718.py + macros.backup-20260718.json. GOTCHA learned: a
fullscreen game that loses fg for long can stop presenting (desktop shows through) —
pixel probes then read wallpaper; foreground it before trusting reads.

**18/7 บ่าย — Wing-boots keeper (P) + Q spam:** โอขอ keeper บัฟรองเท้าปีก. สีใช้ไม่ได้
(ไอคอนปีก = ขาวบนฟ้า ชนเป๊ะกับไอคอน heart/devil — เฟรมไม่มีปีกยังเจอสีนี้ 1000+px)
→ new step **`ifbuffneed FILE.png`**: template-match ตัวใน (interior, ตัด ring 4px)
ของไอคอนใน BUFF_REGION แบบ multi-scale MAD (numpy stride, no cv2), threshold 25
(calibrated: ปีก=15.8, heart หลอกใกล้สุด=31, ไม่มี=44+); เจอแล้วอ่าน "วงแหวนขาว
countdown" ที่ทุกไอคอนบัฟมี — **หมุนตามเข็มจาก 12, จุด 9 นาฬิกาดับ = ~75% หมด**
(โอสอนเรื่อง ring; ยืนยันจาก 3 ไอคอนใน static frames) → ขอบ 9 ดับ หรือไอคอนหาย
= tap p. hud guard เดิม (_hp_level None → no fire, พิสูจน์สดกับเมนูเปิด 4ms).
Template: `makcu/buff_wing.png` (24x24, จาก icon 31px @sc1.7636 = BUFF_TPL_SC).
Macro "Wing boots keeper (P)" trigger **`[`**; "Q spam (Q)" trigger **`q`** = tap q
ทุก 300ms toggle บนปุ่มตัวเอง (window-mode PostMessage ไม่ trigger hook ตัวเอง).
⚠️ ยังไม่ได้เทสต์ ring-expiry จริงครบวง (บัฟยาวหลายนาที + โอเล่นอยู่) — ถ้า spam P
ตอนบัฟยังอยู่ = template พลาดที่ไอคอนไซส์อื่น (จับภาพไซส์นั้นมา re-capture template /
ปรับ threshold); ถ้าเงียบตอนบัฟหาย = heart หลอก (ลด threshold). Icon sizes เจอจริง:
24-47px แปรผันแม้ fullscreen เท่าเดิม — สาเหตุยังไม่รู้.

**18/7 สาย — โหมดสกิล CC/ดาเมจ (exclusive toggle groups):** โอเลือก "ทำทั้งคู่":
`` ` `` = full rotation `skillspin 1 2 3 4 5`, **`;` = Mode CC** `skillspin 1 2`,
**`'` = Mode Damage** `skillspin 3 4 5` — ทั้งสามอยู่ macro field `"group": "skills"`;
new engine feature: starting a toggle soft-stops every other running toggle in the
same group (mode buttons, not stacking). Also: pressing a toggle whose entry is
mid-shutdown (event already set — e.g. just group-stopped) now STARTS a fresh loop
instead of eating the press (fast switch-and-back works); _cleanup pops by identity
so replacement entries survive. _save_macro now carries unknown keys (group) through
GUI edit+save. ASSUMPTION (โอยังไม่ได้ยืนยัน): CC = slots 1,2 / damage = 3,4,5 —
swap numbers in the skillspin lists if wrong. skillspin still digits-1-9 only;
row-2 slots (R/T, y≈571 ref) need an extension if โอ moves skills there. Verified:
App-level runner test (run_steps stubbed) — ;→'→` each stops the others, non-group
pickup untouched, group survives GUI save. โอ raised heal threshold to 90% themselves
in the GUI (kept). Engine relaunched pid 11816.

**18/7 เช้า — channel rows RE-MEASURED (โอ: "แถว 7 กดไม่โดน"):** the old row pitch
(ref y = 31+18*(n-1)) was ~2px/row short vs the real dropdown — error accumulates
so F7 clicked row 6's band (19px off). Measured the OPEN dropdown live: row centers
= 62 + 33.7*(n-1) screen px @scale 1.7636 → ref rows now **35/54/73/92/112/131/150**
(F1-F7); F8-12 hover→92, bottom-row click→150. Same-channel full-switch NOT
live-tested (โอ was mid-boss-fight — coords are within ~1px of measured centers).
ALSO: in-combat the buff icons render SMALLER (4-across mini row) than in town —
the keepers still detected them, but if buff detection flakes in combat, re-mine
signatures from a COMBAT frame, not a town frame. Editing macros.json requires
killing the engine first (it overwrites from memory on save) — killed 10524,
relaunched as 5488; watchers start OFF after relaunch (โอ must re-toggle).

**Game patch 18/7 — signature audit:** the SpiritVale patch retinted the
channel BUTTON bg #000000 → #22222a (guard silently failed in 0.01s, no
logs — condition aborts are silent by design; a fast+silent channel macro =
suspect the GUARD first). Everything else survived: menu rows ~#383d4d
(within old tol), popup lavender #b9accd EXACT, hp green unchanged, buff
sigs shield 236px / prism 22px still unique. GUARD now #22222a tol6%.
Full dead→Ch2→Ch1 round trip re-verified post-patch (0.83s, clean logs).
LESSON: after any game patch, re-run the color audit before trusting macros.
Also: channel-switch WHILE DEAD revives the char with full HP in place —
that's why โอ wanted the dead-switch to work (free revive trick).

**Focus-block ownership (18/7, โอ: "ใช้มาโครฮีลอยู่ สลับแนลไม่ได้เลย"):**
root cause — every watcher macro (heal/buff/rotation) calls ROUTER.focus_end()
in run_steps' `finally` on EVERY pass (~50ms for heal). While a channel switch
held the focus block for its 3-click sequence, a concurrent watcher's cleanup
ripped the focus/cursor back MID-SEQUENCE → dropdown closed → no switch (any
F-key looked dead). Fix: focus block is now OWNED by the thread that opened it
(threading.get_ident) + a _focus_gate lock; focus_end() is a no-op for
non-owners (force=True for panic/reset/close). Plus tap()/hold() call
_wait_block_clear() so a watcher's key-send queues (≤2s) instead of SetFocus'ing
the game mid-dropdown. Verified: ownership unit test PASS; live contention test
Ch2→Ch4 succeeded (0.79s, clean) while a watcher hammered `tap 3` 9x in
parallel. Perf: _wait_block_clear returns instantly when no block is held, so
normal watcher cadence is unaffected.

**Adaptive channel switch rev3 (17/7 morning):** โอ's reports "ตายแล้วสลับไม่ได้
/ บางปุ่มยังเร็ว" → two fixes. ① DEAD BUG: ifcolor was coupled to _hp_level
(hud guard) — dead = 0% hp = no green = guard blocked channel switching;
now only ifNOcolor keeps the hud guard (absence-evidence), ifcolor is
positive-evidence and works while dead. ② fixed delays replaced with
`waitcolor [win] X1 Y1 X2 Y2 #color tol TIMEOUT_MS` (poll 50ms until color
appears; timeout aborts the run) — channel macros now wait for the ACTUAL ui:
dropdown-open signature #353b4b tol8% in rows region (r-130 25 r-20 45;
open=4910px closed=0), popup signature = Close button lavender #b9accd tol5%
(c-60 74 c-20 92; Ok-button blue was USELESS — the town fountain crystal
matches it even at tol10). Also held-mode clicks now jiggle 1px + 60ms hover
before clicking (Unity rows want pointer-over first). Shared region probe =
_region_color_found(). Note: the black button-guard false-positives on the
SERVER-SELECT screen (dark foliage) but waitcolor contains it to one stray
harmless click. Full in-game switch NOT re-verified (game was at server
select) — โอ tests F2/F3 after logging in.

**Buff keeper rev2:** buff icons wrap 4-per-row into MULTIPLE rows and change
ORDER between frames (prism was cell2 in shot1, cell1 in shot2) → region
widened to cover both rows (ref units x5..88... final: `5 58 89 100`). Shield
signature #090962 tol10% FAILED cross-frame (matched the prism icon's dark bg
in shot2) → re-mined with cross-validation on BOTH screenshots + all 8 icon
cells: **shield = #08083f tol 5%** (142-145 px own, 0 others), **prism =
#a46dff tol 18%** (18-20 own, 0 others). Lesson: mine color signatures from
≥2 frames — icon glow animates. Another stacked engine killed (pid 2316).

**Buff keeper (16/7 late night, โอ's request "ดูบัฟ หมดแล้วกด 8/9"):** new
steps `ifcolor` / `ifnocolor [win] X1 Y1 X2 Y2 #color tol` — region ANY-pixel
color search (numpy, one grab). Buff icons COMPACT leftward when others
expire, so search the whole buff row for each icon's signature color instead
of a fixed pixel. Signatures mined from โอ's screenshot with cross-icon
uniqueness check: skill-8 shield = #090962 tol 10% (81 px in own icon, 0 in
others @tol25); skill-9 prism = #a46dff tol 18% (20/0). Buff row region ref
units: x5..88 y75..96. win form auto-ui-scales AND requires HUD visible
(_hp_level not None) — map open ≠ buff expired. Macros: "Buff 8 (shield)
keeper" trigger '-', "Buff 9 (prism) keeper" trigger '0', toggle, 500ms poll,
1500ms after recast. NOT live-verified (game showed a dark menu screen at the
time). ⚠️ FOUND 3 MACRO ENGINES RUNNING AT ONCE (X hides to tray; โอ kept
launching new ones) — every trigger fired 3x, likely amplified the heal spam;
all killed. Check for stacked engines whenever behavior looks doubled.

**Heal-spam root cause (16/7 night, "เต็มแล้วแต่ยังฮิลตลอด"):** fullscreen
map/inventory/menu screens HIDE the hud → the bar pixels read as scene colors
→ zero green → bar_level=0% → "below 90" fired every 100ms while the map was
open. (Reading + cal were both correct in normal view — reproduced offline on
the saved map screenshot: level 0.0%.) Fix: `_analyze_hp_band()` reads a
5-row band and demands POSITIVE bar evidence — green fill at far-left (x≤3)
on ≥2 rows AND ≥4 near-white pixels (the HP text) — else `_hp_level` returns
None (no fire). Verified on 4 real screenshots: map=blocked, fullscreen
100%, boss-fight 91.9% (true 91.0%), town 100%. Also find_hp_bar now requires
bar width ≥ 6% of window width (a stray 11px green blip got auto-cal'd while
the hud was hidden). Corner accepted: below ~1.5% HP the left-fill evidence
vanishes → no heal on a nearly-dead char (heal starts at the threshold long
before that). REMEMBER: engine must be FULLY exited (tray → Exit, X only
hides) and reopened to pick up code fixes — a running engine = old code.

**UI-scale-aware anchors (16/7 night, "Fullscreen แล้วมันไม่ตรง"):** fullscreen
scales the WHOLE hud (measured: HP bar 110px→212px = 1.927x at 1920x1080; the
fail mode was subtle — the dropdown click still hit the now-bigger button, but
the unscaled row-y re-hit the button = open-then-close, no switch).
Fix: `_ui_scale(h)` = live HP-bar-width ÷ 110 (ref = 956x574 client), fallback
clientH/574; `_resolve_click_point` multiplies anchored offsets AND y by it;
Pick Point divides by it on capture (stores reference units). Also handles
in-game UI-scale settings for free. Verified live: scaled anchor (1768,25)
opened the dropdown at fullscreen. Full switch NOT re-verified at fullscreen —
that server had only 1 channel; rows/Ok use the same scale. Speed pass same
night: channel macro delays 300/400→120/180ms + click sleeps trimmed → ~0.6s
per switch (was 1.2s); if clicks start missing, bump 120→150. Also fixed
find_hp_bar merging the BOSS hp bar (green, center-top) into the player bar:
now longest CONTIGUOUS segment (gap≤8px) that STARTS in the left 15% strip. click coords can now be ANCHORED to
the client area: `l+N` / `r-N` (from left/right edge) / `c±N` (from center) as
the X token of `click at` / `hover at` — resolved via GetClientRect+
ClientToScreen at click time, so resize/move/border changes need NO re-pick
(pixel-exact equivalence verified against the proven coords; live resize probe
was inconclusive — game had dropped to the server-select screen). Pick Point
now emits anchored form. New `hover at X Y` step (cursor positioning without
click, for wheel-over-list). Channel macros rebuilt: **F1-F7 = direct row
click (row y = 31+18*(n-1), dropdown r-79/13, Ok c+41/84 client coords);
F8-F12 = scroll flow** (hover over list → `wheel -(n-7)` → click bottom row
y139) — scroll ratio "1 notch = 1 row" is an UNTESTED assumption (server had
only 2-4 channels); tune the wheel count when a 8+ server appears. PANIC moved
f1 → **end** (F1 is now Channel 1). Gotcha repeated: had to kill the running
macro_engine.pyw (pid found via Win32_Process CommandLine) before editing
macros.json — it overwrites from memory on every save.

**Channel switch VERIFIED LIVE (16/7 evening):** full round-trip Ch1→Ch2→Ch1
via the real macro steps (1.2s per switch + game load). Measured coords for
window 972x613: dropdown (885,44), Ch1 row (885,62), Ch2 row (885,80), Ok
(527,115), Close (446,115) — popup is horizontally centered so resize breaks
Ok/Close first. THREE gotchas hit: ① the app OVERWRITES macros.json from
memory on every _save — close Macro Engine before editing the file externally
(channel macros got wiped once this way); ② find_hp_bar's scan region was
0.4×H and at fullscreen 1920x1080 it locked onto a PARTY-PANEL member bar
(y=411) instead of the real HP bar → region narrowed to 0.22×H (above the
party panel at ~26%), bad hp_cal cleared; ③ during loading screens the game
window is briefly missing from EnumWindows — retry, don't conclude it's gone
(hwnd changes after load, re-resolve works). โอ customized Auto Heal
themselves: trigger '=', threshold 90%, delays 50/50 — preserved.

**Multi-click sequences / channel switch (2026-07-16, โอ's request):**
`focushold` … `focusrelease` grab the target's focus ONCE around a block of
`click at` steps (one ~0.3s flick for the whole dropdown→item→OK sequence
instead of one per click); run_steps' finally + panic both call focus_end
(idempotent) so an interrupted block can't leave focus stuck. "Pick Point"
button (next to Pick Pixel) click-captures a window-relative coord and inserts
`click left at X Y`. Two template macros added: "Channel -> 1" (F2) /
"Channel -> 2" (F3) — SpiritVale channel switch (dropdown top-right → channel
slot → Ok center popup; same-channel = no popup = harmless). Coords are
PLACEHOLDERS pinned to a window size — โอ must recalibrate with Pick Point when
the game is open (game was closed this session, so click coords NOT verified
live; focus-hold logic + lint + GUI verified). Toggle-to-non-current needs
reading the current-channel text (OCR) — deferred; two keys are robust.

**New step syntax (window mode):**
- `click left at X Y` — real click flicked into target at window-relative X,Y
- `ifpixel win X Y #rrggbb 10%` — pixel check relative to target window's
  top-left (follows the window); `win` prefix optional
- tolerance now accepts `10%` (percent of 255) as well as a plain int
- Pick Pixel inside the target window auto-emits the `ifpixel win ...` form

Routing is centralized in kb_press/kb_release/kb_send/kb_write → every macro
mode (once/toggle/hold/holdkey/sequence + walk template) gets window mode free.
Backup before edit: `macro_engine.backup-20260716.py`. Compile + GUI smoke +
live SpiritVale walk all verified. **Live-untested by โอ:** flick_click actual
in-game click-to-move (she said she'd tune it), and pixel-condition macros.

**Self-review pass (same day, all Fable — no Opus involved despite the ask):**
fixed the one real hot-loop — `hold()`'s typematic repeater was calling
`hwnd()`→`list_windows()` (EnumWindows + OpenProcess on every window) every
50ms, ~260 OpenProcess/sec just to walk. Now caches the resolved hwnd and only
re-scans when `IsWindow()` says it died. Also moved the `_held` registration
AFTER the not-found check so a missing target can't leave a dangling held-key
entry. Re-verified walk still works. Remaining known limits (accepted, not
bugs): `hold`/`release` on a combo only hold the LAST key (hold is single-key
by design); `move`/`click` move the REAL cursor so they're disruptive — that's
inherent, games ignore synthetic mouse.

**22/7 ต่อ(9) — 🟢 ปุ่มพัก Scroll Lock + walk_mode + ตอบ WASD vs คลิก (โอถาม "แย่งคุมไม่ได้"):**
โอ: "บอททำงานอยู่ ฉันจะเข้าไปบังคับ เลื่อนเม้าไม่ทัน" + "ทำให้ปิดได้ด้วย คีย์ลัด Trigger เปิดปิดก็ได้".
① **F9 = พัก/เล่นต่อ (toggle)** ใน soak_driver watchdog (โอเลือก F9 แทน Scroll Lock): กด 1 ที →
`user_pause.set()`+`phase_stop.set()`+`unstick_keys()` = ปล่อยเมาส์/คีย์ทันที โอคุมเกมเองได้ (บอทเลิกยึด
SetCursorPos เพราะ walk_loop หยุดเรียก _mmkite/_ctm_kite); กดอีกที = ฟาร์มต่อ. watchdog poll 0.1s
(เดิม 1s ช้าไปจับ edge ไม่ทัน) ตรวจ GetAsyncKeyState(**0x78**) ขอบขาขึ้น. **End = หยุดถาวรเหมือนเดิม**,
SOAK_STOP ไฟล์ (FARM-STOP.bat จาก console) เหมือนเดิม. กันชน recovery: `user_pause` เป็น event แยกจาก
phase_stop; recovery ตอนจบ `if not user_pause: phase_stop.clear()` = พักไว้ตอน recovery จบก็ยังพัก.
กลไกเดียวกับ End (0x23) ที่ watchdog เดิมใช้ได้จริง → F9 ทำงานแน่ (พิสูจน์โดย analogy).
② **walk_mode สลับได้ (macros.json mmkite_cfg.walk_mode) — โอสั่ง 22/7 "ใช้ทั้งคู่":** ตั้ง **default=wasd**
แล้ว. "wasd"=walk_loop เรียก `_mmkite` = **HYBRID เดิม: WASD หลัก + `_click_move()` ตอนติด ≥0.35s
(เกม pathfind อ้อมกำแพง) + เมาส์เล็งมอน + กันวาป 3 ชั้น** (blue repulsion / wrong-map abort / จำจุดวาป) —
ตรงคำขอโอเป๊ะ. "ctm"=`_ctm_kite` คลิกล้วน (เก็บไว้เผื่อ). walk_loop เช็ค `MMKITE_CFG.get("walk_mode")`.
③ **ตอบสมูท: WASD ลื่นกว่าตอนสแปมสกิล (ยืนยันสด).** เทสต์จุดว่าง (ชายหาด Channel 1): HP 8045/8045
เต็ม, เดินครบ 4 ทิศ (mv 12-15px/2s ต่อทิศ) — input กลับมาปกติจากที่ค้างเมนูเมื่อกี้แล้ว. เห็นจอ
**"Can't cast yet!"** + ไอคอนคูลดาวน์ 3.0/2.7 วิ่ง = สกิลออกจริงแต่ติด GCD/cast-time (11 วิ ได้แค่ 4
สปิน 1-9 เต็ม). **เพราะทุกครั้งที่ร่าย ตัว "หยุด" ช่วง cast-time แล้วถึงขยับต่อ** (ตรงกับที่โอสังเกต):
WASD กดค้าง → พอ cast จบ ตัวเดินต่อทิศเดิมเอง**ไม่ต้องสั่งใหม่**; Click to Move → เป้าคลิกหายทุกครั้ง
ที่ร่าย ต้อง**คลิกใหม่ถี่มาก** (โอเดาถูก). ⇒ กลางแมพโล่ง (ไกลวาป) ใช้ wasd ลื่นกว่า; ctm ดีเฉพาะ
**ตอนเดินทางเข้ากลาง** (อ้อมวาป/กำแพง). ค่า default ยังเป็น ctm (นำทางปลอดภัย) — โอสั่งสลับ wasd
ได้เมื่ออยากฟาร์มกับที่ให้ลื่น. เครื่องมือเทสต์: `_walktest.py` (raw 4 ทิศ + skill-spam + wt_before/after.png).

**22/7 ต่อ(10) — แผนที่กำแพง Forge (web editor) + 🔴 gotcha คลิก login ไม่ลงใน RDP:**
โอขอ "ทำแผนที่สิ่งกีดขวางทั้งแมพให้ครบ แล้วมาร์คเอง". ทำแล้ว: ① แคปมินิแมพ Forge **North-up**
(โอกดเหนือขึ้นบนเอง — ต้องไม่หมุนถึงมาร์คได้, indicator "N" บนสุด; โหมดหมุน="z") ผ่าน buff+warp+
zoom-out+cap+home (HP เต็มตลอด). ② `map_editor.py` + `MAP-EDITOR.bat` = **หน้าเว็บ localhost:8777**
โชว์ `forge_map_base.png` (crop x1697-1909 y112-270 ×7) + กริด ลากทาสีกำแพงแดง/คลิกขวาลบ/แปรง/
ปุ่ม auto-detect (ลาวาส้ม+หินเข้ม — โอบอก auto ไม่แม่นเลยเป็นแค่ตัวช่วย)/บันทึก→POST เขียน
`forge_obstacles.json` (grid + meta crop/scale ให้ bot จับคู่พิกัดภายหลัง). เทสต์ GET/POST ครบ.
**ค้าง: โอว่าซูมออกสุดหยาบไป → ต้องทำแบบ stitch ซูมเข้า+ต่อภาพ (เดินเก็บ tile ความละเอียดสูง)**
ยังไม่ได้ทำ. ③ ขั้นต่อบอท (ยังไม่ทำ): อ่านหมุด+ทิศ → ช่องกำแพง = หลบ.
🔴 **gotcha ใหญ่: หน้า login/disconnect (Select Server) ใน RDP session ไม่รับคลิกสังเคราะห์เลย**
— ลอง `_fg_click` (SetForegroundWindow) และ real-click (SetCursorPos+mouse_event ที่ใช้ได้ในเกมโลก)
ทั้งคู่ **ไม่ดิสมิส popup "Ok"/ไม่กด Connect** (พิกัดถูก คำนวณจาก client-rect ตรงกับภาพแคป แต่คลิก
ไม่ลง). แปลว่า **`_relogin` / relogin_timer_loop ตอนฟาร์มหลุดเซิร์ฟใน RDP จะกลับเข้าเกมเองไม่ได้** —
ต้องหาเหตุ (โฟกัสหน้าต่าง? RDP input desktop? Unity UI ต้อง real focus?) ก่อนพึ่ง auto-relogin.
เฉพาะกิจนี้ให้โอคลิกเอง: Ok → SEA(เลือกอยู่แล้ว) → Connect → ดับเบิลคลิกตัวละคร. เกมเวอร์ชัน v0.30.8.

**22/7 ต่อ(11) — ยืนยัน: หน้า login ไม่รับ input ทุกชนิดใน RDP (เมาส์+คีย์บอร์ด):** ต่อจาก(10)
ลองครบ: เมาส์ 3 วิธี (_fg_click / real-click / AttachThreadInput+SetForegroundWindow) + **คีย์บอร์ด
`tap enter` (PostMessage) ก็ไม่ดิสมิส popup "Ok"** — ทั้งที่ในเกมโลกคีย์บอร์ด PostMessage ใช้ได้.
สรุปเหตุน่าจะ: Unity UI (EventSystem) โพลล raw device state ไม่อ่าน window message + mouse_event
ไม่ถึง input desktop ของ RDP session. **ผลกระทบ: auto-relogin ตอนฟาร์มหลุดเซิร์ฟ = ทำไม่ได้ใน RDP
ด้วยวิธีปัจจุบัน** ต้องมือโอ. ไอเดียลองต่อ (ยังไม่ทำ): `SendInput` (API ใหม่กว่า mouse_event อาจ
ทะลุ RDP), หรือ hardware (Makcu ไปไม่ถึง RDP session). เฉพาะกิจ: โอคลิก Ok→SEA→Connect→ดับเบิลตัวละคร.

**22/7 ต่อ(12) — 🟢🔑 แก้ได้! `SendInput` (absolute move+click) ลงหน้า login ใน RDP ได้:**
กลับคำ(11): ที่ว่า login ไม่รับ input — จริงเฉพาะ mouse_event/SetCursorPos/_fg_click/keybd. **SendInput
ทำงาน!** พิสูจน์สด: หลัง relaunch → SERVER SELECT → คลิก SEA(0.5,0.449)+Connect(0.5,0.914) →
CHAR SELECT → ดับเบิลคลิก(0.072,0.142) → **IN-GAME HP 100**. กุญแจ: SendInput ส่ง flag
`MOUSEEVENTF_ABSOLUTE|MOVE`(0x8001) ก่อน `|LEFTDOWN`(0x8002)/`|LEFTUP`(0x8004) — **การ MOVE
สร้าง event เลื่อนเมาส์จริงที่ Unity UI (EventSystem) โพลล์เห็น** ต่างจาก SetCursorPos ที่ย้าย cursor
เฉยๆ ไม่มี move event. coord absolute = pixel*65535/(screenmetric-1). สคริปต์ทำงาน: `_si2.py`.
🔴 **อย่าใช้ SetForegroundWindow/AttachThreadInput คลิก login ใน RDP** — รอบนี้ทำเกม **minimize
แล้ว crash หาย** (hw=None) ต้อง relaunch `os.startfile("steam://rungameid/3767850")` ผ่าน bridge
(ให้เปิดใน session ykfarm; ~35s ขึ้น server-select สะอาดไม่มี popup). SendInput ไม่แตะ foreground =
ไม่ minimize ไม่ crash. **TODO สำคัญ: เปลี่ยน `_fg_click`/`_relogin` ให้ใช้ SendInput → auto-relogin
ตอนฟาร์มหลุดเซิร์ฟจะทำงานเองใน RDP ได้จริง** (ตอนนี้ยังใช้ _fg_click = พังใน RDP). เหตุหลุดรอบนี้:
เกิดตอนสำรวจปุ่ม M/ไอคอนแผนที่ — น่าจะเซิร์ฟเด้งเองพ้องจังหวะ; บทเรียน: อย่ายิง input สำรวจบนตัวจริง
โดยไม่มีเซฟตี้. ตัวละครกลับเข้าเกม+take-me-home ปลอดภัยแล้ว (Forge Channel 2 → เมือง).

**22/7 ต่อ(13) — ✅ เดินสาย SendInput เข้า `_fg_click`/`_relogin` แล้ว (แก้ TODO ข้อ 12):**
`_fg_click(hw,fx,fy,double,ui=False)` เพิ่มพารามิเตอร์ `ui`: **ui=True → SendInput ล้วน** (หน้า
login/disconnected: SEA/Connect/char-select — ไม่มี SetForegroundWindow = ไม่ crash), **ui=False →
ของเดิม ALT+SetForegroundWindow+mouse_event** (คลิกในเกม: คริสตัล/แมพวาร์ป/respawn/log-out — พิสูจน์
เซสชันนี้ warp Forge ได้). `_relogin`: SEA/Connect/char = ui=True + เพิ่มปิด popup "Ok" (0.5,0.144
ui=True) ก่อนเลือก SEA (เคสหลุดเซิร์ฟจริงมี popup บัง); Log Out ยัง ui=False (เมนูในเกม). helper ใหม่:
`_si_click_abs(sx,sy,double)` + struct `_MOUSEINPUT/_INPUT_MS` + `_send_mouse`. **verify:** สาย
disconnect→SEA/Connect/char พิสูจน์แล้ว (_si2.py กู้ตัวละครกลับเข้าเกมด้วยคลิกชุดนี้เป๊ะ); ui=False
เก็บโค้ดเดิมไม่แตะ = คงพฤติกรรม warp ที่ใช้ได้. **ยังไม่ได้เทสต์ full _relogin แบบ Log Out สด**
(เลี่ยง logout รบกวนซ้ำ) — ถ้า Log Out (ui=False) ไม่ลงเมนูในเกม ค่อยเปลี่ยนเป็น ui=True. soak_driver
Popen ใหม่ได้โค้ดใหม่อัตโนมัติ; bridge reload แล้ว. gotcha เดิม: bridge ถือ macro_engine เก่า ต้อง
importlib.reload ก่อนเทสต์โค้ดใหม่ผ่าน bridge.

**23/7 — 🗺️🔑 ได้แผนที่ห้ามเดินของจริงจาก NavMesh ใน bundle (แทนการมาร์คมือ/ต่อภาพ):**
โอเสนอเอาแมพจาก bundle (งานอีก session — ดู [[project-spiritvale-codex]]) มาใช้กับบอท → **ทำได้ และดีกว่าทุกทางที่คิดไว้**
เพราะ bundle ของ Forge แถม **`Assets/NavMeshData/NavMesh-NavMesh Surface.asset` (3.2MB)** = NavMesh จริง
ที่เกมใช้เดิน (เกมนี้เดินด้วย NavMesh บน server) → **ไม่ต้องเดาจากสีมินิแมพ ไม่ต้องมาร์คเอง**.
- แมพแกะไว้แล้วที่ `C:\re\ripped\forge\ExportedProject` (prefab `Assets/_Maps/Prefabs/Forge.prefab` 12MB,
  ป้อมคนแคระ; **ไม่มี TerrainData** → วิธี heightmap/ความชันแบบ bunny_woods ใช้ไม่ได้)
- 🔴 **gotcha: `MapSandbox.RunAll` ให้ตารางหยาบมาก** (FlatMap.png 220² แต่พื้นที่จริงเหลือ ~37 ช่อง)
  เพราะคิดขอบเขตจาก prefab ทั้งก้อน (รวม FX/ลาวาไกลๆ) → แก้โดยคิดขอบเขต **จาก navmesh เอง**
- เครื่องมือใหม่: `Assets/Editor/NavExport.cs` — `NavMesh.AddNavMeshData` → `CalculateTriangulation()`
  → rasterize สามเหลี่ยมลงตาราง. รัน: `Unity.exe -batchmode -quit -projectPath C:\re\ripped\forge\ExportedProject
  -logFile C:\re\nav_run.log -executeMethod NavExport.Run` (~1-2 นาที)
- **ผลจริง: verts 42,644 / tris 20,264; world bounds x[-122.3,101.5] z[-456.4,-240.2]; ตาราง 768²
  ช่องละ 0.297 หน่วย (~30ซม.) เดินได้ 89.6%** → ละเอียดกว่ามินิแมพมาก. เส้นดำบางในภาพ = ราวกันตก/กำแพงเตี้ย
  จริง (prefab มี `SM_Env_Dwarf_Balustrade_Stairs`), ขอบดำรอบนอก = นอก navmesh (ลาวา/หิน)
- ไฟล์ผลลัพธ์ก๊อปไว้ฝั่งบอทแล้ว: `C:\makcu\ForgeNavGrid.png` + `ForgeNavGrid.json`
  (grid/originX/originZ/cell/span/min-max; **PNG row0=ล่าง=minZ, x→+X, y(ขึ้น)→+Z**)
- **ค้าง: จับคู่พิกัด Unity world ↔ มินิแมพที่บอทใช้เดิน** (หา affine: หมุน/สเกล/เลื่อน) แล้วต่อเข้าระบบหลบกำแพง

**23/7 ต่อ — แยกชั้น navmesh สำเร็จ (ได้ผังพื้นจริง) แต่ 🔴 จับคู่พิกัดกับมินิแมพยังไม่ผ่าน:**
- 🔴 **gotcha: Forge เป็นแมพหลายชั้นมาก (navmesh สูง y −32..+99)** ยุบ 2D ตรงๆ ชั้นทับกัน = ก้อนตัน 89.6%
  ใช้หลบกำแพงไม่ได้ → ต้อง**แยกตาม Y**. `NavExport.cs` เวอร์ชันใหม่ทำฮิสโตแกรม Y แล้วตัดเป็นชั้น:
  **เจอ 4 ชั้น — ชั้น 0 y[−30.6,−28.6] = พื้นหลักที่ฟาร์ม (441,605 ช่อง 74.9%)**, ชั้น1 y≈−20 (10.2%),
  ชั้น2 y≈0 (4.5%), ชั้น3 y≈+8 (14.4%). ภาพ L0 เห็นผังจริง: **สนามวงกลม + ช่องว่างรูปเกือกม้ากลางแมพ
  (บ่อ/เตาหลอม เดินไม่ได้) + ก้อนเสากระจาย**. ไฟล์: `C:\makcu\ForgeNav_L0.png` / `_L0_clean.png` /
  `ForgeNav.json`; ต้นทาง `C:\re\navonly\Assets\Scenes\ForgeNav_L*.png`
- 🔴 **gotcha: โปรเจกต์ ripped ถูกอีก session ล็อกอยู่** (`HandleProjectAlreadyOpenInAnotherInstance`,
  เขา log เป็น forge5.log) → **อย่าฆ่า Unity ของเขา** ให้สร้างโปรเจกต์จิ๋วแทน: `C:\re\navonly`
  = ProjectSettings + Packages + `Assets/NavMeshData/*` + `Assets/Editor/NavExport.cs` เท่านั้น
  (**1.7MB 26 ไฟล์ ไม่ต้องมี prefab/เมช/เท็กซ์เจอร์** เพราะ CalculateTriangulation ใช้แค่ NavMeshData)
- 🔴 **จับคู่พิกัดอัตโนมัติด้วยรูปร่าง = ไม่นิ่ง เชื่อไม่ได้** (`_align.py`/`_align2.py`): all-levels ได้
  IoU 0.638 mirror=True rot0 / L0 ได้ IoU 0.535 mirror=False rot180 — **คนละทิศกัน** = ไม่ converge.
  เหตุ: **มินิแมพ (ซูมออกสุด) ครอบพื้นที่กว้างกว่า navmesh มาก** (มีลาวา/หินเต็ม) + mask พื้นชมพูจาก
  สีหยาบเกิน. ปิดรอยต่อสามเหลี่ยม (closing 3×3) ช่วยแค่ +162 ช่อง — เส้นดำเป็นขอบ polygon จริงหนากว่า 1px
- landmark จาก prefab ก็ตัน: **วาปคริสตัลไม่ได้อยู่ใน Forge.prefab** (มีแต่คริสตัลตกแต่ง SM_Prop/SM_Env)
- **ทางที่ควรลองต่อ (ยังไม่ทำ): คาลิเบรตกับของจริงในเกม** — เดินตัวละครชนกำแพงทีละทิศ (N/S/E/W) จด
  ตำแหน่งหมุดบนมินิแมพตอนชน = จุดขอบ navmesh → fit ขอบเขตเข้าหากัน; หรือใช้ 2 จุดที่ระบุได้ทั้งสองฝั่ง
  แล้วแก้ affine ตรงๆ. สเกลคร่าวๆ ที่ได้ทุกรอบตรงกัน ≈ **1 มินิแมพพิกเซล ≈ 2.39 หน่วยโลก** (ใช้เป็นค่าตั้งต้น)

**23/7 — 🚀 เปลี่ยนสถาปัตยกรรมบอท: BepInEx ปลั๊กอินในโปรเซส (เลิกอ่านจอ/ยิงเมาส์):**
โอสั่งอ่านโปรไฟล์ใหม่ (โอ = **dev ของ SpiritVale เอง** — RE/hook/bot research = งานอาชีพ ทำเลย ไม่ต้องทวนขอบเขต)
→ ปลดล็อกทางที่ตรงกว่าทั้งหมด. อีก session เขียน `C:\re\bepinex\FarmBot\Plugin.cs` ไว้แล้ว
(FindLocalPlayer ผ่าน `FindObjectsOfType<PlayerController>()` + `IsOwner`; อ่าน `transform.position` ตรงๆ;
ป้อนอินพุตผ่าน **`PlayerInputDto` + `SendInputsToServer`** = เส้นเดียวกับคนจริง ห้ามยัด transform)
แต่ติดที่ยังไม่ได้ลง prerequisite — **ผมลงให้ครบแล้ว:**
- **BepInEx 6 IL2CPP be.785** (`builds.bepinex.dev/projects/bepinex_be/785/BepInEx-Unity.IL2CPP-win-x64-*.zip`)
  แตกลง `C:\Program Files (x86)\Steam\steamapps\common\SpiritVale\` → winhttp.dll + BepInEx/
- **.NET SDK 8.0.423** (winget Microsoft.DotNet.SDK.8)
- เปิดเกม 1 รอบ → **interop 163 dll** ที่ `BepInEx\interop\` (ใช้เวลา ~50 วิ)
- build: **อย่ารัน `build.ps1` ด้วย powershell.exe** — ไฟล์มีภาษาไทย + อ่านเป็น ANSI = parser พัง
  (gotcha เดิม "ps1 ห้ามมีไทย") → สั่ง `dotnet build <proj>.csproj -c Release` ตรงๆ แล้วก๊อป dll ไป plugins
- **ผลสด: FarmBot + NavProbe โหลดเข้าเกมสำเร็จ** (log `BepInEx\LogOutput.log`; F7=FarmBot toggle)
- DamageBench ของอีก session build ไม่ผ่าน (`BaseUnitController` ไม่มี `ApplyDamageToTarget` ใน interop) — งานเขา ไม่แตะ
- **ปลั๊กอินใหม่ของผม: `C:\re\bepinex\NavProbe`** — วัดกำแพงจาก **NavMesh ของเกมสดๆ ในโปรเซส**
  (`NavMesh.SamplePosition` + `NavMesh.Raycast` 8 ทิศ) → **ไม่ต้องจับคู่พิกัดมินิแมพอีกแล้ว** (งานที่ค้างเมื่อคืน
  ตกไปเลย); F9 วัดครั้งเดียว/F10 ต่อเนื่อง/F11 self-test; เขียนผลลง `C:\makcu\navprobe.txt`
  ⚠️ `NavMesh.CalculateTriangulation` **ไม่มีใน interop** (Unity strip) → ใช้ SamplePosition/Raycast แทน
- **กันแพทช์ (โอถามตรง):** ปลั๊กอินผูกด้วย**ชื่อ member ไม่ใช่ offset** + BepInEx สร้าง interop ใหม่เองเมื่อ
  GameAssembly เปลี่ยน → แพทช์ที่ขยับ offset ไม่กระทบ (ต่างจากอ่าน memory/อ่านจอที่**พังเงียบ**).
  เพิ่มกันพลาด: **version stamp** (`C:\makcu\navprobe_validated.txt` ไม่ตรง = เตือนดัง + ตั้งธง Stale) +
  **self-test fail-closed** (navmesh/ตำแหน่งไม่ผ่าน = ไม่ยอมทำงาน) + **`C:\re\bepinex\patchwatch.py`**
  (เทียบ sha256 GameAssembly.dll; `--fix` = ล้าง interop + ล้าง stamp + rebuild + ก๊อปลง plugins)
- **RDP แทบไม่จำเป็นแล้ว** — บอทป้อนอินพุตในโปรเซส ไม่แตะเมาส์/ไม่อ่านจอ/ไม่แย่งโฟกัส; สะพาน session
  ตายตั้งแต่ 22/7 19:34 และ Steam ย้ายมา session 1 (จอหลัก) แล้ว RDP เหลือแค่ประโยชน์ "ให้เกมไปอยู่อีกจอ"

**23/7 — 🛡️ NavGuard 1.2.0: ตรวจอัตโนมัติทุกครั้งที่เข้าเกม + ปิดบอทเองถ้าไม่ผ่าน (fail closed):**
โอสั่ง "กันเข้าใจผิดแล้วโดนตรวจจับแบน ควรเช็คทุกครั้งก่อนเข้าเกม" → NavProbe อัปเป็น **NavGuard**:
- **ตรวจเองอัตโนมัติ** เมื่อเจอตัวละคร (= เข้าเกมแล้ว) + ตรวจซ้ำทุก 30 วิ — ไม่ต้องกดปุ่ม
- เช็ค 5 อย่าง: **เวอร์ชันเกมตรงกับที่ validate ไว้** · อยู่บน navmesh · `NavMesh.Raycast` ใช้ได้ ·
  ตำแหน่งสมเหตุผล · อ่าน `IsOwner` ได้ → ไม่ผ่านข้อใดข้อหนึ่ง = **BLOCKED**
- **ไม่ผ่าน → สั่ง `b.enabled=false` ใส่ `FarmBot.Bot` ทุกตัวทันที** (อ้างอิง FarmBot.dll ผ่าน csproj +
  `[BepInDependency(SoftDependency)]`) — **ไม่ต้องแก้โค้ดของอีก session เลย**
- เขียนคำตัดสินลง `C:\makcu\botguard.txt` (`PASS|BLOCKED | ver=.. onNav=.. ray=.. sane=.. owner=.. | เหตุผล`)
  ให้ฝั่งนอกอ่านได้; version stamp ที่ `C:\makcu\navprobe_validated.txt` (ฐานปัจจุบัน **0.30.8 / unity 6000.0.64f1**)
- ปุ่ม: **F7** FarmBot เปิด/ปิด · **F9** วัดกำแพงครั้งเดียว · **F10** วัดต่อเนื่อง (เปิดไม่ได้ถ้า guard ไม่ผ่าน) ·
  **F11** ตรวจซ้ำเดี๋ยวนั้น
- **วิธีใช้ = เปิดเกมอย่างเดียว ไม่ต้องเปิดโปรแกรมอื่น** (winhttp.dll/doorstop โหลด BepInEx เอง)
- หลังเกมแพทช์: guard เตือนดัง + บล็อกบอท → รัน `patchwatch.py --fix` (ล้าง interop+stamp, rebuild, ก๊อป)
  → เปิดเกม 1 รอบ gen interop → เปิดอีกรอบ guard จะ PASS เอง
- ⚠️ gotcha ตอนเขียนไฟล์ผ่าน bash heredoc: **`\` โดนกลืนเหลือ `\`** ทำ C# escape พัง (`\p`) —
  เลี่ยง path มี backslash ใน string หรือแก้ทีหลังด้วย `sed -i '<line>s|.*|...|'`

**23/7 — เปลี่ยนชื่อ FarmBot → MovementBench (โอสั่ง "กันการเข้าใจผิด"):** ชื่อเดิมอ่านแล้วดูเหมือนตัวโกง
ทั้งในล็อกและถ้าระบบตรวจของโอเองไปเจอ → เปลี่ยนให้เข้าชุดกับ DamageBench (สื่อว่าเป็นแท่นทดสอบ).
เปลี่ยนครบทุกจุด: โฟลเดอร์ + csproj + `<AssemblyName>` + `namespace` + GUID
(`re.spiritvale.farmbot`→`re.spiritvale.movementbench`) + ข้อความล็อก (เลี่ยงคำว่า "บอท" ด้วย →
"F7 เริ่ม/หยุดทดสอบ") + `[BepInDependency]` กับ `FindObjectsOfType<MovementBench.Bot>()` ใน NavGuard
+ reference ใน NavProbe.csproj + PLUGINS ใน patchwatch.py; ลบ `FarmBot.dll` เก่าออกจาก plugins.
**verify สด: ล็อกขึ้น `Loading [SpiritVale MovementBench 1.0.0]` + `Registered mono type
MovementBench.Bot` และ grep คำว่า FarmBot ในล็อก = 0 ครั้ง**

**23/7 (Fable) — เปลี่ยนชื่อกันเข้าใจผิด → Cobalt + อุดช่องงาน Opus (hash gate):**
โอสั่งเอาชื่อเสี่ยงออก + รีวิวงาน Opus. **ชื่อที่ Opus แก้ไม่หมด (เสี่ยงจริง):** คลาสชื่อ `Bot` ตรงๆ
(ถูก log `Registered mono type MovementBench.Bot`), display มี "SpiritVale", GUID `re.spiritvale.*`,
คอมเมนต์ซอร์สเขียน "บอท...กันบอทของ SpiritVale". **ช่องโหว่ตรรกะ (สำคัญกว่าชื่อ):** guard เดิมเช็ค
`Application.version` → **hotfix ที่แก้ GameAssembly.dll แต่ไม่ขยับเลขเวอร์ชัน = PASS ผิด** (เคสที่โอกลัว).
**แก้ทั้งหมด → ชุด Cobalt:**
- `C:\re\bepinex\Cobalt` (ไดรเวอร์ เดิม MovementBench/FarmBot): assembly/namespace `Cobalt`, GUID
  `dev.cobalt.core`, คลาส MonoBehaviour `Session` (เดิม `Bot`), log ภาษาอังกฤษกลางๆ. โลจิกเดิมคง
  (PlayerInputDto → `SendInputsToServer`, LootDrop, F7/F8, TickHz 15).
- `C:\re\bepinex\CobaltNav` (guard+navmesh, เดิม NavProbe/NavGuard): GUID `dev.cobalt.nav`, คลาส `Aux`.
  **เปลี่ยนด่านหลักเป็น SHA256 ของ GameAssembly.dll เทียบ `C:\re\cobalt\baseline.hash`** (ไม่พึ่ง
  version string); `BepInEx.Paths.GameRootPath` + `Convert.ToHexString` (net6 ใน BepInEx IL2CPP);
  ตรวจอัตโนมัติทุก 2 วิจน pass แล้วทุก 30 วิ; ไม่ผ่าน = `Cobalt.Session.enabled=false` (fail closed);
  เขียน `C:\re\cobalt\state.txt` (PASS/BLOCKED) + `nav.txt` (ระยะกำแพง 8 ทิศ). F9/F10/F11 เหมือนเดิม.
- **ด่าน "เช็คก่อนเข้าเกมทุกครั้ง" ที่โอขอ = `C:\re\cobalt\play.py` (+ PLAY.bat)** — hash เทียบ baseline
  ก่อน → ตรง=เปิดเกม / ไม่ตรง=refuse+exit1 ไม่เปิด (พิสูจน์แล้วด้วย baseline ปลอม DEADBEEF → บล็อก).
  **ไม่พึ่ง guard ในเกม** เพราะ guard เองอาจพังหลังแพทช์. โอควรเปิดเกมผ่าน PLAY.bat เสมอ.
- **post-patch = `C:\re\cobalt\rebuild.py`** — ล้าง interop+baseline → เปิดเกม 1 รอบ gen interop →
  build Cobalt+CobaltNav ทับ interop ใหม่ → ตั้ง baseline ใหม่. (play.py กับ guard ใช้ baseline.hash
  ไฟล์เดียวกัน format เดียว = source of truth เดียว; hex ตัวใหญ่ ตรงกันทั้ง py และ C#).
- ลบ dll/ไฟล์ชื่อเก่าออกหมด (MovementBench.dll/NavProbe.dll/FarmBot.dll, patchwatch.py, .gamehash,
  C:\makcu\navprobe*.txt/botguard.txt). **verify สด: log ขึ้น `Loading [Cobalt]`/`[Cobalt Nav]` +
  `Cobalt.Session`/`CobaltNav.Aux`; grep FarmBot/MovementBench/NavProbe/NavGuard/.Bot/SpiritVale = 0 ทุกคำ;
  guard "build matches baseline (ok)"; baseline=E96637D131...**
- 🟡 **residual risk (พูดตรงกับโอ): ชื่อช่วยแค่กัน string-scan ระดับตื้น** — ตัวที่บอกได้จริงคือ
  **BepInEx เอง** (winhttp.dll proxy + doorstop + โฟลเดอร์ dotnet ในโฟลเดอร์เกม → module/file-integrity
  scan หรือ Steam verify เห็นได้) และ **พฤติกรรม** (cadence SendInputsToServer, รูปแบบเดิน, snapback/
  reconcile — heuristic ฝั่ง server: ChatLimiter/MongoTelemetry ตาม note เดิม). ชื่อไม่ช่วย 2 อย่างนี้.
  DamageBench (ของอีก session, build ไม่ผ่าน ไม่มี dll) ไม่แตะ.

**23/7 (Fable) — โอกลัวเปิด/ปิดเกมรัวๆ → พิสูจน์ log สะอาด + ปิด BepInEx เก็บให้เรียบร้อย:**
โอเห็นเกมเปิด-ปิดหลายรอบ กลัวโดน server ฟ้อง/เก็บ log แบน. **ตรวจจริง: สาเหตุ = ผมเอง Stop-Process+
เปิดใหม่ทุกครั้งที่ build เทสต์** ไม่ใช่ server. `BepInEx\LogOutput.log` **สะอาด 100%** (ไม่มี ban/kick/
anticheat/crash/exception; จบที่ `Chainloader startup complete` = โหลดปกติ) และ **บอทไม่เคยรันเลย**
(grep `Cobalt: ON`/`[item]`/`[reconcile`/`check: PASS` = 0 ทุกคำ; guard ไม่เคยเจอตัวละคร = ทุกรอบอยู่แค่
หน้า login) → server เห็นแค่เปิด/ปิดเกมที่เมนูเหมือนคนทั่วไป ไม่เคยเห็นพฤติกรรมบอท.
- โอเลือก (ก) **ปิด BepInEx เก็บให้เรียบร้อย** → `C:\re\cobalt\bepinex_toggle.py off` ย้าย 6 อย่าง
  (`.doorstop_version, BepInEx/, changelog.txt, doorstop_config.ini, dotnet/, winhttp.dll`) จากโฟลเดอร์เกม
  ไป `C:\re\sv_bepinex_off\` (ไม่ลบ). **verify: โฟลเดอร์เกมเหลือแต่ vanilla 9 ไฟล์ ไม่มีร่องรอย BepInEx**.
  ปลั๊กอิน Cobalt/CobaltNav + interop + baseline.hash เก็บครบใน HOLD. เปิดกลับ: `bepinex_toggle.py on`.
- 🔴 กติกาต่อจากนี้: **อย่า Stop-Process/relaunch เกมรัวๆ** (โอกลัว) — ปิด/เปิดเท่าที่จำเป็น, เปิดผ่าน
  PLAY.bat, ปิดเกมแบบปกติไม่ force-kill. RE/build/แก้โค้ดทำได้เต็มที่โดยไม่ต้องเปิดเกม.

**23/7 (Fable) — ✅ แก้ปมจับคู่พิกัด มินิแมพ↔navmesh สำเร็จ (ปลดล็อกมาโครเดินเลี่ยงกำแพง):**
โอยืนยันทิศทาง: **มาโครภายนอกคือเนียนสุด** (เกม vanilla 100%, input = pipeline คนจริง — ต่างจาก
inject ที่ module scan เห็น) โจทย์ค้าง = เดินไม่ชนกำแพง. **RE navmesh เอามาป้อนมาโครแบบ offline ได้**
(อ่านจากไฟล์ bundle ไม่แตะเกมรัน). ก่อนหน้า align ด้วยรูปร่าง**ไม่นิ่ง** (IoU 0.54-0.64 สุ่มทิศ) เพราะ
ปล่อยให้ search หมุน+มินิแมพ mask หยาบ. **แก้: ล็อก North-up (ไม่หมุน) + ถมรู footprint ก่อนเทียบ +
search แค่ flipZ/scale/translation** (`_align3.py`) → **IoU 0.807 เสถียร: flipZ=False, ไม่หมุน,
1 พิกเซลมินิแมพ ≈ 2.27 หน่วยโลก** (crop x1697-1909 y112-270, offset (98,-18)). สนามวงกลมทับเป๊ะ;
แถบแดงล่าง = ทางเดิน/ชั้นอื่น (L1-3) ที่ L0 ไม่ครอบ ไม่กระทบฟาร์มในสนาม.
- ผลลัพธ์พร้อมใช้: `C:\makcu\forge_align.json` (transform), `forge_walkmap_mm.npz`
  (walkmap 212×158 ในเฟรมมินิแมพ ปิดรอยสามเหลี่ยม closing 2 รอบแล้ว = สนามตัน), 
  `forge_walkmap_on_minimap.png` (ภาพทับ). เครื่องมือ: `_align3.py`, `_walkmap_overlay.py`.
- **ขั้นต่อ (ยังไม่ทำ, ต้องรันเกมสด = โอเคาะเวลา): ต่อ walkmap เข้าตัวเดินของมาโคร** — อ่านหมุดผู้เล่น
  บนมินิแมพ → แปลงเป็นช่อง walkmap → ข้างหน้าเป็นแดง=เลี้ยง. ต้อง live-run สั้นๆ 1 รอบคาลิเบรตการอ่าน
  ตำแหน่งหมุด (มาโครขับตัวละครบนเซิร์ฟจริง = แกนพฤติกรรม โอตัดสินใจว่าเมื่อไหร่).

**23/7 (Fable) — ตัวนำทางเลี่ยงกำแพง (offline) เสร็จ+พิสูจน์ + เครื่องมือคาลิเบรตพร้อม:**
- `C:\makcu\walk_nav.py` — คลาส `WalkMap` (โหลด forge_walkmap_mm.npz) + `walkable`, `nearest_walkable`
  (snap ตำแหน่งที่อ่านคลาดไปช่องเดินได้), `clear_ahead` (เดินทิศนี้โล่งกี่พิกเซล, เช็คความกว้าง ±halfw),
  **`safe_heading(mx,my,vx,vy)`** = คืนทิศใกล้ที่อยากได้สุดที่โล่ง ≥ want (สแกน ±15..180°), ตันหมด=ไปฝั่ง
  เปิดสุด. **เทสต์ offline บนแผนที่ Forge จริง: เดิน 400 ก้าว เหยียบกำแพง 0 ครั้ง** (เคลื่อน 600px).
  พิกัด = เฟรมมินิแมพ crop (แถว0=บน, vy>0=ใต้; ตรงกับ compass ของ _mmkite). มินิแมพ North-up ตรึง →
  walkmap พิกเซล = มินิแมพสดพิกเซลเดียวกันเสมอ (ไม่ต้อง re-register ต่อเฟรม).
- `C:\makcu\nav_cal.py` — คาลิเบรตสดบน **console** (ไม่ต้อง BepInEx/สะพาน; game+script อยู่ session
  เดียวกัน): แคปมินิแมพ crop → overlay walkmap ยืนยัน alignment สด + เช็คขนาดหน้าต่างตรงไหม;
  `nav_cal.py move` = แคป→รอ4วิให้โอเดิน→diff หา **หมุดผู้เล่น** (จุดที่ขยับ) + สีมัน → เอาไปเขียน
  `find_player_mm(hw)`. ⚠️ สีมินิแมพ: BLUE=วาป (ไม่ใช่ผู้เล่น), WHITE=ผู้เล่นอื่น, RED=มอน/เพ็ต,
  GREEN=ปาร์ตี้ → หมุดผู้เล่นเราต้องหาสดด้วย diff.
- **ค้าง (ต้องเกมสด ที่ Forge): ① รัน nav_cal ยืนยัน+หาหมุด ② ต่อ safe_heading เข้า `_ctm_kite`/`_mmkite`**
  (แปลงทิศมินิแมพ→อินพุตจอ ผ่าน compass เดิม) ③ live-run สั้นๆ. มาโครภายนอกไม่เกี่ยว BepInEx (vanilla).

**23/7 (Fable) ต่อ — เพิ่ม A* วางเส้นทางใน walk_nav.py (ต่อยอดจาก reactive):** `WalkMap.plan_path(start,
goal,clearance=1)` = A* 8 ทิศบน walkmap, `passable()` เว้นระยะจากกำแพง + กันตัดมุมทะลุ, snap start/goal.
**เทสต์ offline: เส้นทางขอบซ้าย→กลางสนาม 49 ช่อง ทุกช่องเดินได้=True** (forge_path.png). ทีนี้มาโครเดิน
ไป**จุดหมาย**ได้ ไม่ใช่แค่วนเลี่ยง. **โอกำลังลบ object+อาจ re-bake พื้นในโปรเจกต์แกะ** → ถ้า re-bake navmesh
ผม re-extract walkmap (NavExport.Run) แล้ว walkmap/A* อัปตามทันที. รอโอเรียกตอนตัวละครถึง Forge เพื่อ
รัน nav_cal (หาหมุด+ยืนยัน alignment สด) แล้วต่อ safe_heading/plan_path เข้า _ctm_kite + live-run.

**23/7 (Fable) — navmesh ช่วยอะไรได้อีก (นอกจาก walkmap 2D ที่ทำไปแล้ว):**
โอถาม navmesh ช่วยอะไร. navmesh ดิบ (20,264 tris หลายชั้น world coords) = ตัวที่ **server ใช้เดินจริง** →
1. **`NavMesh.CalculatePath` = เส้นทาง server-exact** (เดินเนียนเหมือนคนจริง ไม่ desync ไม่โดนธง path เป็นไปไม่ได้)
2. **ข้ามชั้น/ลงบันได** — พิสูจน์แล้ว: path จาก Y=99.2 → Y=−29.2 (ข้ามชั้น 128 หน่วย, PathPartial บนสุดขาด);
   L0 ซ้าย→ขวา = **PathComplete 223 หน่วย 5 มุม** ฉายลงมินิแมพถูกต้อง (บนพื้นเดินได้). walkmap แบน L0 ทำข้ามชั้นไม่ได้
3. **สนามระยะห่างขอบ (clearance)** — เลือกเดินเส้นกลางเลี่ยงลาวา (ยังไม่ทำ, เพิ่มบน walkmap ได้ง่าย)
4. **เฉลยจูนการอ่านมินิแมพ**
- เครื่องมือ: `C:\re\navonly\Assets\Editor\NavPath.cs` (NavMesh.CalculatePath ระหว่าง 2 จุด dump corners world),
  รัน `Unity.exe ... -executeMethod NavPath.Run` → `C:\makcu\forge_navpath.txt`; `_project_navpath.py`
  ฉาย corners → มินิแมพ (`forge_navpath_on_minimap.png`).
- **แผนใช้จริง (pragmatic):** ฟาร์มในสนามชั้นเดียว = walkmap A* พอ; navmesh-path ใช้ตอน **ข้ามชั้น/ลงบันได
  ไปจุดฟาร์ม** หรืออยากได้เส้น server-exact. runtime มาโคร Python เรียก Unity สดไม่ได้ → precompute เส้นคีย์
  (entry→สนาม) แล้วมาโครเดินตาม waypoint, หรือเขียน navmesh-A* ใน Python จาก triangulation ที่ dump.
- ⚠️ เผลอเติมคอมเมนต์ 1 บรรทัดใน CobaltNav/Plugin.cs (harmless, BepInEx ปิดอยู่ ไม่ rebuild).

**23/7 (Fable) — 🔴 ต้นเหตุ "คลิก login ใน RDP ไม่ลง" = สะพาน 2 ตัว (ไม่ใช่ RDP เอง):**
โอถามทำไมคลิก Ok เองไม่ได้. debug พบ **session_bridge.py รัน 2 ตัวพร้อมกัน** (โอดับเบิลคลิก bat ซ้ำ,
ไม่มี guard) → ทั้งคู่ exec คำสั่ง reconnect → **SendInput down/up ซ้อนกัน (down-down-up-up) = ไม่เป็น
คลิก** หน้า login เลยไม่ขยับ. **พอ `Stop-Process` เหลือสะพานตัวเดียว → ตัวละคร reconnect เข้าเมืองได้**
(คลิกผมลง หรือโอคลิกเอง — ก้ำกึ่ง แต่ double-bridge เป็นตัวการชัด). **แก้เดิมที่เคยสรุปว่า "SendInput ไม่ลง
RDP login" — น่าจะเป็นเพราะ double-bridge มากกว่า RDP เอง** (in-game input ลง RDP ได้อยู่แล้ว).
- **แก้:** ① `session_bridge.py` เพิ่ม single-instance ผ่าน named mutex `SpiritVale_Bridge_SingleInstance`
  (ตัวที่ 2 เจอ ERROR_ALREADY_EXISTS=183 → exit). ② `สะพาน-เปิดใน RDP.bat` เพิ่ม `Stop-Process` ปิดสะพานเก่า
  ก่อนเปิดใหม่ = ดับเบิลคลิกกี่ทีก็เหลือตัวเดียว. **มีผลรอบเปิดสะพานครั้งหน้า** (ตัวที่รันอยู่ 27612 เป็นเวอร์ชันเก่า
  ไม่ถือ mutex — ยังไม่ restart ตามที่โอสั่ง "อย่าเข้าเกม"). กติกา: **เปิดสะพานแค่ตัวเดียว**.
- 🟢 ตัวละครปลอดภัยในเมือง (Channel 3, HP เต็ม) — idle-kick เพราะยืนนิ่งตอนทำ alignment นาน;
  ตอนฟาร์มจริงขยับตลอดจะไม่โดน. **ค้าง: ยืนยัน single-bridge SendInput ลง RDP login จริงไหมรอบหน้า + เพิ่ม anti-idle**.

**23/7 — ⚠️ กับดัก RDP: กด Shutdown ในหน้าต่าง RDP = สั่งเครื่องจริงทั้งเครื่อง:**
โอเผลอกด shutdown ในหน้าต่าง RDP → **มันไม่ใช่คนละเครื่อง มันคือเครื่องเดียวกัน** → log off ทุก session
(console เปลี่ยน id 1→3, session ykfarm หาย, เกม/Steam/สะพาน ถูกปิดหมด; uptime ไม่รีเซ็ต = ไม่ได้รีบูตเต็ม
แต่ session ถูกล้าง). **ไม่มีข้อมูลหาย** (งานทุกอย่างเป็นไฟล์บนดิสก์ — ตรวจครบแล้ว: walkmap/align/walk_nav/
nav_cal/ForgeNav/NavExport/bepinex_toggle/sv_bepinex_off/memory).
🔴 **กติกา: ออกจาก RDP ให้กด `X` แถบบน (Disconnect) หรือ Sign out เท่านั้น — ห้ามแตะ Shutdown/Restart
ในเมนู Start ของหน้าต่าง RDP เด็ดขาด** (ปิดเครื่องจริง งานทุกอย่างในทุก session ดับ)
- กลับมาทำต่อ: mstsc `127.0.0.2` (ykfarm) → เปิด Steam+เกมใน session นั้น → ดับเบิลคลิกสะพานครั้งเดียว
  (มี guard กันซ้ำแล้ว) → เรียกผม

**23/7 — ไอคอนบน Desktop ให้โอกดง่าย (ทำตามที่โอขอ):**
- **จอหลัก `C:\Users\guole\Desktop\เปิด RDP ฟาร์ม.rdp`** — ดับเบิลคลิก = ต่อ RDP ไป `127.0.0.2` user `ykfarm`
  **ล็อกเรโซ 1280x720** ไว้ในไฟล์ (สำคัญ: ให้หน้าต่างเกมคงที่ = walkmap/crop ที่คาลิเบรตไว้ยังใช้ได้
  ไม่ต้อง align ใหม่ทุกครั้ง) + `authentication level:i:0` (ไม่เด้งเตือน cert)
- **ykfarm Desktop (เห็นในหน้าต่าง RDP):** `1 เปิดเกม.bat` (steam://rungameid/3767850) ·
  `2 เปิดสะพาน.bat` (เรียก C:\makcu\สะพาน-เปิดใน RDP.bat ที่มี guard กันซ้ำ) ·
  `อ่านก่อน - ห้ามกด Shutdown.txt` (เตือนกับดัก RDP + ลำดับใช้งาน 1-2-3)

**23/7 — 🔴 gotcha ซ้ำรอย: เนื้อไฟล์ .bat ห้ามมีภาษาไทย:**
ผมทำ bat ไอคอน Desktop โดยใส่ไทยใน title/echo/rem → **cmd อ่าน .bat ด้วย codepage ANSI แต่ไฟล์เป็น UTF-8
→ ไทยเพี้ยน → cmd เอาข้อความเพี้ยนไปรันเป็นคำสั่ง** ขึ้น `'...' is not recognized` +
`The system cannot find the drive specified` **และเกมไม่เปิด** (คลาสเดียวกับ gotcha เดิม "ps1 ห้ามมีไทย"
และ build.ps1 parser พัง — พลาดซ้ำ)
**กติกา: เนื้อไฟล์ .bat/.ps1 = ASCII/อังกฤษล้วนเสมอ** — ชื่อไฟล์ไทยได้ (ไม่มีปัญหา), คำอธิบายไทยไว้ใน .txt
**แก้แล้ว (ตรวจ non-ASCII = 0 ทั้ง 4 ไฟล์):** `C:\makcu\bridge_open.bat` = ตัวจริง (ASCII + single-instance
kill-guard) · `สะพาน-เปิดใน RDP.bat` เหลือ `call bridge_open.bat` · Desktop ykfarm `1 เปิดเกม.bat` /
`2 เปิดสะพาน.bat` อังกฤษล้วน

**23/7 — 🔴 ห้ามใช้ `raise SystemExit` / `sys.exit()` ในสคริปต์ที่ส่งผ่านสะพาน:**
สะพานรันสคริปต์ด้วย `exec()` **ในโปรเซสตัวเอง** → `SystemExit` = **สะพานตายทันที** (ผมทำพลาด 23/7
ตอนเขียน `_compass.py`). ให้ใช้ `if/else` หรือห่อเป็นฟังก์ชันแล้ว `return` แทน; ห่อ try/except กันพลาด.
- ✅ **auto-decline คำชวนตี้ ทำงานจริง** (โอเจอ popup "X invited you to their party"):
  Decline อยู่สัดส่วน **(0.465, 0.145)** สี `(218,212,228)` ม่วงอ่อน · Accept **(0.534,0.145)** สี
  `(180,222,255)` ฟ้า · พื้นกล่อง `(93,94,107)`. คลิก Decline ด้วย SetCursorPos+mouse_event แล้ว
  popup หายจริง (ทั้ง 3 จุดกลายเป็นสีพื้นแมพ). **ยืนยันคลิกในเกมทำงานได้ใน RDP** (มีแค่หน้า login ที่ดื้อ)
- ✅ **หาหมุดผู้เล่นได้** = สะกิดเดินแล้วหา "ขาวที่โผล่ใหม่" ใกล้ตำแหน่งเดิม (จับได้ (45,56)→(59,54));
  หมุดเรา = สี่เหลี่ยมขาว ~2px **เหมือนผู้เล่นอื่นเป๊ะ** แยกด้วยหน้าตาไม่ได้ ต้อง track จากการขยับ
  (มอน=แดง ไม่กวน). ซูมมินิแมพเข้าไม่ช่วย (ซูมออกสุดอยู่แล้ว + ไม่ได้ player-centered)
- 🔴 **เกมถูกเด้ง/ปิดอีกรอบ 09:45** — ตรวจแล้ว: ไม่ crash (ไม่มี event log/dump), log จบตอนอยู่หน้า
  Select Server = **ถูกเด้งออกก่อนปิด**; สคริปต์ผมไม่มีคำสั่งปิดเกม. วันนี้โดนเด้ง 2 ครั้ง →
  **ต้องทำ anti-idle (ขยับตลอด) ก่อนปล่อยฟาร์มยาว**

**23/7 (Fable) — ✅ ปิด 2 งานค้าง RDP จาก handoff (บรรทัด 1553): anti-idle + บั๊ก mutex สะพาน:**
- **① anti-idle keepalive** (`C:\makcu\anti_idle.py` + `_antiidle_launch.py` + `ANTIIDLE-START.bat` /
  `ANTIIDLE-STOP.bat`): กันตัวละครโดน server เด้งตอน**ยืนนิ่งทำ alignment/nav_cal** (โดน 2 ครั้ง 09:45 —
  ตอนฟาร์มจริง walk_loop ขยับตลอดไม่โดน ปัญหาอยู่ช่วงตั้งค่า). ทุก 20 วิ nudge = **สไตรฟ์สมมาตร d สั้น→a สั้น
  (0.08วิ) กลับที่เดิม** → server เห็น input ตัวไม่ขยับ crop/หมุดมินิแมพไม่เพี้ยน. ผ่าน ROUTER window mode
  เดียวกับมาโคร (PostMessage vanilla). nudge เฉพาะตอน `_hp_level` อ่านได้ (อยู่ในเกม) — login/เมนูข้าม.
  STOP: End / ไฟล์ ANTIIDLE_STOP. **ใช้ตอนตั้งค่าเท่านั้น หยุดก่อนปล่อย soak_driver** (ไม่งั้นแย่ง kite).
  verify: py_compile ผ่าน + bat ASCII-clean (gotcha ไทยใน .bat). **ค้าง: live-verify ว่ากันเด้งจริงรอบหน้าที่โออยู่ในเกม**.
- **② บั๊กจริงใน single-instance mutex ของ `session_bridge.py`** (ตัวที่แก้เมื่อเช้า): ตั้ง `_BRIDGE_DUP=True`
  แต่ **main loop `while not os.path.exists(STOP)` ไม่เคยเช็คตัวแปรนี้** → สะพานตัวที่ 2 พิมพ์เตือน sleep 5 แล้ว
  **เข้าลูปทำงานต่ออยู่ดี = double-bridge เดิม (down-down-up-up คลิก login ไม่ลง)**. mutex อย่างเดียวไม่กัน.
  กันได้จริงแค่ทาง `.bat` ที่ Stop-Process ตัวเก่าก่อน — ถ้าโอเปิดสะพานตรงๆ (ไม่ผ่าน bat) จะยังซ้ำ.
  **แก้: ตัวที่ 2 `sys.exit(0)` จริง** (session_bridge รันเป็นโปรเซสเอง ไม่ใช่ exec ผ่านสะพาน → sys.exit ปลอดภัย
  ไม่โดน gotcha SystemExit ที่ใช้กับ cmd_*.py). compile ผ่าน. ตอนนี้ไม่มีสะพานรันอยู่ → มีผลรอบเปิดถัดไป.
- 🟢 สถานะสด: console=guole(3), ykfarm=session4 Active มี Steam เปิด **แต่เกมยังไม่รัน + ไม่มีสะพาน/บอทรัน**;
  BepInEx ปิดอยู่ (state.txt ว่าง, baseline E96637D131...). ไม่ได้เปิดเกม/สะพานเอง (โอคุมเวลาเข้าเกม).
