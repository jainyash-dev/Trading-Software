// P10 browser validation driver. Real headless Chrome against the running platform (built dist).
// FIXTURE data only (setup_fixture_env.py). Not NSE market data; nothing here is a performance claim.
// Usage: node run_p10_browser.mjs <out_dir> '<cfg json>'
import { createRequire } from "module";
import fs from "fs";
const require = createRequire("/Users/yash/day-trader-skill/platform/web/package.json");
const puppeteer = require("puppeteer-core");
const BASE = "http://127.0.0.1:8899/";
const OUT = process.argv[2];
const CFG = JSON.parse(process.argv[3]);
fs.mkdirSync(`${OUT}/shots`, { recursive: true });
const log = [];
const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true, args: ["--no-sandbox", "--disable-gpu"] });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 1000 });
const consoleErrors = [];
page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 200)); });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function go(hash, wait = 700) { await page.goto(BASE + "#/" + hash, { waitUntil: "networkidle0", timeout: 30000 }); await page.reload({ waitUntil: "networkidle0", timeout: 30000 }); await sleep(wait); }
async function shot(name, fullPage = true) { const f = `shots/${name}.png`; await page.screenshot({ path: `${OUT}/${f}`, fullPage }); return f; }
async function text() { return page.$eval("body", (n) => n.innerText); }
async function api(method, path, body, key) {
  return page.evaluate(async (method, path, body, key) => {
    const headers = { "X-GTF-Request": "1", "Content-Type": "application/json" };
    if (key) headers["Idempotency-Key"] = key;
    const r = await fetch(path, { method, headers, credentials: "same-origin", body: body ? JSON.stringify(body) : undefined });
    return { status: r.status, body: await r.json().catch(() => null) };
  }, method, path, body, key);
}
async function step(name, fn) {
  try { const r = await fn(); log.push({ step: name, ok: true, ...r }); }
  catch (e) { log.push({ step: name, ok: false, error: String(e).slice(0, 300) }); }
}
async function audit() {
  return page.evaluate(() => {
    const h1 = [...document.querySelectorAll("h1")].map((n) => n.innerText.trim());
    const unnamedButtons = [...document.querySelectorAll("button")].filter((b) => !(b.textContent.trim() || b.getAttribute("aria-label") || b.getAttribute("title"))).length;
    const unlabelled = [...document.querySelectorAll("input, select, textarea")].filter((el) => {
      if (el.type === "hidden" || el.type === "radio" || el.type === "checkbox") return false;
      if (el.getAttribute("aria-label")) return false;
      if (el.id && document.querySelector(`label[for="${el.id}"]`)) return false;
      return !el.closest("label");
    }).length;
    const imgsNoAlt = [...document.querySelectorAll("img")].filter((i) => !i.hasAttribute("alt")).length;
    const certifiedBadges = [...document.querySelectorAll('[data-provenance="CERTIFIED"]')].length;
    const overflowX = document.documentElement.scrollWidth > window.innerWidth + 1;
    return { h1, unnamedButtons, unlabelled, imgsNoAlt, certifiedBadges, overflowX, theme: document.documentElement.dataset.theme };
  });
}

