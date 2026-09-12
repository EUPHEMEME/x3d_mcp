#!/usr/bin/env node
// competitions/capture_draft.js v1.1 2026-08-31 — headless 1080p frame capture of
// (v1.1: stills captured first + neutral-pose shots before gaits — ModeSwitch
//  'stand' freezes the current pose, it does not re-neutralize)
// anatomy_explorer.html for the Web3D 2026 draft competition videos.
//
// METHOD: deterministic VIRTUAL-CLOCK capture. Before any page script runs we
// replace performance.now / Date.now / requestAnimationFrame with a manually
// stepped clock, then advance exactly 1/FPS per captured frame. X_ITE's render
// loop (rAF) and TimeSensor gaits (Date.now) both follow the virtual clock, so
// the output is a perfectly smooth 24 fps regardless of SwiftShader's real
// render speed. setTimeout/fetch stay real-time (boot path unaffected; the
// loader's 45 s stall guard compares virtual Date.now deltas, and we only creep
// the clock ~33 ms per real 100 ms while loading, so it can never fire).
//
// Usage: node competitions/capture_draft.js <url> <outdir> [fps] [scale]
//   scale: duration multiplier for a quick smoke run (e.g. 0.15)
// Output: <outdir>/<shot>/f_%05d.jpg per shot + two PNG stills + manifest.json
const puppeteer = require('puppeteer'), path = require('path'), fs = require('fs');

const URL_ = process.argv[2] || 'http://localhost:8099/anatomy_explorer.html';
const OUT = path.resolve(process.argv[3] || 'competitions/footage');
const FPS = parseFloat(process.argv[4] || '24');
const SCALE = parseFloat(process.argv[5] || '1');
const STEP_MS = 1000 / FPS;

