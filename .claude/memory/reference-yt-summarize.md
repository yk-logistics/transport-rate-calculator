---
name: reference-yt-summarize
description: "Summarize YouTube clips/livestream-VODs in Thai for free — yt-dlp pulls captions, Qwen summarizes, Claude pays no tokens to \"watch\""
metadata: 
  node_type: memory
  type: reference
  originSessionId: ab0816d5-66a6-42c8-a9b2-4a942fda6c63
---

Claude can't watch YouTube directly (unlike Gemini). Tool at `_Claude Tools/yt-summarize/` works around it: yt-dlp pulls the clip's captions → plain text → [[reference-qwen-subagent]] (free 9arm Qwen) summarizes to Thai. Opus pays 0 tokens for the heavy read.

Run (PowerShell, from repo root):
```
python "_Claude Tools\yt-summarize\yt_summary.py" "<url1>" ["<url2>" ...]
```
Output: `_Claude Tools/yt-summarize/out/<videoid>.summary.th.md`. English clips summarized to Thai too. Batch = multiple URLs in one call (confirmed working 2026-06-18, English test clip → correct Thai summary).

Files: `get_transcript.py` (captions→clean text, usable alone), `yt_summary.py` (full pipeline), `README.md`.

**Hard limits:**
- Clip MUST have captions (manual OR YouTube auto-sub). Captions-off + no auto-sub → `NO_SUBTITLES`, can't summarize (would need to download+transcribe audio — not built).
- Live-while-streaming may lack full transcript; wait for the VOD.
- Very long clips (multi-hour lives) truncated at ~280k chars to avoid Qwen's 128k context overflow.

**Encoding gotcha that bit us:** all logic kept in Python UTF-8, NOT a .ps1 — PowerShell 5.1 misreads a UTF-8-no-BOM .ps1 containing Thai as ANSI → mojibake → parse error. PowerShell is only a thin launcher for qwen.ps1; the Thai prompt is passed via a temp file read with `[Text.Encoding]::UTF8`. yt-dlp installed via pip (no ffmpeg/JS-runtime needed for caption-only).
