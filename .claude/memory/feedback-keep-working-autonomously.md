---
name: feedback-keep-working-autonomously
description: "โอ wants Claude to keep working continuously and, when a question would normally block, answer it AS โอ would instead of stopping — only stop for genuinely โอ-only decisions"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 707edb2f-b4a1-48aa-a7f8-54bca957f2e4
---

โอ wants a more autonomous working style: **keep going, don't stop to ask at every step.** When work finishes a step and a clarifying question would normally come up, **predict what โอ would answer and proceed on that** — don't block on him.

**Why:** โอ is a non-coder manager. Constant "should I do X?" check-ins slow him down and make him do the thinking he hired Claude to do. He'd rather Claude carry the chain forward and surface only what truly needs him.

**How to apply:**
- After finishing a sub-task, if the next decision has an obvious default given everything known about โอ and the project → just do it, state the assumption in one line, keep moving.
- Use what's known about โอ to answer for him: prefers simplest/laziest solution that works, don't add complexity he won't use, Windows stack is fine, concise plain-language summaries (hide code/paths), money work stays careful.
- **Still STOP and ask** for genuinely โอ-only calls: anything touching money/payroll/billing correctness, irreversible/destructive actions, outward-facing actions (sending/publishing), spending, or a real fork where his preference can't be inferred.
- When proceeding on an inferred answer, make it visible: "ถ้าเป็นโอน่าจะเลือก X เลยทำต่อเลย — ถ้าผิดบอกได้" so he can veto.

Confirmed 2026-06-23. โอ explicitly approved this exact line: general work proceeds autonomously, money work always checks first. Aligns with [[feedback-concise-no-code-dump]] and the money-safety rules in [[feedback-test-data-cleanup-safety]] (autonomy does NOT override money preflight discipline).
