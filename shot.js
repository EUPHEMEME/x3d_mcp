// Headless screenshot of an X3D/X_ITE demo page. Usage: node shot.js <htmlPath> <outPng> [waitMs]
const puppeteer = require('puppeteer');
const path = require('path');
(async () => {
  const html = path.resolve(process.argv[2]);
  const out = path.resolve(process.argv[3]);
  const wait = parseInt(process.argv[4] || '7000', 10);
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl',
           '--ignore-gpu-blocklist', '--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1680, height: 945, deviceScaleFactor: 1 });
  page.on('console', m => console.log('PAGE:', m.type(), m.text()));
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  await page.goto('file://' + html, { waitUntil: 'networkidle2', timeout: 60000 });
  await new Promise(r => setTimeout(r, wait));
  await page.screenshot({ path: out });
  console.log('wrote', out);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
