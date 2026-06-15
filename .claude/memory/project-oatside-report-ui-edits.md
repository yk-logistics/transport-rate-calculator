---
name: project-oatside-report-ui-edits
description: How to change Oatside report HTML/UI without altering published billing numbers (rebuild re-picks newest GPS)
metadata: 
  node_type: memory
  type: project
  originSessionId: f04318ab-5ec6-4915-a81f-6ddfc57b3797
---

Editing the Oatside customer report UI (the static report at reports/oatside-pg-2026/, built by `Oatside/build_oatside_reports.py`, deployed by `deploy_oatside_report.ps1` to the `transport-rate-calculator-repo` Pages clone → yk-logistics.github.io/transport-rate-calculator/reports/oatside-pg-2026/).

**Gotcha:** a full rebuild (`python Oatside/build_oatside_reports.py`) recomputes ALL money. `discover_gps_files()` picks the **newest GPS export by mtime** in `Oatside/`, so if newer "รายงานการผ่านจุด" xlsx files exist, a rebuild silently changes the published figures.

**Why:** UI tweaks must not move the customer's billing numbers.

**How to apply:** for UI-only changes — (1) edit the builder (source of truth, survives future rebuilds), (2) do NOT rebuild; instead inject into the already-generated HTML with a patch tool (no recompute), (3) leave git push to โอ (outward-facing). The trips-table export buttons (Print/PDF · Excel-as-shown · PNG) were added this way: builder edit + `python ProjectYK_System/tools/patch_oatside_trips_export_buttons.py` (idempotent; also bundles `Oatside/assets/html2canvas.min.js` for the PNG button). Preview locally via `.claude/launch.json` "oatside-report" server. Related: [[project-oatside-billing-recon]]