// ---------------------------------------------------------------- seed (real API routes)
await go("overview");
let planId = null, entryId = null, draftId = null;
await step("seed: owner settings", async () => {
  const r = await api("PATCH", "/api/v1/settings", { capital: 100000, rpt_pct: 1, risk_stage: "LEARNING" });
  if (r.status !== 200) throw new Error(JSON.stringify(r.body).slice(0, 200)); return { status: r.status };
});
await step("seed: plan draft from stored candidate", async () => {
  const r = await page.evaluate(async (cfg) => {
    const res = await fetch("/api/v1/plans?include_fixtures=true", { method: "POST", credentials: "same-origin", headers: { "X-GTF-Request": "1", "Content-Type": "application/json" }, body: JSON.stringify({ scan_key: cfg.scan_key, symbol: "SYN", zone_id: cfg.zone_id, rationale: "P10 browser seed" }) });
    return { status: res.status, body: await res.json() };
  }, CFG);
  planId = r.body?.data?.plan_id; if (!planId) throw new Error(JSON.stringify(r.body).slice(0, 200));
  return { plan_id: planId, combinations: (r.body.data.combinations || []).length };
});
await step("seed: approve with every checklist item answered (no order)", async () => {
  const checklist = Object.fromEntries(["EXPLOSIVE_RELATIVE_SIZE_CONTEXT", "GAP_MEANINGFULNESS", "AUTHENTICITY", "GARBAGE_CHART", "LOTL", "CAME_FROM", "TARGET_QUALITY", "BUFFER_SELECTION", "SECTOR", "CORPORATE_ACTIONS", "TRADER_STATE"].map((k) => [k, true]));
  const r = await api("POST", `/api/v1/plans/${planId}/approve`, { combination_index: 0, alert_note: "P10 seed. Not an order.", checklist });
  entryId = r.body?.data?.entry_id; if (r.status !== 200) throw new Error(JSON.stringify(r.body).slice(0, 300));
  return { entry_id: entryId, authorises_order: r.body.data.authorises_order ?? false };
});
await step("seed: journal order reference and entry print (owner-typed facts)", async () => {
  const plan = (await api("GET", `/api/v1/plans/${planId}`)).body?.data || {};
  const prep = plan.manual_execution?.prep_fields || {};
  const qty = Number(prep.quantity || plan.quantity || 10);
  const price = Number(prep.proposed_entry || 160);
  const o = await api("POST", `/api/v1/journal/${entryId}/order`, { submitted_at: new Date(Date.now() + 1000).toISOString(), order_ref: "KITE-P10-SEED", note: "Owner submitted in Kite (fixture)" }, "p10-order-" + Date.now());
  const e = await api("POST", `/api/v1/journal/${entryId}/executions`, { side: "ENTRY", quantity: qty, price, at: new Date(Date.now() + 2000).toISOString(), print_key: "p10-print-1" }, "p10-exec-" + Date.now());
  const n = await api("POST", `/api/v1/journal/${entryId}/notes`, { note_key: "p10-note-1", at: new Date(Date.now() + 3000).toISOString(), kind: "POST_TRADE_REVIEW", body: "Entry at planned level. Fixture data." }, "p10-note-" + Date.now());
  return { order: o.status, execution: e.status, note: n.status, qty, price, order_error: o.status >= 300 ? JSON.stringify(o.body).slice(0, 200) : undefined, exec_error: e.status >= 300 ? JSON.stringify(e.body).slice(0, 200) : undefined };
});
await step("seed: second draft left in DRAFT", async () => {
  const r = await page.evaluate(async (cfg) => {
    const res = await fetch("/api/v1/plans?include_fixtures=true", { method: "POST", credentials: "same-origin", headers: { "X-GTF-Request": "1", "Content-Type": "application/json" }, body: JSON.stringify({ scan_key: cfg.scan_key, symbol: "SYN", zone_id: cfg.zone_id }) });
    return { status: res.status, body: await res.json() };
  }, CFG);
  draftId = r.body?.data?.plan_id; return { status: r.status, plan_id: draftId, error: r.status >= 300 ? r.body?.error?.code : undefined };
});
await step("seed: real-pipeline MIT scan on WALK + missing NOPE", async () => {
  const r = await api("POST", "/api/v1/scans", { mode: "MANUAL", trade_type: "MIT", universe: ["WALK", "NOPE"], as_of: "2024-07-12", dataset_id: CFG.dataset_id }, "p10-walk-" + Date.now());
  let job = r.body?.data; const states = [job?.state];
  for (let i = 0; i < 60 && job && !["SUCCEEDED_COMPLETE", "SUCCEEDED_PARTIAL", "FAILED", "INTERRUPTED", "CANCELLED"].includes(job.state); i++) {
    await sleep(500); job = (await api("GET", `/api/v1/jobs/${job.job_id}`)).body?.data; states.push(job?.state);
  }
  CFG.walk_job = job?.job_id; CFG.walk_scan = job?.result_ref;
  return { status: r.status, error: r.status >= 300 ? JSON.stringify(r.body).slice(0, 300) : undefined, states: [...new Set(states)], job_id: job?.job_id, result_ref: job?.result_ref };
});
await step("seed: ingest stored scan into opportunities", async () => {
  const r = await api("POST", "/api/v1/opportunities/ingest", { scan_key: CFG.scan_key, include_rejected: true });
  return { status: r.status, error: r.status >= 300 ? r.body?.error?.code : undefined };
});
await step("seed: watchlist", async () => {
  const r = await api("POST", "/api/v1/watchlists", { name: "Fixture study list", symbols: [] }, "p10-wl-" + Date.now());
  return { status: r.status, error: r.status >= 300 ? JSON.stringify(r.body).slice(0, 300) : undefined };
});