// CAPTURE order ≠ edit order: the gaits leave the skeleton frozen mid-pose
// (ModeSwitch 'stand' freezes, it does not re-neutralize), so every neutral-pose
// shot is captured BEFORE any gait runs. The numeric ids keep the EDIT order.
const SHOTS = [
  { id: '01_turntable', kind: 'orbit', dur: 12 },
  { id: '05_search_clavicle', kind: 'search', query: 'collarbone', bone: 'l_clavicle', dur: 9 },
  { id: '06_tooth', kind: 'pick', bone: 'tooth_incisor_8_11', dur: 6 },
  { id: '07_ethmoid', kind: 'pick', bone: 'ethmoid', dur: 6 },
  { id: '08_recon', kind: 'recon', dur: 9 },
  { id: '09_tour', kind: 'tour', tour: 'spine', dur: 9 },
  { id: '02_walk', kind: 'gait', timer: 'WalkTimer', dur: 15 },
  { id: '03_run', kind: 'gait', timer: 'RunTimer', dur: 15 },
  { id: '04_jump', kind: 'gait', timer: 'JumpTimer', dur: 15 },
];

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await puppeteer.launch({ headless: 'new', args: [
    '--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl',
    '--ignore-gpu-blocklist', '--no-sandbox', '--enable-unsafe-swiftshader',
    '--hide-scrollbars'] });
  const p = await b.newPage();
  await p.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  p.on('pageerror', e => console.log('PAGEERR', e.message));

  // ---- virtual clock, installed before any page script ----
  await p.evaluateOnNewDocument(() => {
    let vt = 0;
    const EPOCH = 1756600000000;         // fixed epoch: deterministic TimeSensor phase
    let rafQ = [];
    window.__vt = {
      now: () => vt,
      step(ms) {
        vt += ms;
        const q = rafQ; rafQ = [];
        q.forEach(cb => { try { cb(vt); } catch (e) { console.error('rafcb', e); } });
      },
    };
    performance.now = () => vt;
    Date.now = () => EPOCH + vt;
    const OD = Date;
    // keep `new Date()` consistent with Date.now for any consumer
    window.Date = new Proxy(OD, {
      construct(t, a) { return a.length ? new t(...a) : new t(EPOCH + vt); },
      get(t, k) { return k === 'now' ? (() => EPOCH + vt) : t[k]; },
    });
    window.requestAnimationFrame = cb => (rafQ.push(cb), rafQ.length);
    window.cancelAnimationFrame = () => {};
  });

  console.log('goto', URL_);
  await p.goto(URL_, { waitUntil: 'networkidle2', timeout: 120000 });

  // ---- boot: creep the clock until the loader is gone, then settle ----
  const t0 = Date.now();
  for (;;) {
    const gone = await p.evaluate(() =>
      document.getElementById('load').classList.contains('gone'));
    if (gone) break;
    if (Date.now() - t0 > 300000) throw new Error('scene never finished loading');
    await p.evaluate(() => window.__vt.step(33.3));
    await new Promise(r => setTimeout(r, 100));
  }
  // settle: fade out overlay (CSS, real time) + a few virtual frames
  for (let i = 0; i < 24; i++) await p.evaluate(() => window.__vt.step(33.3));
  await new Promise(r => setTimeout(r, 800));
  console.log('scene loaded, hooked bones:',
    await p.evaluate(() => Object.keys(M).length));

  // ---- page-side shot driver ----
  await p.evaluate(() => {
    window.__DRAFT = {
      orbitVP: null,
      reset() {
        try { document.querySelector('#tabs button[data-m=explore]').click(); } catch (e) {}
        try { document.getElementById('reset').click(); } catch (e) {}
      },
      orbit(a) {
        if (!this.orbitVP) {
          const vp = scene.createNode('Viewpoint');
          vp.description = 'draft orbit';
          vp.fieldOfView = 0.72; vp.nearDistance = 0.01; vp.farDistance = 80;
          if (typeof scene.addRootNode === 'function') scene.addRootNode(vp);
          else scene.rootNodes.push(vp);
          this.orbitVP = vp;
        }
        const c = [0, 0.92, 0], r = 2.75, vp = this.orbitVP;
        vp.position = new X3D.SFVec3f(c[0] + r * Math.sin(a), c[1], c[2] + r * Math.cos(a));
        vp.centerOfRotation = new X3D.SFVec3f(c[0], c[1], c[2]);
        vp.orientation = new X3D.SFRotation(0, 1, 0, a);
        vp.set_bind = true;
      },
      tick(shot, t) {                    // t = seconds into the shot (virtual)
        const hit = (at) => t >= at && t - at < 1 / __DRAFT.fps;
        switch (shot.kind) {
          case 'orbit':
            this.orbit(2 * Math.PI * t / shot.dur0); break;
          case 'gait':
            if (hit(0)) setGait(shot.timer); break;
          case 'pick':
            if (hit(0)) select(shot.bone);
            if (hit(0.8)) frameSelected(shot.bone);
            break;
          case 'search': {
            const q = document.getElementById('q');
            const n = shot.query.length, tEnd = 1.6;
            if (t <= tEnd + 0.2) {
              const k = Math.min(n, Math.ceil(n * t / tEnd));
              const v = shot.query.slice(0, k);
              if (q.value !== v) { q.value = v; q.dispatchEvent(new Event('input')); }
            }
            if (hit(3.2)) {
              const li = document.querySelector(`#hits li[data-n="${shot.bone}"]`)
                      || document.querySelector('#hits li');
              if (li) pickHit(li); else select(shot.bone);
            }
            if (hit(4.0)) frameSelected(shot.bone);
            break;
          }
          case 'recon':
            if (hit(0)) document.querySelector('#tabs button[data-m=learn]').click();
            break;
          case 'tour':
            if (hit(0)) {
              document.querySelector('#tabs button[data-m=learn]').click();
              tour.start(shot.tour);
            }
            if (hit(shot.dur0 / 2)) tour.next();
            break;
        }
      },
    };
  });
  await p.evaluate(fps => { window.__DRAFT.fps = fps; }, FPS);

  // ---- stills first (PNG, 1920x1080) — neutral pose, before any gait ----
  const manifest = { url: URL_, fps: FPS, scale: SCALE, captured: [], stills: [] };
  const still1 = path.join(OUT, 'still_full_skeleton.png');
  await p.screenshot({ path: still1, type: 'png' });
  manifest.stills.push('still_full_skeleton.png');
  console.log('still', still1);

  await p.evaluate(() => { select('l_clavicle'); });
  for (let i = 0; i < 12; i++) await p.evaluate(() => window.__vt.step(33.3));
  await p.evaluate(() => { frameSelected('l_clavicle'); });
  for (let i = 0; i < 60; i++) await p.evaluate(() => window.__vt.step(33.3));
  const still2 = path.join(OUT, 'still_bone_pick_clavicle.png');
  await p.screenshot({ path: still2, type: 'png' });
  manifest.stills.push('still_bone_pick_clavicle.png');
  console.log('still', still2);

  // ---- capture loop ----
  for (const shot of SHOTS) {
    const dur = Math.max(1, shot.dur * SCALE);
    const nf = Math.round(dur * FPS);
    const dir = path.join(OUT, shot.id);
    fs.mkdirSync(dir, { recursive: true });
    await p.evaluate(() => window.__DRAFT.reset());
    for (let i = 0; i < 12; i++) await p.evaluate(() => window.__vt.step(33.3));
    const sh = { ...shot, dur0: dur };
    const tShot = Date.now();
    for (let i = 0; i < nf; i++) {
      await p.evaluate((s, t) => window.__DRAFT.tick(s, t), sh, i / FPS);
      await p.evaluate(ms => window.__vt.step(ms), STEP_MS);
      await p.screenshot({ path: path.join(dir, `f_${String(i).padStart(5, '0')}.jpg`),
                           type: 'jpeg', quality: 90 });
    }
    const secs = ((Date.now() - tShot) / 1000).toFixed(1);
    console.log(`shot ${shot.id}: ${nf} frames (${dur}s @ ${FPS}fps) in ${secs}s real`);
    manifest.captured.push({ id: shot.id, frames: nf, dur });
  }

  fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2));
  await b.close();
  console.log('DONE — frames in', OUT);
})().catch(e => { console.error('FATAL', e); process.exit(1); });
