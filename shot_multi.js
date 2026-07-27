// Multi-viewpoint screenshots from one page load.
// Usage: node shot_multi.js <htmlPath> <prefix> <vp1> <vp2> ...
const puppeteer = require('puppeteer');
const path = require('path');
(async () => {
  const html = path.resolve(process.argv[2]);
  const prefix = process.argv[3];
  const vps = process.argv.slice(4);
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl',
           '--ignore-gpu-blocklist', '--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1680, height: 945, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  await page.goto('file://' + html, { waitUntil: 'networkidle2', timeout: 60000 });
  await new Promise(r => setTimeout(r, 7000));
  for (const vp of vps) {
    await page.evaluate(v => { if (v==='all'){ if(window.bindView) bindView('VP_all'); } else if (window.select){ select(v); } else if (window.bindView){ bindView('VP_'+v); } }, vp);
    await new Promise(r => setTimeout(r, 1800));
    const out = `${prefix}_${vp}.png`;
    await page.screenshot({ path: path.resolve(out) });
    console.log('wrote', out);
  }
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