// ---------------------------------------------------------------- every route, both themes
const ROUTES = [
  ["overview", "overview"],
  ["watchlists", "watchlists"],
  ["analysis-D", `analysis?scan=${CFG.scan_key}&symbol=SYN&fixtures=1&timeframe=D`],
  ["analysis-W", `analysis?scan=${CFG.scan_key}&symbol=SYN&fixtures=1&timeframe=W`],
  ["analysis-noscan", "analysis?symbol=SYN"],
  ["scanner", `scanner?scan=${CFG.scan_key}&fixtures=1`],
  ["opportunities", "opportunities"],
  ["history", "history"],
  ["plans", `plans?plan=${planId}`],
  ["portfolio", "portfolio"],
  ["risk", "risk"],
  ["journal", `journal?entry=${entryId}`],
  ["backtest", "backtest"],
  ["analytics", "analytics"],
  ["reports", "reports"],
  ["assistant", "assistant"],
  ["paper", "paper"],
  ["data", "data"],
  ["jobs", "jobs"],
  ["settings", "settings"],
];
const audits = {};
for (const theme of ["dark", "light"]) {
  await page.evaluate((t) => localStorage.setItem("gtf-theme", t), theme);
  await page.reload({ waitUntil: "networkidle0" });
  for (const [name, hash] of ROUTES) {
    await step(`${theme}: ${name}`, async () => {
      await go(hash, name.startsWith("analysis-") && name !== "analysis-noscan" ? 1500 : 800);
      if (name === "history") {
        await page.evaluate(() => [...document.querySelectorAll('button[role="switch"]')].find((b) => b.innerText.includes("Include fixture"))?.click()); await sleep(700);
      }
      if (name === "assistant") {
        await page.evaluate(() => [...document.querySelectorAll('button[role="switch"]')].find((b) => b.innerText.includes("Include fixture"))?.click()); await sleep(700);
        await page.select("#stored-scan", CFG.scan_key); await sleep(800);
        await page.select("#symbol-in-that-scan", "SYN"); await sleep(200);
        await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.innerText.trim() === "Why this status?")?.click()); await sleep(900);
      }
      if (name === "reports") {
        await page.evaluate(() => [...document.querySelectorAll('button[role="switch"]')].find((b) => b.innerText.includes("Include fixture"))?.click()); await sleep(700);
        await page.select("#scan-key", CFG.scan_key); await sleep(200);
        await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.innerText.startsWith("Export "))?.click()); await sleep(800);
      }
      if (name === "analysis-D") {
        await page.waitForSelector("[data-testid='candle-chart'] canvas", { timeout: 15000 }).catch(() => null);
        await page.evaluate(() => { const d = document.querySelector('[data-testid="notices"]'); if (d) d.open = true; });
      }
      const a = await audit();
      audits[`${theme}:${name}`] = a;
      const t = await text();
      return { h1: a.h1, theme: a.theme, certified_badges: a.certifiedBadges, unnamed_buttons: a.unnamedButtons, unlabelled_inputs: a.unlabelled, overflow_x: a.overflowX, fixture_banner: t.includes("FIXTURE_NOT_MARKET_DATA"), shot: await shot(`${theme}-${name}`) };
    });
  }
}

