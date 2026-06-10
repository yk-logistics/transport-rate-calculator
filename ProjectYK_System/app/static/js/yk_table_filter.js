/**
 * yk_table_filter.js — Excel-style dropdown column filter for all HTML <table> elements
 * Auto-applies to every <table> with <thead>+<tbody> on the page.
 * Skip action columns (those with empty <th> text).
 * Add data-no-filter on a <table> to opt out.
 */
(function () {
  "use strict";

  // Per-table filter state: table → Map<colIdx, Set<string>>
  const TABLE_FILTERS = new WeakMap();
  let _openPop = null;

  function closePop() {
    if (_openPop) { _openPop.remove(); _openPop = null; }
  }

  // Read unique values from a column
  function colValues(tbody, colIdx) {
    const m = new Map();
    Array.from(tbody.rows).forEach(tr => {
      const td = tr.cells[colIdx];
      const raw = td ? td.textContent.trim() : "";
      const k = raw === "" ? "\0BLANK" : raw;
      m.set(k, (m.get(k) || 0) + 1);
    });
    return [...m.entries()].sort(([a], [b]) =>
      a === "\0BLANK" ? 1 : b === "\0BLANK" ? -1 : a.localeCompare(b, "th")
    );
  }

  // Show/hide rows based on all active filters
  function applyFilters(table, tbody) {
    const filters = TABLE_FILTERS.get(table) || new Map();
    Array.from(tbody.rows).forEach(tr => {
      let show = true;
      filters.forEach((sel, ci) => {
        if (!sel || sel.size === 0 || sel.has("__ALL__")) return;
        const td = tr.cells[ci];
        const raw = td ? td.textContent.trim() : "";
        const k = raw === "" ? "\0BLANK" : raw;
        if (!sel.has(k)) show = false;
      });
      tr.style.display = show ? "" : "none";
    });
    // Recompute date-band stripes if applicable
    if (table.dataset.dateCol !== undefined) {
      const dc = parseInt(table.dataset.dateCol) || 0;
      let lastDate = "", band = 0;
      Array.from(tbody.rows).forEach(tr => {
        tr.classList.remove("yk-day-b");
        if (tr.style.display === "none") return;
        const cell = tr.cells[dc];
        const dt = cell ? cell.textContent.trim() : "";
        if (dt && dt !== lastDate) { band ^= 1; lastDate = dt; }
        if (band) tr.classList.add("yk-day-b");
      });
    }
  }

  // Build the popup
  function openPopup(anchorBtn, entries, sel, onApply) {
    closePop();
    const rect = anchorBtn.getBoundingClientRect();
    const pop = document.createElement("div");
    pop.style.cssText =
      "position:fixed;z-index:9999;background:#fff;border:1px solid #cbd5e1;" +
      "border-radius:6px;box-shadow:0 4px 24px rgba(0,0,0,.18);" +
      "display:flex;flex-direction:column;min-width:200px;max-width:290px;" +
      "max-height:340px;font-size:12px;" +
      "left:" + Math.min(rect.left, Math.max(0, innerWidth - 300)) + "px;" +
      "top:" + Math.min(rect.bottom + 2, innerHeight - 350) + "px;";

    // Search
    const si = document.createElement("input");
    si.type = "text"; si.placeholder = "🔍 ค้นหา…";
    si.style.cssText = "margin:6px;padding:3px 6px;border:1px solid #94a3b8;" +
      "border-radius:3px;font-size:11px;box-sizing:border-box;width:calc(100% - 12px);";
    pop.appendChild(si);

    // List
    const ul = document.createElement("div");
    ul.style.cssText = "overflow-y:auto;flex:1;padding:2px 4px;";
    pop.appendChild(ul);

    // Footer
    const ft = document.createElement("div");
    ft.style.cssText = "display:flex;gap:4px;padding:6px;border-top:1px solid #e2e8f0;flex-shrink:0;";
    [["ใช้ตัวกรอง", false], ["ล้าง", true]].forEach(([t, isClear]) => {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = t;
      b.style.cssText = "flex:1;border-radius:4px;padding:4px;font-size:11px;cursor:pointer;" +
        "border:1px solid " + (isClear ? "#e2e8f0" : "transparent") + ";" +
        "background:" + (isClear ? "#f8fafc" : "#0284c7") + ";color:" + (isClear ? "#334155" : "#fff") + ";";
      b.onclick = () => {
        if (isClear) { sel.clear(); sel.add("__ALL__"); }
        onApply(new Set(sel));
        closePop();
      };
      ft.appendChild(b);
    });
    pop.appendChild(ft);

    function mkRow(key, label, count) {
      const row = document.createElement("label");
      row.style.cssText = "display:flex;align-items:center;gap:5px;padding:2px 3px;border-radius:3px;cursor:pointer;";
      row.onmouseenter = () => row.style.background = "#f8fafc";
      row.onmouseleave = () => row.style.background = "";
      const chk = document.createElement("input");
      chk.type = "checkbox"; chk.value = key;
      chk.style.cssText = "accent-color:#0284c7;flex-shrink:0;";
      chk.checked = sel.has("__ALL__") || sel.has(key);
      chk.onchange = () => {
        if (key === "__ALL__") {
          sel.clear();
          if (chk.checked) sel.add("__ALL__");
          ul.querySelectorAll("input[type=checkbox]").forEach(c => c.checked = chk.checked);
        } else {
          // Expand __ALL__ → explicit list before modifying
          if (sel.has("__ALL__")) {
            sel.clear();
            entries.forEach(([k]) => sel.add(k));
          }
          chk.checked ? sel.add(key) : sel.delete(key);
          const ac = ul.querySelector("input[value='__ALL__']");
          if (ac) {
            const allKeys = entries.map(([k]) => k);
            const allChecked = allKeys.every(k => sel.has(k));
            if (allChecked) { sel.clear(); sel.add("__ALL__"); }
            ac.checked = sel.has("__ALL__");
            ul.querySelectorAll("input[type=checkbox]:not([value='__ALL__'])").forEach(c => {
              c.checked = sel.has("__ALL__") || sel.has(c.value);
            });
          }
        }
      };
      const sp = document.createElement("span");
      sp.textContent = label;
      sp.style.cssText = "flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" +
        (key === "\0BLANK" ? "color:#94a3b8;font-style:italic;" : "") +
        (key === "__ALL__" ? "font-weight:600;" : "");
      const cn = document.createElement("span");
      cn.textContent = count; cn.style.cssText = "color:#94a3b8;font-size:10px;flex-shrink:0;";
      row.append(chk, sp, cn);
      return row;
    }

    function renderList(q) {
      ul.innerHTML = "";
      const total = entries.reduce((s, [, c]) => s + c, 0);
      ul.appendChild(mkRow("__ALL__", "✓ ทั้งหมด", total));
      entries.forEach(([k, c]) => {
        const lbl = k === "\0BLANK" ? "(ว่าง)" : k;
        if (q && k !== "\0BLANK" && !lbl.toLowerCase().includes(q.toLowerCase())) return;
        ul.appendChild(mkRow(k, lbl, c));
      });
    }

    renderList("");
    si.addEventListener("input", () => renderList(si.value));
    document.body.appendChild(pop);
    _openPop = pop;
    si.focus();

    // Close on outside click
    setTimeout(() => {
      const h = e => {
        if (_openPop && !_openPop.contains(e.target) && e.target !== anchorBtn) {
          closePop();
          document.removeEventListener("mousedown", h);
        }
      };
      document.addEventListener("mousedown", h);
    }, 0);
  }

  function addFilterBtn(table, tbody, th, colIdx) {
    let sel = new Set(["__ALL__"]);

    const wrap = document.createElement("div");
    wrap.style.cssText = "margin-top:2px;";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "yk-filter-btn";

    function styleBtn() {
      const all = sel.has("__ALL__");
      btn.textContent = all ? "ทั้งหมด ▾" : sel.size + " เลือก ▾";
      btn.style.cssText = "width:100%;text-align:left;font-size:10px;padding:1px 3px;" +
        "border:1px solid " + (all ? "#7dd3fc" : "#f59e0b") + ";" +
        "border-radius:3px;background:" + (all ? "#f0f9ff" : "#fef3c7") + ";" +
        "cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" +
        "color:" + (all ? "#0369a1" : "#b45309") + ";font-weight:" + (all ? "normal" : "600") + ";";
    }
    styleBtn();

    btn.addEventListener("click", e => {
      e.stopPropagation();
      if (_openPop) { closePop(); return; }
      const entries = colValues(tbody, colIdx);
      openPopup(btn, entries, sel, newSel => {
        sel = newSel;
        const filters = TABLE_FILTERS.get(table);
        if (filters) {
          if (sel.has("__ALL__") || sel.size === 0) filters.delete(colIdx);
          else filters.set(colIdx, sel);
        }
        applyFilters(table, tbody);
        styleBtn();
      });
    });

    wrap.appendChild(btn);
    th.appendChild(wrap);
  }

  function initTable(table) {
    if (table._ykFilter || table.dataset.noFilter !== undefined) return;
    table._ykFilter = true;

    const thead = table.querySelector(":scope > thead");
    const tbody = table.querySelector(":scope > tbody");
    if (!thead || !tbody) return;

    TABLE_FILTERS.set(table, new Map());

    const ths = thead.querySelectorAll("tr:last-child > th");
    ths.forEach((th, colIdx) => {
      // Skip action columns (empty header text)
      if (th.textContent.trim() === "") return;
      addFilterBtn(table, tbody, th, colIdx);
    });
  }

  function initAll(root) {
    (root || document).querySelectorAll("table:not([data-no-filter])").forEach(initTable);
  }

  document.addEventListener("DOMContentLoaded", () => initAll());

  // Re-init after HTMX swaps
  document.addEventListener("htmx:afterSettle", e => {
    initAll(e.detail && e.detail.target);
  });

  // Close popup on Escape
  document.addEventListener("keydown", e => { if (e.key === "Escape") closePop(); });

})();
