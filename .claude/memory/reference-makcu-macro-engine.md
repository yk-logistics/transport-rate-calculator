---
name: reference-makcu-macro-engine
description: "Location + nature of โอ's personal macro_engine.py (Makcu KM tool) — NOT part of Project YK"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 94b005b6-f022-41d3-8493-a8b53b6e9bb0
---

โอ's personal side-project, separate from Project YK business app.

**Path:** `C:\Users\guole\Desktop\2026.5.28\Desktop\_NonYK_Projects\makcu\macro_engine.py`
(Note: it is NOT under the Project YK repo — glob from the YK cwd will NOT find it. Search `_NonYK_Projects\makcu`.)

**What it is:** Tkinter GUI macro tool that drives a Makcu KM-injector over serial
(`km.move(dx,dy)`, `km.left/right/middle(1|0)`, `km.wheel(n)` at 4 Mbaud) plus the
`keyboard` lib for global hotkeys. Has Macros tab + Walk Profiles tab (counter-rotation
auto-walk with per-key + per-diagonal gains: gain_{w,a,s,d,wa,wd,sa,sd}_{dx,dy}).

**Active work (2026-06-11):** โอ wants to replace the Makcu with a **Waveshare RP2350-USB-A**
board (RP2350A, USB-C device + USB-A host, ~200-400฿ vs Makcu's ~1500-3500฿). Plan: flash
firmware that speaks the SAME serial protocol (`km.move/left/right/middle/wheel`), so
macro_engine.py needs zero changes — just point at the new COM port.

IMPORTANT findings: CircuitPython has NO official board page for RP2350-USB-A, and the
Waveshare wiki warns that flashing a generic Pico2/RP2350 firmware can make the board's
USB-A host port undetectable (it uses Pico-PIO-USB, needs special config). The stock demo
(`host_hid_to_device_cdc`) does the OPPOSITE of what we want (reads a real mouse, prints to
CDC) — not injection.

DECISION: wrote a **C / Pico SDK + TinyUSB firmware, DEVICE-ONLY** (USB-C HID mouse + CDC
only; USB-A host port unused) → sidesteps all the fragile host patches. Lives at
`_NonYK_Projects\makcu\rp2350_firmware_c\` (main.c, usb_descriptors.c, tusb_config.h,
CMakeLists.txt, pico_sdk_import.cmake, build.ps1, README.md). PICO_BOARD=pico2.
The earlier CircuitPython `rp2350_firmware/` folder was DELETED (wrong approach).

Toolchain: โอ installed the **Pico VS Code extension** and did Import Project, which pulled
`~/.pico-sdk/` (sdk 2.2.0, toolchain 14_2_Rel1, cmake v3.31.5, ninja v1.12.1, picotool 2.2.0-a4).
The extension prepended its own header to CMakeLists.txt + overwrote pico_sdk_import.cmake — kept.
GOTCHA fixed: extension defaulted PICO_BOARD to rp2040/pico; must set `PICO_BOARD pico2` +
`PICO_PLATFORM rp2350` as CACHE vars at the TOP of CMakeLists.txt BEFORE the pico-vscode.cmake
include, else it builds for the wrong chip.

**DEVICE-ONLY build SUCCEEDED + TESTED 2026-06-11**: flashed, `move 200 0` moved the cursor →
device side (descriptors, km.* parser, HID inject) all confirmed working. Board enumerated on COM5.

**DUAL-MODE build SUCCEEDED 2026-06-11** → `rp2350_firmware_c/makcu_km_DUAL.uf2` (119 KB). Adds
USB-A HOST passthrough via Pico-PIO-USB (cloned into project), so a real mouse plugged into USB-A
works AND macro_engine can inject km.move on top. Architecture: core1 = host (PIO, D+=GPIO12), core0
= device (native USB-C) + CDC parser. Buttons OR'd: g_phys_buttons|g_cmd_buttons. SDK 2.2.0 already
fixed the hcd_edpt_abort_xfer/hcd_frame_number undefined-ref the forums warned about — no SDK patch
needed. CMake pattern: add_subdirectory(Pico-PIO-USB), compile dcd_pio_usb.c+hcd_pio_usb.c from
PICO_TINYUSB_PATH into target, defines PIO_USB_DP_PIN_DEFAULT=12 + PIO_USB_USE_TINYUSB.

HARDWARE: R13 is NOT a problem on โอ's board — DUAL flashed, plugged Logitech PRO X2 dongle into
USB-A, cursor MOVED. So host passthrough works and R13 was already fine (no desolder needed). 🎉

SOLVED axes 2026-06-11: PRO X2 report layout (13 bytes) = btn@0, X int16le@2-3, Y int16le@4-5,
wheel@6. Parse by offset (RPT_*_OFS in main.c), don't cast hid_mouse_report_t. After fix: L/R/U/D +
left/right click + scroll all work.

STILL BROKEN: (a) side buttons Back/Forward + middle/wheel-click don't pass; (b) G Hub doesn't see
the mouse (we present generic VID 0xCafe, not Logitech); (c) residual double-click + drag latency.

DECISION 2026-06-11 (max-effort review): root cause of (a)+(b) = we re-emit a GENERIC HID report
instead of transparently cloning the real mouse. Found ref impl **VoltCyclone/Hurra** (github,
branch master) = KMBox-style RP2350 passthrough that does dynamic descriptor clone + re-enumeration,
accepts km.move()/km.left() TEXT protocol (macro_engine works as-is), 300MHz. Its USB host pins are
GPIO16/17 on Metro but configurable; for our board use D+=GPIO12/D-=GPIO13. BUT Hurra is huge
(usb_hid.c 133KB, plus Xbox emu / TFT / dual-board bridge / humanization we DON'T need). PLAN agreed
with โอ: keep OUR small firmware, READ Hurra's clone logic as reference, implement descriptor-clone +
re-enumeration ourselves cleanly. humanization stays on PC side (macro_engine smooth_move+jitter);
future aim-assist = PC computes km.move, firmware just injects. Also TODO: edge-track buttons (not
overwrite latch) to kill double-click; raise clock 120→240/300MHz for latency.

NEXT STEP: capture is lost (temp cleaned). Rebuilt `makcu_km_DESCDUMP.uf2` with BOTH
DEBUG_DUMP_DESCRIPTORS=1 and DEBUG_DUMP_REPORTS=1. read_hex.py now saves to capture.txt (permanent).
โอ flashes DESCDUMP, runs read_hex.py COM5, re-plugs mouse (dumps desc) + presses side buttons
(dumps their report bytes). Then read capture.txt → design the clone.

Fable reviewed the code 2026-06-11 and fixed ~8 stability bugs: makcu_* serial writes now
wrapped in try/except (USB unplug no longer crashes threads), WalkRunner.stop_now joins the
thread before restart (no double-walk fight), keyboard.is_pressed wrapped, all_stops leak
fixed via _drop_stop, _test_once routed through _spawn for PANIC.

2026-06-14: added `holdkey` macro mode (press trigger once -> hold a key/combo down, press
again -> release; auto-released on panic/disable/close via _release_all_holdkeys + self.holdkeys).
Steps line 1 = key(s) to hold, e.g. `c` or `ctrl+shift`. Trigger MUST differ from the held key.

2026-07-11 BUGFIX PASS (Fable, full-file review): ① single-key triggers now EDGE-DETECTED
(on_press_key + on_release_key pair per hook; typematic repeats while key held no longer
re-fire 'once', flap 'toggle', or spawn duplicate hold/sequence loops — previously any repeat
>80ms after last accepted fire slipped past the leading-edge debounce; self-heal: press >1.5s
after last down = fresh press even if release was missed). ② Listboxes exportselection=False
(drag-selecting text in Steps cleared list selection → Save Macro APPENDED a duplicate).
③ _new_macro/_new_walk use deepcopy (shared steps lists). ④ _save now atomic (tmp+os.replace);
corrupt macros.json is backed up to .corrupt.bak instead of being silently overwritten by sample.
⑤ keyboard.is_pressed via _kb_key scan code in hold/sequence/auto-WASD (Thai layout safe).
⑥ COM port persisted in settings (was hardcoded COM3 default; board is COM5). ⑦ _ival() guards
IntVar reads (empty spinbox no longer silently kills Save under pythonw) + report_callback_exception
shows Tk errors on status bar. Verified: py_compile + 19-check smoke test (scratchpad) incl. App()
build; live typematic behavior still needs a real-key test by โอ.

2026-07-12 ROUND-4 FEATURES (โอเลือก 3): ① tray — X hides window (macros keep running),
pystray icon created lazily on first hide from macro_engine.ico, menu Show(double-click)/
Enable toggle/PANIC/Exit; tray callbacks marshal via self.after; no pystray → X quits as before.
② mouse side buttons as triggers: names "mouse4"/"mouse5" (lib `mouse` → x/x2), fire on DOWN
(no typematic on mouse buttons, no edge state needed); trigger_is_pressed() helper makes
hold/sequence modes work with them; Set capture button now also catches x/x2. ③ En.key field
in top bar = global ENABLE/DISABLE toggle hotkey (blank=off, persisted as enable_key, chirps
high/low, re-registered in _reset, Set-capturable). **Deps: pip installed pystray + mouse into
Python312 — reinstalling Windows needs both.** Smoke test 44 checks ALL PASS incl. real tray
create+stop (process exits clean). Live-untested: tray double-click UX, mouse4/5 in real game.

2026-07-11 ROUND-3 REVIEW: fixed ① RESET hook leak (pre-existing since the June on_press_key
change): unhook_all_hotkeys() doesn't remove on_press_key/on_release_key HOOKS, and _reset
discarded the remove() callables → every RESET press stacked another live hook per trigger+panic
= triggers fired 2x/3x/... after resets. Now _reset calls _unregister_triggers()+_unregister_panic()
first. ② auto-connect fresh-config guard: want_conn defaults ON only when settings already contain
com_port (a past successful connect); never BAUD_INIT-pokes default COM3 blind. Smoke test now 34
checks ALL PASS (incl. handler-count stability across 3 resets). Known-remaining (accepted): combo
(ctrl+x) triggers still go through add_hotkey → typematic re-fire >80ms while held (single keys are
edge-detected); PixelPicker is primary-monitor only; capture button doesn't mute active triggers.

2026-07-11 FEATURES (โอเลือกครบ 4 ชุด): ① "Set" buttons capture trigger by tapping the key
(macro/walk/panic; SCAN_TO_NAME reverse map → canonical US name, layout-safe) + lint_steps()
static check gates Save Macro (skips holdkey mode — its line 1 is a bare key). ② beep()
high/low on toggle/holdkey/walk on/off + beep_panic(), gated by Beep checkbox (persisted);
Log tab (3rd notebook tab) + App.log() + module-level LOG routed via _set_logger (pythonw
has no console). ③ per-macro/walk "enabled" flag (checkbox + [OFF] in list, skipped in
_register_triggers) + Copy button (blank trigger on copy) + ^Up/vDown reorder. ④ auto-connect:
_conn_watch every 3s via serial.tools.list_ports — connects on launch/replug when want_conn
(persisted as auto_connect; user Disconnect sets False), detects unplug → "(unplugged)".
Verified: 30-check smoke test ALL PASS. NOT yet live-tested by โอ (beeps in-game, capture UX,
replug cycle).

2026-06-14 FIXED "trigger doesn't fire reliably" (โอ had to hit RESET often). TWO bugs: (H2) the
sliding-window debounce refreshed last_fire on EVERY event incl. typematic repeats, so a held key
kept the 80ms window open and swallowed the next real press — changed to leading-edge (don't refresh
on dropped events) in both macro & walk runners. (H1, the big one) bind_hotkey used
keyboard.add_hotkey(scancode) which degrades after many suppress/unhook cycles and silently stops
firing; single-key triggers now use keyboard.on_press_key(scancode, lambda e: callback()) which
hooks the raw key event and is stable. bind_hotkey now ALWAYS returns a no-arg remove() callable;
_unregister_triggers / _unregister_panic call h() instead of keyboard.remove_hotkey(h). Verified via
console log: '-' '=' backslash ']' all fire every press now.
