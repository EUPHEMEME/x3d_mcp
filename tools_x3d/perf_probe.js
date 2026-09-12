#!/usr/bin/env node
// perf_probe.js v1.1 2026-08-31 — headless perf A/B for the LOA5 Anatomy Explorer
// (shot_*.js pattern: puppeteer + swiftshader WebGL, no GUI).
//
// Measures, per rendering config, on a fresh page each time:
//   * TTFF  — time from navigation until the #load overlay goes .gone
//             (manifest + scene fetched, parsed, hooked; first scene frame)
//   * FPS   — 20 s requestAnimationFrame sample while the RUN gait cycles,
//             plus X_ITE's own browser.currentFrameRate sampled each second
// Configs (2x2, shading x shadows): A = PHONG + shadows (the authored default),
// B = GOURAUD + no-shadows, C = PHONG + no-shadows, D = GOURAUD + shadows.
//
// MEASURED 2026-08-31 (Hétu M5 Max, headless Chromium swiftshader — a CPU
// rasterizer, so absolute fps is a conservative floor and the RATIO between
// configs is the signal). serve_gzip.py on :8099, Run gait active, 1366x768:
//   A  PHONG   + shadows    : TTFF 4.3 s   rAF 4.4 fps   min-1s 4.2   X_ITE avg 4.2
//   B  GOURAUD + no-shadow  : TTFF 3.7 s   rAF 5.7 fps   min-1s 5.6   X_ITE avg 8.3
//   C  PHONG   + no-shadow  : TTFF 3.4 s   rAF 5.8 fps   min-1s 5.6   X_ITE avg 5.6
//   D  GOURAUD + shadows    : TTFF 3.4 s   rAF 4.4 fps   min-1s 4.2   X_ITE avg 4.3
// VERDICT: the two variables separate cleanly — shadow mapping costs ~24% of
// the frame (4.4 vs 5.7-5.8 fps, identical under either shading), while PHONG
// vs GOURAUD costs NOTHING measurable (A==D, B==C). Side-by-side screenshots
// are visually indistinguishable (dark studio, no visible ground plane for the
// shadows to land on). So anatomy_explorer.html KEEPS PHONG (better-looking,
// free) and turns KeyLight.shadows off at runtime. RECOMMENDATION for
// build_anatomy_spine.py (not edited here): set the KeyLight's shadows='false'
// so the bare .x3d gets the same ~24% back in other viewers. Neither config
// reaches 30 fps on the swiftshader floor — on real GPUs (M5 Max, iPhone) the
// scene runs far above it; re-run this probe if the scene grows layers.
//
// Usage: node tools_x3d/perf_probe.js [url] [shot_prefix]
//   url default http://localhost:8099/anatomy_explorer.html
//   shot_prefix: if given, writes <prefix>_A.png ... <prefix>_D.png
const puppeteer = require('puppeteer'), path = require('path');

const URL_ = process.argv[2] || 'http://localhost:8099/anatomy_explorer.html';
const SHOT = process.argv[3] || '';
const SAMPLE_MS = 20000;

const CONFIGS = [
  { id: 'A', label: 'PHONG + shadows',     shading: 'PHONG',   shadows: true  },
  { id: 'B', label: 'GOURAUD + no-shadow', shading: 'GOURAUD', shadows: false },
  { id: 'C', label: 'PHONG + no-shadow',   shading: 'PHONG',   shadows: false },
  { id: 'D', label: 'GOURAUD + shadows',   shading: 'GOURAUD', shadows: true  },
];

async function runConfig(browser, cfg) {
  const p = await browser.newPage();
  await p.setViewport({ width: 1366, height: 768 });
  p.on('pageerror', e => console.log('  ERR', e.message));
  p.on('console', m => { if (/error|fail|exception/i.test(m.text())) console.log('  LOG', m.text().slice(0, 160)); });

  const t0 = Date.now();
  await p.goto(URL_, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.waitForFunction(
    () => document.querySelector('#load').classList.contains('gone'),
    { polling: 'raf', timeout: 120000 });
  const ttff = (Date.now() - t0) / 1000;

  // apply the config, then start the Run gait through the page's own button
  await p.evaluate(c => {
    const cv = document.querySelector('#cv');
    try { cv.browser.setBrowserOption('Shading', c.shading); } catch (e) {}
    try { cv.browser.currentScene.getNamedNode('KeyLight').shadows = c.shadows; } catch (e) {}
    document.querySelector('#gait button[data-t="RunTimer"]').click();
  }, cfg);
  await new Promise(r => setTimeout(r, 1500));   // let the transition settle

  const s = await p.evaluate(ms => new Promise(res => {
    const cv = document.querySelector('#cv');
    const t0 = performance.now();
    let n = 0, bN = 0, bStart = t0;
    const buckets = [], xite = [];
    function tick(t) {
      n++; bN++;
      if (t - bStart >= 1000) {
        buckets.push(bN * 1000 / (t - bStart)); bN = 0; bStart = t;
        try { xite.push(Number(cv.browser.currentFrameRate)); } catch (e) {}
      }
      if (t - t0 < ms) requestAnimationFrame(tick);
      else res({
        raf: n * 1000 / (t - t0),
        min1s: buckets.length ? Math.min(...buckets) : 0,
        xiteAvg: xite.length ? xite.reduce((a, b) => a + b, 0) / xite.length : 0,
      });
    }
    requestAnimationFrame(tick);
  }), SAMPLE_MS);

  if (SHOT) {
    const out = path.resolve(`${SHOT}_${cfg.id}.png`);
    await p.screenshot({ path: out });
    console.log('  wrote', out);
  }
  await p.close();
  return { ttff, ...s };
}

(async () => {
  console.log(`perf_probe.js v1.1 — ${URL_} — ${SAMPLE_MS / 1000}s Run-gait sample per config`);
  const b = await puppeteer.launch({ headless: 'new', args: [
    '--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl',
    '--ignore-gpu-blocklist', '--no-sandbox', '--enable-unsafe-swiftshader'] });
  const results = [];
  for (const cfg of CONFIGS) {
    console.log(`config ${cfg.id}: ${cfg.label}`);
    const r = await runConfig(b, cfg);
    results.push({ cfg, r });
    console.log(`  TTFF ${r.ttff.toFixed(1)} s   rAF ${r.raf.toFixed(1)} fps` +
                `   min-1s ${r.min1s.toFixed(1)}   X_ITE avg ${r.xiteAvg.toFixed(1)} fps`);
  }
  await b.close();
  const [A, B] = results;
  const gain = (B.r.raf - A.r.raf) / A.r.raf * 100;
  console.log(`\nB vs A: ${gain >= 0 ? '+' : ''}${gain.toFixed(1)}% rAF fps`);
  console.log(A.r.raf >= 30
    ? 'A (PHONG + shadows) holds >=30 fps -> keep the better-looking default.'
    : (B.r.raf >= 30
      ? 'A drops below 30 fps but B holds it -> recommend GOURAUD/no-shadows (spine change).'
      : 'NEITHER holds 30 fps headlessly -- judge on real hardware.'));
})().catch(e => { console.error('FATAL', e); process.exit(1); });
