// Supplemental browser checks: FR-4.2 zoom/crosshair, FR-4.3 drawing persistence, UX-004 rename. FIXTURE data.
import { createRequire } from "module"; import fs from "fs";
const require = createRequire("/Users/yash/day-trader-skill/platform/web/package.json");
const puppeteer = require("puppeteer-core");
const OUT = process.argv[2]; const BASE = "http://127.0.0.1:8899/";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage(); await page.setViewport({ width: 1440, height: 1000 });
const out = {};
const click = (label) => page.evaluate((l) => { const b = [...document.querySelectorAll("button")].find((x) => x.innerText.trim() === l); if (!b) return false; b.click(); return true; }, label);
await page.goto(BASE + "#/analysis?scan=scan-browser-syn&symbol=SYN&fixtures=1&timeframe=D", { waitUntil: "networkidle0" });
await page.waitForSelector("[data-testid='candle-chart'] canvas"); await sleep(600);
const host = await page.$("[data-testid='candle-chart']"); const box = await host.boundingBox();
const axis = () => page.$eval("[data-testid='candle-chart']", (n) => n.innerText.replace(/\s+/g, " ").slice(-120));
const before = await axis();
await click("+"); await click("+"); await sleep(400); const zoomed = await axis();
await click("Fit"); await sleep(400); const fitted = await axis();
await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.4); await sleep(400);
out.crosshair_legend = await page.$eval("[data-testid='candle-chart']", (n) => n.parentElement.firstChild.textContent);
out.zoom_changed_axis = before !== zoomed; out.fit_restored = fitted === before;
await page.screenshot({ path: `${OUT}/21-p2-zoom-crosshair.png` });
out.mark_clicked = await click("Save a horizontal mark"); await sleep(800);
await page.reload({ waitUntil: "networkidle0" }); await sleep(800);
const ann = await page.evaluate(() => [...document.querySelectorAll("li button")].map((b) => b.innerText).filter((t) => t.startsWith("horizontal")));
out.drawing_persisted_after_reload = ann;
await page.screenshot({ path: `${OUT}/22-p2-drawing-persisted.png`, fullPage: true });
if (ann.length) { await page.evaluate(() => [...document.querySelectorAll("li button")].find((b) => b.innerText.startsWith("horizontal")).click()); await sleep(300); out.delete_clicked = await click("Delete selected drawing"); await sleep(600); await page.reload({ waitUntil: "networkidle0" }); await sleep(600);
  out.after_delete = await page.evaluate(() => [...document.querySelectorAll("li button")].map((b) => b.innerText).filter((t) => t.startsWith("horizontal")).length); }
await page.goto(BASE + "#/watchlists", { waitUntil: "networkidle0" }); await sleep(600);
await page.evaluate(() => { const b = [...document.querySelectorAll("button")].find((x) => x.innerText.includes("Browser validation list")); b && b.click(); }); await sleep(400);
await page.evaluate(() => { const i = [...document.querySelectorAll("label")].find((l) => l.innerText.startsWith("Rename"))?.querySelector("input"); if (!i) return; const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; set.call(i, "Renamed browser list"); i.dispatchEvent(new Event("input", { bubbles: true })); });
const renameBtn = await page.evaluate(() => [...document.querySelectorAll("button")].map((b) => b.innerText.trim()).find((t) => /^rename|save name/i.test(t)));
out.rename_button = renameBtn; if (renameBtn) { await click(renameBtn); await sleep(600); }
await page.reload({ waitUntil: "networkidle0" }); await sleep(600);
out.rename_persisted = (await page.$eval("body", (n) => n.innerText)).includes("Renamed browser list");
await page.screenshot({ path: `${OUT}/23-p3-watchlist-renamed.png`, fullPage: true });
fs.writeFileSync(`${OUT}/../results_supplement.json`, JSON.stringify(out, null, 2)); console.log(JSON.stringify(out));
await browser.close();
