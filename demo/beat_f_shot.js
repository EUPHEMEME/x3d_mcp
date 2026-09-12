#!/usr/bin/env node
// beat_f_shot.js v1.0 2026-08-31 — Beat F: headless screenshot with OFFLINE ENFORCEMENT.
// Like shot_plain.js, but intercepts every network request and ABORTS anything that
// is not same-host (localhost) — so the screenshot doubles as a proof the page loads
// with zero external (CDN) fetches. Exits non-zero if any external request was even
// attempted, and prints every one.
// Usage: node demo/beat_f_shot.js <url> <out.png> [wait_ms]
const puppeteer = require('puppeteer'), path = require('path');
(async () => {
  const url = process.argv[2], out = process.argv[3];
  const wait = parseInt(process.argv[4] || '8000');
  const host = new URL(url).host;
  const external = [], served = [];
  const b = await puppeteer.launch({ headless: 'new', args: [
    '--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl',
    '--ignore-gpu-blocklist', '--no-sandbox', '--enable-unsafe-swiftshader'] });
  const p = await b.newPage();
  await p.setViewport({ width: 1200, height: 780 });
  await p.setRequestInterception(true);
  p.on('request', r => {
    const u = new URL(r.url());
    if (u.host === host || u.protocol === 'data:') { served.push(r.url()); r.continue(); }
    else { external.push(r.url()); r.abort('blockedbyclient'); }
  });
  p.on('pageerror', e => console.log('ERR', e.message));
  p.on('console', m => { if (/error|fail|exception/i.test(m.text())) console.log('LOG', m.text().slice(0, 200)); });
  await p.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
  await new Promise(r => setTimeout(r, wait));
  await p.screenshot({ path: path.resolve(out) });
  await b.close();
  console.log('wrote', out);
  console.log('requests served same-host:', served.length);
  if (external.length) {
    console.log('EXTERNAL REQUESTS ATTEMPTED (blocked):', external.length);
    external.forEach(u => console.log('  BLOCKED', u));
    console.log('VERDICT: NOT OFFLINE-CLEAN');
    process.exit(1);
  }
  console.log('external requests attempted: 0  -> OFFLINE-CLEAN');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
