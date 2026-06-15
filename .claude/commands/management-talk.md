---
name: management-talk
description: Rewrite engineer-to-engineer content for engineering-org leadership and shape it for the channel it's going to (JIRA, Slack, email, standup, meeting talking points).
---

Rewrite the content above for engineering-org leadership (VPs, directors, PMs, release managers) — people who are engineering-savvy but don't read code. They want state, customer impact, ownership, and next steps. Shape the output for the specific channel requested.

## What to keep
- Product names, framework identifiers, JIRA keys, PR numbers (e.g. `JIRA-12345`, `PR #5751`)

## What to strip
- Function names, file paths, commit SHAs, struct fields, internal data-structure jargon

## What to translate
- Technical mechanisms into plain-English cause-and-effect. Don't oversimplify — the audience understands "race condition" and "synchronization."

## Channel formats

**JIRA:** Structured blocks with bolded labels — Status, Impact, What Broke, Owner, Next Steps

**Slack:** Single message. Bold the TL;DR. 2–4 bullets. ~80 words. One embedded link max.

**Standup:** 1–3 lines. Pattern: `<state> <thing>. <owner>. <next>`

**Email:** Noun-phrase subject line. Flowing paragraphs in body.

**Meeting talking points:** Bullet list ordered for spoken delivery.

## Rules
- Never invent facts or owners.
- Never post directly to Slack/email — output only, confirm before sending.
- Get explicit approval before posting to JIRA.
- Status updates only — not recommendations.
