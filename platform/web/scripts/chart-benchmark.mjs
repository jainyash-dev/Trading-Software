import puppeteer from "puppeteer-core";

const chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const url = process.env.GTF_BENCH_URL ?? "http://127.0.0.1:4173/?fixtures=1&bench=1#/analysis";

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ["--no-sandbox", "--disable-gpu"],
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1100, height: 720 });
  await page.goto(url, { waitUntil: "networkidle0", timeout: 60000 });
  await page.waitForFunction(
    () => {
      const node = document.getElementById("bench-results");
      return Boolean(node && node.textContent && node.textContent.includes("large"));
    },
    { timeout: 60000 },
  );
  const raw = await page.$eval("#bench-results", (node) => node.textContent ?? "");
  const banner = await page.$eval("body", (node) => node.innerText.includes("FIXTURE_NOT_MARKET_DATA"));
  const canvas = await page.$("#bench-host canvas, [data-testid='candle-chart'] canvas");
  const chip = await page.$eval("body", (node) => node.innerText.includes("Unknown status"));
  console.log(JSON.stringify({ banner, canvas: Boolean(canvas), chip, report: JSON.parse(raw) }, null, 2));
  if (!banner) process.exitCode = 1;
} finally {
  await browser.close();
}
