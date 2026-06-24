---
name: reference-server-no-gpu-llm
description: "YK server (.197) has no discrete GPU — not worth self-hosting an LLM on it; use this to shut down repeat \"let's run our own LLM on the server\" proposals"
metadata: 
  node_type: memory
  type: reference
  originSessionId: de7755ef-cda3-4b02-86f2-6b27483ebf6a
---

The YK server at app.yklogistics.uk (Tailscale `100.97.150.114`, see [[reference-mvp-server-deploy]]) is **MSI MS-7E02 / Intel Core i5-14400 (10c/16t) / 32 GB RAM / Intel UHD 730 onboard graphics only — NO discrete NVIDIA GPU, no VRAM** (verified via SSH 2026-06-18, `nvidia-smi` absent).

**Verdict: do NOT self-host an LLM on this box.** Without a discrete GPU it can only run small models (7–8B) on CPU, slowly (~few tokens/sec). That is *worse and slower* than the free Qwen (9arm) โอ already uses, and anything Opus-class is impossible. Self-hosting here would also fight the live MVP app + cloudflared tunnel + LINE archiver (all boot-time tasks) for the same CPU/RAM and risk slowing/crashing the real office tool.

Self-hosting only becomes worth considering IF: (a) data must never leave the company (payroll/customer secrets), AND (b) we buy a *separate* box with a discrete NVIDIA GPU (16–24 GB VRAM) — never repurpose this server. Until then: free Qwen + paid Claude/Haiku API already beat anything this machine can run.