// ---------------------------------------------------------------- journeys and behaviours
await step("G: theme switch from header persists across reload", async () => {
  await page.evaluate(() => localStorage.setItem("gtf-theme", "dark"));
  await go("overview");
  await page.click('button[aria-label="Switch to light theme"]'); await sleep(300);
  const after = await page.evaluate(() => document.documentElement.dataset.theme);
  await page.reload({ waitUntil: "domcontentloaded" });
  const atDomReady = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  await sleep(800);
  const afterReload = await page.evaluate(() => document.documentElement.dataset.theme);
  return { after_click: after, at_dom_content_loaded: atDomReady, after_reload: afterReload };
});
await step("G: deep link, back and forward", async () => {
  await go("portfolio"); await go("risk"); await go(`journal?entry=${entryId}`);
  await page.goBack(); await sleep(600); const back = await page.evaluate(() => [location.hash, document.querySelector("h1")?.innerText]);
  await page.goBack(); await sleep(600); const back2 = await page.evaluate(() => [location.hash, document.querySelector("h1")?.innerText]);
  await page.goForward(); await sleep(600); const fwd = await page.evaluate(() => [location.hash, document.querySelector("h1")?.innerText]);
  const active = await page.$eval('nav a[aria-current="page"]', (n) => n.innerText.trim());
  await page.reload({ waitUntil: "networkidle0" }); await sleep(600);
  const reloaded = await page.evaluate(() => [location.hash, document.querySelector("h1")?.innerText]);
  return { back, back2, forward: fwd, active_nav: active, reloaded };
});
await step("A: search -> analyse -> choose stored scan -> chart", async () => {
  await go("overview");
  await page.type("#global-search", "SYN"); await page.keyboard.press("Enter"); await sleep(800);
  const results = await page.$$eval('[aria-label="Instrument results"] li', (n) => n.length).catch(() => 0);
  const msg = await page.$eval('form[role="search"] [role="status"]', (n) => n.innerText).catch(() => null);
  await go("analysis?symbol=SYN"); await sleep(600);
  const chooser = (await text()).includes("Choose a stored scan for SYN");
  await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.innerText.startsWith("Open SYN in this scan"))?.click()); await sleep(1500);
  const opened = await page.evaluate(() => [location.hash, document.querySelector("h1")?.innerText]);
  return { search_results: results, search_message: msg, chooser, opened, shot: await shot("journey-a-opened-from-chooser") };
});
await step("C: approve dialog appears before approval (draft plan)", async () => {
  await go(`plans?plan=${draftId}`); await sleep(600);
  await page.$$eval("select[aria-label]", (sels) => sels.forEach((s) => { if ([...s.options].some((o) => o.value === "true") && s.getAttribute("aria-label") !== "Filter state") { const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set; setter.call(s, "true"); s.dispatchEvent(new Event("change", { bubbles: true })); } }));
  await sleep(300);
  await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.innerText.trim() === "Approve plan")?.click()); await sleep(400);
  const dialog = await page.$eval('[role="dialog"]', (n) => n.innerText).catch(() => null);
  const s = await shot("journey-c-approve-confirmation", false);
  await page.keyboard.press("Escape"); await sleep(300);
  const closed = (await page.$('[role="dialog"]')) === null;
  return { dialog: dialog?.split("\n").slice(0, 3), closed_on_escape: closed, shot: s };
});
await step("D: portfolio -> journal record link", async () => {
  await go("portfolio");
  await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.innerText.trim() === "Journal")?.click()); await sleep(900);
  return { hash: await page.evaluate(() => location.hash), detail: await page.$eval('[data-testid="journal-detail"]', (n) => n.innerText.split("\n")[0]).catch(() => null) };
});
for (const [w, h, label] of [[1024, 768, "laptop"], [768, 1024, "tablet"], [390, 844, "mobile"]]) {
  await step(`responsive ${label} ${w}px`, async () => {
    await page.setViewport({ width: w, height: h });
    await go("overview"); const o = await audit(); const s1 = await shot(`responsive-${label}-overview`, false);
    await go(`analysis?scan=${CFG.scan_key}&symbol=SYN&fixtures=1&timeframe=D`, 1500); const a = await audit(); const s2 = await shot(`responsive-${label}-analysis`, false);
    return { overview_overflow_x: o.overflowX, analysis_overflow_x: a.overflowX, shots: [s1, s2] };
  });
}
await page.setViewport({ width: 1440, height: 1000 });

fs.writeFileSync(`${OUT}/results.json`, JSON.stringify({ cfg: CFG, steps: log, consoleErrors }, null, 2));
await browser.close();
const failed = log.filter((s) => !s.ok);
console.log(`steps ${log.length}, failed ${failed.length}`);
for (const f of failed) console.log("FAIL", f.step, f.error);
