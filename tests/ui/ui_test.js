// End-to-end test of the real interface in Chromium.
// Usage: node tests/ui/ui_test.js [command...]   (default: python3 -m gamecheck)
// Starts GameCheck, drives the page, and fails if the page requests anything off this computer.
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const root = path.resolve(__dirname, "..", "..");
const cmd = process.argv.length > 2 ? process.argv.slice(2) : ["python3", "-m", "gamecheck"];
const shots = process.env.SHOTS_DIR;

function assert(cond, msg) { if (!cond) throw new Error("ASSERT: " + msg); }

async function startApp() {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "gc-ui-"));
  const proc = spawn(cmd[0], [...cmd.slice(1), "--no-browser"], {
    cwd: root, env: { ...process.env, GAMECHECK_DATA_DIR: dataDir }, stdio: ["ignore", "pipe", "pipe"],
  });
  const url = await new Promise((resolve, reject) => {
    let out = "";
    const timer = setTimeout(() => reject(new Error("app did not start: " + out)), 30000);
    proc.stdout.on("data", (d) => {
      out += d;
      const m = out.match(/http:\/\/127\.0\.0\.1:\d+\//);
      if (m) { clearTimeout(timer); resolve(m[0]); }
    });
    proc.stderr.on("data", (d) => { out += d; });
    proc.on("exit", (code) => reject(new Error("app exited " + code + ": " + out)));
  });
  return { proc, url };
}

(async () => {
  const { proc, url } = await startApp();
  const browser = await chromium.launch();
  const external = [];
  const errors = [];
  try {
    // bypassCSP lets Playwright run its own checks; the app's CSP itself is covered by test_server.py.
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, bypassCSP: true });
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
    await page.route("**/*", (route) => {
      const u = new URL(route.request().url());
      if (u.hostname === "127.0.0.1") return route.continue();
      external.push(u.href);
      return route.abort();
    });

    await page.goto(url);
    await page.waitForSelector(".game");
    assert(await page.getAttribute("html", "dir") === "rtl", "page is RTL");
    assert((await page.textContent("h2#sys-title")).includes("مواصفات جهازك"), "Arabic heading");
    const cards = await page.locator(".game").count();
    assert(cards === 14, "all games listed, got " + cards);
    assert((await page.textContent("#footer")).includes("المكتبة المضمَّنة"), "footer shows bundled library");
    if (shots) await page.screenshot({ path: path.join(shots, "1-auto-detect.png"), fullPage: true });

    // Search filters the list.
    await page.fill("#search", "elden");
    assert(await page.locator(".game").count() === 1, "search filters");
    await page.fill("#search", "");

    // Manually choose hardware (this server's GPU is not detectable) and verify verdicts update.
    await page.click("#toggle-override");
    await page.waitForFunction(() => document.querySelectorAll("#gpu-list option").length > 50);
    await page.fill("#cpu-pick", "AMD Ryzen 7 7800X3D");
    await page.fill("#gpu-pick", "NVIDIA GeForce RTX 4070");
    await page.click("#save-override");
    await page.waitForFunction(() => document.querySelector("#override-status").textContent.includes("تم الحفظ"));
    await page.waitForFunction(() => document.querySelector("#specs").textContent.includes("RTX 4070"));
    assert((await page.textContent("#specs")).includes("اخترته يدويًا"), "manual choice is labelled");

    await page.fill("#search", "cyberpunk");
    await page.click(".game");
    await page.waitForSelector("dialog[open]");
    const dialog = await page.textContent("#d-body");
    assert(!dialog.includes("null") && !dialog.includes("undefined"), "no null/undefined text in details");
    assert(dialog.includes("المعالج") && dialog.includes("كرت الشاشة"), "details table");
    assert((await page.locator("#d-body tbody tr").count()) >= 5, "component rows");
    const gpuRow = await page.locator("#d-body tbody tr", { hasText: "كرت الشاشة" }).textContent();
    assert(gpuRow.includes("يحقق الموصى به"), "RTX 4070 meets Cyberpunk recommended: " + gpuRow);
    if (shots) await page.screenshot({ path: path.join(shots, "2-details.png") });
    await page.click("#d-close");
    await page.fill("#search", "");

    // Invalid manual choice is refused.
    await page.fill("#gpu-pick", "Totally Fake GPU");
    await page.click("#save-override");
    await page.waitForFunction(() => document.querySelector("#override-status").textContent.includes("من القائمة"));

    // Filter chips.
    await page.click(".chip >> nth=2");
    const filtered = await page.locator(".game").count();
    assert(filtered < cards, "chip filter narrows list");
    await page.click(".chip >> nth=0");

    // Library update without a configured source explains itself and keeps working.
    await page.click("#update");
    await page.waitForFunction(() => document.querySelector("#update-status").textContent.length > 20);
    const msg = await page.textContent("#update-status");
    assert(msg.includes("لم يُضبط") || msg.includes("تعذّر") || msg.includes("محدَّثة"), "update message: " + msg);

    // Phone width: no horizontal scroll.
    await page.setViewportSize({ width: 390, height: 844 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    assert(overflow <= 0, "no horizontal scroll on phone width, overflow=" + overflow);
    if (shots) await page.screenshot({ path: path.join(shots, "3-phone.png"), fullPage: true });
    await page.setViewportSize({ width: 1280, height: 900 });

    // Exit button stops the program.
    await page.click("#quit");
    await page.waitForSelector(".closed");
    const exited = await new Promise((resolve) => {
      const t = setTimeout(() => resolve(false), 5000);
      proc.on("exit", () => { clearTimeout(t); resolve(true); });
    });
    assert(exited, "process exits after pressing Exit");

    assert(external.length === 0, "no external requests: " + external.join(", "));
    assert(errors.length === 0, "no page errors: " + errors.join(" | "));
    console.log("UI test passed");
  } finally {
    await browser.close();
    if (proc.exitCode === null) proc.kill();
  }
})().catch((e) => { console.error(e); process.exit(1); });
