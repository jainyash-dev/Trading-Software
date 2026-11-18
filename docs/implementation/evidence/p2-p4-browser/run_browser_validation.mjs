// Browser validation driver. Real Chrome (headless) against the running platform. FIXTURE data only.
import { createRequire } from "module";
import fs from "fs";
const require = createRequire("/Users/yash/day-trader-skill/platform/web/package.json");
const puppeteer = require("puppeteer-core");
const BASE = "http://127.0.0.1:8899/";
const OUT = process.argv[2];
const CFG = JSON.parse(process.argv[3]);
const log = [];
let shotN = 0;
const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true, args: ["--no-sandbox", "--disable-gpu"] });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 1000 });
const consoleErrors = [];
page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 200)); });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function go(hash) { await page.goto(BASE + "#/" + hash, { waitUntil: "networkidle0", timeout: 30000 }); await sleep(600); }
async function shot(name) { shotN += 1; const f = `${OUT}/${String(shotN).padStart(2, "0")}-${name}.png`; await page.screenshot({ path: f, fullPage: true }); return f.split("/").pop(); }
async function text() { return page.$eval("body", (n) => n.innerText); }
async function click(label) {
  const ok = await page.evaluate((label) => {
    const b = [...document.querySelectorAll("button")].find((x) => x.innerText.trim() === label && !x.disabled);
    if (!b) return false; b.click(); return true;
  }, label);
  if (!ok) throw new Error("button not found: " + label);
  await sleep(900);
}
async function api(method, path, body, key) {
  return page.evaluate(async (method, path, body, key) => {
    const headers = { "X-GTF-Request": "1", "Content-Type": "application/json" };
    if (key) headers["Idempotency-Key"] = key;
    const r = await fetch(path, { method, headers, credentials: "same-origin", body: body ? JSON.stringify(body) : undefined });
    return { status: r.status, body: await r.json().catch(() => null) };
  }, method, path, body, key);
}
async function evidence() {
  return page.$$eval("[data-evidence]", (rows) => Object.fromEntries(rows.map((r) => [r.getAttribute("data-evidence"), r.getAttribute("data-state")])));
}
async function step(name, fn) {
  try { const r = await fn(); log.push({ step: name, ok: true, ...r }); }
  catch (e) { log.push({ step: name, ok: false, error: String(e).slice(0, 300), shot: await shot("FAIL-" + name.replace(/\W+/g, "_")) }); }
}
const A = `analysis?scan=${CFG.scan_key}&symbol=SYN&fixtures=1`;

await go("overview");
await step("P2 empty analysis without stored scan (OD-P2-1 kept deferred)", async () => {
  await go("analysis"); const t = await text();
  if (!t.includes("OD-P2-1")) throw new Error("OD-P2-1 empty state missing");
  return { shot: await shot("p2-analysis-no-scan") };
});
for (const tf of ["D", "W", "M"]) {
  await step(`P2 stored-bundle chart ${tf}`, async () => {
    await go(`${A}&timeframe=${tf}`);
    await page.waitForSelector("[data-testid='candle-chart'] canvas", { timeout: 15000 });
    const t = await text(); const ev = await evidence();
    const volume = (t.match(/Volume (PRESENT|PARTIAL|UNAVAILABLE|UNSUPPORTED)/) || [])[1];
    // hover the last candle area to read the legend (OHLC + V)
    const box = await (await page.$("[data-testid='candle-chart']")).boundingBox();
    await page.mouse.move(box.x + box.width - 90, box.y + box.height / 2); await sleep(300);
    const legend = await page.$eval("[data-testid='candle-chart']", (n) => n.parentElement.innerText.split("\n")[0]);
    return { timeframe: tf, volume_state: volume, evidence: ev, legend, fixture_banner: t.includes("FIXTURE_NOT_MARKET_DATA"), zones_listed: (t.match(/Proximal \d/g) || []).length, shot: await shot(`p2-chart-${tf}`) };
  });
}
await step("P2 wrong symbol (not in stored scan) -> MISSING, not a finding", async () => {
  await go(`analysis?scan=${CFG.scan_key}&symbol=WALK&fixtures=1&timeframe=D`); await sleep(500);
  return { evidence: await evidence(), shot: await shot("p2-wrong-symbol") };
});
await step("P2 unknown scan -> bundle MISSING", async () => {
  await go(`analysis?scan=scan-does-not-exist&symbol=SYN&fixtures=1&timeframe=D`); await sleep(500);
  return { evidence: await evidence(), text_has_error: (await text()).includes("not found"), shot: await shot("p2-unknown-scan") };
});
await step("P2 wrong data version / session -> STALE", async () => {
  await go(`${A}&timeframe=D&as_of=${CFG.as_of.slice(0, 10)}&dataset_id=deadbeef`); await sleep(500);
  const ev1 = await evidence();
  await go(`${A}&timeframe=D&as_of=2024-01-15&dataset_id=${CFG.dataset_id}`); await sleep(500);
  return { wrong_dataset: ev1, wrong_session: await evidence(), shot: await shot("p2-stale-session") };
});

