/* P3: เมนูคลิกขวาทั้งระบบ — framework เดียว (YKCtx)
 *
 * ใช้ 2 ทาง:
 *  1) ประกาศบน element:  <tr data-ctx="transfer-row" data-account="..." data-name="...">
 *     คลิกขวา (เดสก์ท็อป) หรือกดค้าง ~550ms (มือถือ) → เปิดเมนูตามชนิด
 *  2) เรียกตรงจากโค้ด (เช่น Tabulator cellContext):
 *     YKCtx.open("daily-cell", {id: 123, value: "...", customer: "..."}, x, y)
 *
 * รายการเมนูมาจาก server: GET /api/ctxmenu/{type} (กรองสิทธิ์แล้ว) — cache ต่อชนิด
 * ชนิด item: copy (คัดลอก data[key]) | link (เปิด href แทนที่ {key} จาก data)
 *            | call (เรียก window[fn](data) — ฟังก์ชันหน้านั้นต้อง expose เอง)
 * กติกา: ห้ามใส่ action เงินตรงในเมนู — เมนูเปิดหน้า/ฟอร์มที่มีของเดิมเท่านั้น
 * ปิดเมนู: Esc / คลิกนอก / scroll
 */
(function () {
  "use strict";

  const CACHE = {};       // type -> Promise<items>
  let menuEl = null;      // เมนูที่เปิดอยู่ (มีได้ทีละอัน)

  function closeMenu() {
    if (menuEl) { menuEl.remove(); menuEl = null; }
  }

  function fetchItems(type) {
    if (!CACHE[type]) {
      CACHE[type] = fetch(`/api/ctxmenu/${encodeURIComponent(type)}`)
        .then(r => (r.ok ? r.json() : { items: [] }))
        .then(j => j.items || [])
        .catch(() => []);
    }
    return CACHE[type];
  }

  function subst(tpl, data) {
    return String(tpl).replace(/\{(\w+)\}/g, (_, k) => encodeURIComponent(data[k] ?? ""));
  }

  function flash(el, text) {
    const old = el.textContent;
    el.textContent = text;
    setTimeout(closeMenu, 450);
    setTimeout(() => { el.textContent = old; }, 400);
  }

  function render(items, data, x, y) {
    closeMenu();
    if (!items.length) return;
    const m = document.createElement("div");
    m.id = "yk-ctxmenu";
    m.className = "fixed z-[9999] bg-white text-slate-800 rounded-lg shadow-xl border " +
      "border-slate-200 py-1 min-w-[200px] text-sm";
    for (const it of items) {
      const a = document.createElement(it.kind === "link" ? "a" : "button");
      a.className = "block w-full text-left px-4 py-2 hover:bg-slate-100 " +
        "whitespace-nowrap cursor-pointer";
      a.textContent = it.label;
      if (it.kind === "link") {
        a.href = subst(it.href, data);
        if (it.newtab !== false) a.target = "_blank";
      } else if (it.kind === "copy") {
        a.type = "button";
        a.addEventListener("click", () => {
          const v = String(data[it.key] ?? "");
          navigator.clipboard.writeText(v).then(() => flash(a, "✓ คัดลอกแล้ว"));
        });
      } else if (it.kind === "call") {
        a.type = "button";
        a.addEventListener("click", () => {
          closeMenu();
          const fn = window[it.fn];
          if (typeof fn === "function") fn(data);
          else console.warn("YKCtx: ไม่มีฟังก์ชัน", it.fn, "ในหน้านี้");
        });
      }
      m.appendChild(a);
    }
    document.body.appendChild(m);
    // กันเมนูตกขอบจอ
    const r = m.getBoundingClientRect();
    m.style.left = Math.min(x, window.innerWidth - r.width - 8) + "px";
    m.style.top = Math.min(y, window.innerHeight - r.height - 8) + "px";
    menuEl = m;
  }

  function open(type, data, x, y) {
    fetchItems(type).then(items => render(items, data || {}, x, y));
  }

  // ── binding อัตโนมัติสำหรับ [data-ctx] ─────────────────────────────────────
  function dataOf(el) {
    const d = {};
    for (const [k, v] of Object.entries(el.dataset)) { if (k !== "ctx") d[k] = v; }
    return d;
  }

  document.addEventListener("contextmenu", (e) => {
    const host = e.target.closest("[data-ctx]");
    if (!host) return;
    e.preventDefault();
    open(host.dataset.ctx, dataOf(host), e.clientX, e.clientY);
  });

  // มือถือ: กดค้าง ~550ms (ยกเลิกถ้านิ้วขยับ/ปล่อยก่อน)
  let pressTimer = null;
  document.addEventListener("touchstart", (e) => {
    const host = e.target.closest("[data-ctx]");
    if (!host) return;
    const t = e.touches[0];
    pressTimer = setTimeout(() => open(host.dataset.ctx, dataOf(host), t.clientX, t.clientY), 550);
  }, { passive: true });
  ["touchend", "touchmove", "touchcancel"].forEach(ev =>
    document.addEventListener(ev, () => { clearTimeout(pressTimer); }, { passive: true }));

  // ปิดเมนู
  document.addEventListener("click", (e) => {
    if (menuEl && !menuEl.contains(e.target)) closeMenu();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenu(); });
  document.addEventListener("scroll", closeMenu, true);

  window.YKCtx = { open: open, close: closeMenu };
})();
