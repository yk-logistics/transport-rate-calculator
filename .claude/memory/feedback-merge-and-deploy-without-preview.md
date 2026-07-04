---
name: feedback-merge-and-deploy-without-preview
description: "For UI/display work โอ wants done — merge to main AND deploy to server in the same session, don't stop to let him preview the dev branch first"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 861f199b-b8da-4a59-9259-2c834a013a0e
---

For display/UI changes โอ approves, finish the job end-to-end: merge the feature branch into main and deploy to the live server in the same session. Do NOT stop after committing on a dev branch to wait for him to preview locally.

**Why:** Telling him "open it in dev, if you like it I'll deploy" wastes a round-trip and re-loads context next session → burns tokens. He'd rather see it live and tell me to tweak from there. (said 2026-06-25, after the lcb_mixed split-display feature)

**How to apply:** When work is done + self-verified, go straight to merge → deploy → report the live URL. Still STOP before deploying for money/payroll-logic changes, destructive DB ops, or anything in the "STOP" rules of [[feedback-keep-working-autonomously]]. Display-only changes are safe to ship without a preview gate. Follow [[reference-mvp-deploy-restart-gotcha]] so the deploy actually serves new code.