// ---- P4 planning journey -------------------------------------------------------------------
await step("P4 settings: owner capital and risk percent (API from the browser session)", async () => {
  const r = await api("PATCH", "/api/v1/settings", { capital: 100000, rpt_pct: 1, risk_stage: "LEARNING" });
  if (r.status !== 200) throw new Error(JSON.stringify(r.body).slice(0, 200)); return { status: r.status };
});
let planId = null, entryId = null;
await step("P4 create draft from stored candidate (UI)", async () => {
  await go(`plans?scan=${CFG.scan_key}&symbol=SYN&zone=${CFG.zone_id}&fixtures=1`);
  await click("Create draft"); await sleep(800);
  const t = await text();
  planId = (t.match(/plan-[0-9a-f]{16}/) || [])[0];
  const combos = (t.match(/^\d+: entry .*$/gm) || []);
  return { plan_id: planId, state_draft: t.includes("Plan state\nDRAFT"), combinations: combos.slice(0, 3), geometry: (t.match(/Geometry\n(\w+)/) || [])[1], shot: await shot("p4-draft-geometry") };
});
await step("P4 approval refused with unanswered checklist (UI)", async () => {
  await click("Approve plan"); const t = await text();
  return { refused: t.includes("Every checklist item must be answered"), shot: await shot("p4-approve-refused-checklist") };
});
await step("P4 approve with answered checklist (UI) - no order", async () => {
  await page.$$eval("select[aria-label]", (sels) => sels.forEach((s) => { if ([...s.options].some((o) => o.value === "true") && s.getAttribute("aria-label") !== "Filter state") { const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set; setter.call(s, "true"); s.dispatchEvent(new Event("change", { bubbles: true })); } }));
  await sleep(300); await click("Approve plan"); await sleep(800);
  const t = await text();
  entryId = Number((t.match(/Journal entry\n(\d+)/) || [])[1]) || null;
  return { approved_msg: t.includes("No order was sent"), entry_id: entryId, journal_state: (t.match(/Journal state\n(\w+)/) || [])[1], sync: (t.match(/Plan\/journal sync\n(\w+)/) || [])[1], cancel_redirect: t.includes("Cancel it in the Journal"), authorises_order_false: t.includes("authorises_order\nfalse"), shot: await shot("p4-approved") };
});
await step("P2 FR-4.9 plan overlay on chart (approved, journal PLANNED)", async () => {
  await go(`${A}&timeframe=D`); await page.waitForSelector("[data-testid='candle-chart'] canvas", { timeout: 15000 });
  const panel = await page.$eval("[data-testid='plan-overlay']", (n) => n.innerText);
  return { panel: panel.split("\n").slice(0, 6), lines: (panel.match(/PLAN \w+ (entry|stop|target)/g) || []), shot: await shot("p2-plan-overlay-active") };
});
await step("P4 platform cancel of approved plan is not offered; journal cancel via Journal UI", async () => {
  await go(`journal?entry=${entryId}`);
  await page.evaluate(() => { const i = [...document.querySelectorAll("label")].find((l) => l.innerText.startsWith("Cancel reason"))?.querySelector("input"); if (i) { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; set.call(i, "Owner withdrew the setup before any order"); i.dispatchEvent(new Event("input", { bubbles: true })); } });
  await sleep(200); await click("Record CANCELLED"); await sleep(800);
  const t = await text();
  return { message: (t.match(/CANCELLED recorded in the journal[^\n]*/) || [t.match(/[^\n]*(refused|not allowed)[^\n]*/)?.[0]])[0], shot: await shot("p4-journal-cancel") };
});
await step("P4-IR-04 plan mirrors journal cancel (UI)", async () => {
  await go(`plans?plan=${planId}&fixtures=1`); await sleep(500); const t = await text();
  return { plan_state: (t.match(/Plan state\n(\w+)/) || [])[1], journal_state: (t.match(/Journal state\n(\w+)/) || [])[1], sync: (t.match(/Plan\/journal sync\n(\w+)/) || [])[1], from_journal: t.includes("Cancelled from the journal"), approved_count: (t.match(/Approved\n(\d+)/) || [])[1], cancelled_count: (t.match(/Cancelled\n(\d+)/) || [])[1], shot: await shot("p4-plan-mirrored-cancel") };
});
await step("P2 FR-4.9 cancelled plan is not drawn as active", async () => {
  await go(`${A}&timeframe=D`); await page.waitForSelector("[data-testid='candle-chart'] canvas", { timeout: 15000 });
  const panel = await page.$eval("[data-testid='plan-overlay']", (n) => n.innerText);
  return { lines: (panel.match(/PLAN \w+ (entry|stop|target)/g) || []).length, note: panel.split("\n").find((l) => l.includes("Inactive")), shot: await shot("p2-plan-overlay-cancelled") };
});
await step("P4 second draft: submit then reject with reason (UI)", async () => {
  await go(`plans?scan=${CFG.scan_key}&symbol=SYN&zone=${CFG.zone_id}&fixtures=1`);
  await click("Create draft"); await sleep(600);
  await click("Submit for review"); let t = await text(); const awaiting = t.includes("Plan state\nAWAITING_OWNER");
  await click("Reject"); t = await text(); const needReason = t.includes("Reject requires an explicit owner reason");
  await page.evaluate(() => { const i = [...document.querySelectorAll("label")].find((l) => l.innerText.startsWith("Reject / cancel reason"))?.querySelector("input"); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; set.call(i, "Owner: target quality insufficient"); i.dispatchEvent(new Event("input", { bubbles: true })); });
  await sleep(200); await click("Reject"); t = await text();
  return { awaiting, reason_required: needReason, rejected: t.includes("Plan state\nREJECTED"), expiry_note: t.includes("No automatic plan expiry runs"), shot: await shot("p4-rejected") };
});
await step("P4 later-scan mismatch display (FR-5.9) present", async () => {
  const t = await text(); return { later_scan: (t.match(/No later stored scan[^\n]*|Later scan[^\n]*/) || [])[0] };
});

