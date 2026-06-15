// Screenshot X3DOM viewpoints by index.
// Usage: node shot_cave.js <htmlPath> <prefix> <vpIndex...>
const puppeteer = require('puppeteer');
const path = require('path');
(async () => {
  const html = path.resolve(process.argv[2]);
  const prefix = process.argv[3];
  const idxs = process.argv.slice(4);
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl',
           '--ignore-gpu-blocklist', '--no-sandbox', '--enable-unsafe-swiftshader'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 900, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  await page.goto('file://' + html, { waitUntil: 'networkidle2', timeout: 60000 });
  await new Promise(r => setTimeout(r, 6000));
  for (const i of idxs) {
    await page.evaluate(n => {
      const vps = document.querySelectorAll('Viewpoint, viewpoint');
      vps.forEach((v, k) => v.setAttribute('set_bind', k === +n ? 'true' : 'false'));
    }, i);
    await new Promise(r => setTimeout(r, 2000));
    const out = `${prefix}_${i}.png`;
    await page.screenshot({ path: path.resolve(out) });
    console.log('wrote', out);
  }
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