// ---- P3 opportunity journey ----------------------------------------------------------------
await step("P3 scanner: stored scan outcome (qualified)", async () => {
  await go(`scanner?scan=${CFG.scan_key}&fixtures=1`); await sleep(800);
  const kind = await page.$eval("[data-testid='scan-outcome']", (n) => n.getAttribute("data-kind")).catch(() => null);
  return { outcome_kind: kind, outcome: await page.$eval("[data-testid='scan-outcome']", (n) => n.innerText.split("\n")).catch(() => null), shot: await shot("p3-scanner-qualified") };
});
let walkScan = null;
await step("P3 run an authorised MIT scan through the real pipeline (API from browser) and inspect", async () => {
  const refused = await api("POST", "/api/v1/scans", { mode: "MANUAL", trade_type: "MIT", universe: ["WALK"], as_of: "2024-07-31", dataset_id: CFG.dataset_id }, "browser-walk-late-" + Date.now());
  const r = await api("POST", "/api/v1/scans", { mode: "MANUAL", trade_type: "MIT", universe: ["WALK", "NOPE"], as_of: "2024-07-12", dataset_id: CFG.dataset_id }, "browser-walk-" + Date.now());
  let job = r.body?.data; const states = [job?.state];
  for (let i = 0; i < 60 && job && !["SUCCEEDED_COMPLETE", "SUCCEEDED_PARTIAL", "FAILED", "INTERRUPTED", "CANCELLED"].includes(job.state); i++) {
    await sleep(500); job = (await api("GET", `/api/v1/jobs/${job.job_id}`)).body?.data; states.push(job?.state);
  }
  walkScan = job?.result_ref;
  await go(`scanner?scan=${walkScan}&fixtures=1`); await sleep(800);
  const outcome = await page.$eval("[data-testid='scan-outcome']", (n) => ({ kind: n.getAttribute("data-kind"), lines: n.innerText.split("\n") })).catch(() => null);
  return { as_of_beyond_data: { http: refused.status, code: refused.body?.error?.code, message: refused.body?.error?.message }, http: r.status, job_states: [...new Set(states)], result_ref: walkScan, outcome, shot: await shot("p3-scanner-nothing-qualified") };
});
await step("P3 opportunities ingest + list (UI)", async () => {
  await go(`opportunities?fixtures=1`); await sleep(500);
  await page.evaluate((key) => { const s = [...document.querySelectorAll("label")].find((l) => l.innerText.startsWith("Stored scan"))?.querySelector("select"); if (s) { const set = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set; set.call(s, key); s.dispatchEvent(new Event("change", { bubbles: true })); } }, CFG.scan_key);
  await sleep(300);
  const btn = await page.evaluate(() => [...document.querySelectorAll("button")].map((b) => b.innerText.trim()).filter((x) => /ingest/i.test(x)));
  if (btn[0]) await click(btn[0]);
  await sleep(800); const t = await text();
  return { ingest_button: btn, discovered: (t.match(/Discovered\n(\d+)/) || [])[1], shows_syn: t.includes("SYN"), certified_claim: /\bCERTIFIED\b(?!_)/.test(t.replace(/UNCERTIFIED|NOT_CERTIFIED|not certified|Certified: false/gi, "")), shot: await shot("p3-opportunities") };
});
await step("P3 watchlist create / add / persist (UI)", async () => {
  await go("watchlists"); await sleep(400);
  await page.evaluate(() => { const i = [...document.querySelectorAll("label")].find((l) => l.innerText.startsWith("New watchlist"))?.querySelector("input"); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; set.call(i, "Browser validation list"); i.dispatchEvent(new Event("input", { bubbles: true })); });
  const createLabel = await page.evaluate(() => [...document.querySelectorAll("button")].map((b) => b.innerText.trim()).find((x) => /^create/i.test(x)));
  await click(createLabel); await sleep(600);
  await page.reload({ waitUntil: "networkidle0" }); await sleep(600);
  const t = await text();
  return { create_label: createLabel, persisted_after_reload: t.includes("Browser validation list"), eligibility_shown: t.includes("Eligibility"), shot: await shot("p3-watchlist") };
});
await step("P3 scan history lists both scans", async () => {
  await go(`scanner?fixtures=1`); await sleep(800); const t = await text();
  return { has_syn: t.includes(CFG.scan_key), has_walk: walkScan ? t.includes(walkScan) : null, shot: await shot("p3-scan-history") };
});
fs.writeFileSync(`${OUT}/../results.json`, JSON.stringify({ log, consoleErrors }, null, 2));
await browser.close();
console.log(JSON.stringify({ steps: log.length, failed: log.filter((x) => !x.ok).map((x) => x.step), consoleErrors: consoleErrors.length }));
