// Space background: rotating starfield, nebula gradients, constellation lines,
// and the 3-phase hyperspace warp effect. Single IIFE because the hyperspace
// animation shares canvas state (W, H, cx, cy, HS_RAYS) with the regular draw loop.
//
// Exposes window.triggerHyperspace(cb) - called by boot.js and the Launch button.

(function () {
  const canvas = document.getElementById('space-bg');
  const ctx = canvas.getContext('2d');
  const WARP_MS   = 3200;    // initial warp-in duration on page load
  const ROT_SPEED = 0.00014; // very slow whole-scene rotation per frame

  // Hyperspace departure timings in ms - phase 1 builds rays, phase 2 jumps, phase 3 flashes
  const HS_BUILDUP = 1600;
  const HS_JUMP    = 1100;
  const HS_FLASH   = 380;
  const HS_TOTAL   = HS_BUILDUP + HS_JUMP + HS_FLASH;

  // 300 chunky white vector rays - Asteroids / Star Wars arcade aesthetic
  const HS_RAYS = Array.from({ length: 300 }, () => {
    const angle  = Math.random() * Math.PI * 2;
    const speed  = 0.40 + Math.random() * 1.0;
    const bright = Math.random();
    let bri, w;
    // 3 brightness/width tiers - majority are dim and thin
    if      (bright > 0.85) { bri = 0.90; w = 2.5 + Math.random() * 1.5; }
    else if (bright > 0.55) { bri = 0.55 + Math.random() * 0.25; w = 1.2 + Math.random() * 0.8; }
    else                    { bri = 0.20 + Math.random() * 0.30; w = 0.6 + Math.random() * 0.5; }
    return { angle, speed, r: 255, g: 255, b: 255, bri, w };
  });

  function rnd(a, b) { return a + Math.random() * (b - a); }

  // Stars come in 4 colours weighted toward blue-white (more realistic than pure white)
  function starColor() {
    const v = Math.random();
    if (v < 0.55) return [210, 225, 255];  // blue-white
    if (v < 0.78) return [255, 255, 255];  // pure white
    if (v < 0.92) return [255, 245, 165];  // yellow
    return [255, 180, 95];                  // orange
  }

  // Fractional positions (0-1) so stars scale with the window on resize
  const stars = Array.from({ length: 180 }, () => {
    const bright = Math.random();
    let size, bri;
    if      (bright > 0.96) { size = rnd(2.2, 3.2); bri = rnd(0.85, 1.0); }
    else if (bright > 0.82) { size = rnd(1.2, 2.0); bri = rnd(0.55, 0.85); }
    else                    { size = rnd(0.3, 1.0);  bri = rnd(0.18, 0.55); }
    const [sr, sg, sb] = starColor();
    return {
      fx: Math.random(), fy: Math.random(),
      r: sr, g: sg, b: sb, bri, size,
      ts: rnd(0.004, 0.022),  // twinkle speed
      to: rnd(0, Math.PI * 2), // twinkle phase offset
    };
  });

  // Each nebula is 4 offset radial gradients stacked - mimics multi-colour zones of real
  // emission nebulae (eg Trifid: cyan outer ring, hot rose, orange wisp, white core).
  const NEBULAS = [
    // Trifid-style
    { fx: 0.10, fy: 0.20, fr: 0.32, layers: [
      { ox:  0.00, oy:  0.00, rs: 1.00, r:   0, g: 170, b: 220, a: 0.11 },
      { ox:  0.18, oy: -0.12, rs: 0.60, r: 210, g:  50, b: 130, a: 0.15 },
      { ox: -0.14, oy:  0.20, rs: 0.45, r: 230, g:  85, b:  30, a: 0.09 },
      { ox:  0.06, oy:  0.04, rs: 0.17, r: 255, g: 215, b: 185, a: 0.28 },
    ]},
    // Orion-style: deep blue → teal → bright cyan → ice-white core
    { fx: 0.82, fy: 0.10, fr: 0.28, layers: [
      { ox:  0.00, oy:  0.00, rs: 1.00, r:  15, g:  70, b: 210, a: 0.11 },
      { ox: -0.16, oy:  0.12, rs: 0.58, r:   0, g: 200, b: 175, a: 0.14 },
      { ox:  0.12, oy:  0.10, rs: 0.40, r:  80, g: 150, b: 255, a: 0.09 },
      { ox: -0.04, oy: -0.06, rs: 0.15, r: 200, g: 230, b: 255, a: 0.28 },
    ]},
    // Eta Carinae-style: crimson → orange → magenta → gold-white core
    { fx: 0.88, fy: 0.80, fr: 0.30, layers: [
      { ox:  0.00, oy:  0.00, rs: 1.00, r: 190, g:  20, b:  50, a: 0.11 },
      { ox: -0.18, oy: -0.10, rs: 0.62, r: 240, g:  95, b:  20, a: 0.15 },
      { ox:  0.12, oy:  0.16, rs: 0.44, r: 210, g:  55, b: 130, a: 0.08 },
      { ox: -0.02, oy:  0.03, rs: 0.17, r: 255, g: 225, b: 145, a: 0.26 },
    ]},
    // Helix-style: violet → rose → blue accent → lavender-white core
    { fx: 0.15, fy: 0.85, fr: 0.27, layers: [
      { ox:  0.00, oy:  0.00, rs: 1.00, r: 140, g:  25, b: 230, a: 0.11 },
      { ox:  0.15, oy: -0.15, rs: 0.55, r: 230, g:  55, b: 165, a: 0.14 },
      { ox: -0.10, oy:  0.12, rs: 0.42, r:  50, g: 110, b: 250, a: 0.08 },
      { ox:  0.02, oy: -0.04, rs: 0.16, r: 230, g: 205, b: 255, a: 0.27 },
    ]},
  ];

  let W, H, cx, cy, constellations = [];
  let frame = 0, rot = 0;
  const t0 = performance.now();

  // Hyperspace state - set by triggerHyperspace, consumed by draw loop
  let hsActive = false, hsStart = 0, hsCb = null;

  window.triggerHyperspace = function (cb) {
    hsActive = true;
    hsStart  = performance.now();
    hsCb     = cb || null;
  };

  // Connect any two stars within 20% of the screen, capped at 2 connections each,
  // and only 35% of candidates - gives a sparse, organic constellation look.
  function buildConstellations() {
    constellations = [];
    const thresh = Math.min(W, H) * 0.20;
    const connCount = new Array(stars.length).fill(0);
    for (let i = 0; i < stars.length; i++) {
      if (connCount[i] >= 2) continue;
      for (let j = i + 1; j < stars.length; j++) {
        if (connCount[i] >= 2 || connCount[j] >= 2) continue;
        const dx = (stars[i].fx - stars[j].fx) * W;
        const dy = (stars[i].fy - stars[j].fy) * H;
        if (Math.sqrt(dx * dx + dy * dy) < thresh && Math.random() < 0.35) {
          constellations.push([i, j]);
          connCount[i]++; connCount[j]++;
        }
      }
    }
  }

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    cx = W / 2; cy = H / 2;
    buildConstellations();
  }
  window.addEventListener('resize', resize);
  resize();

  function easeOut(t)  { return 1 - Math.pow(1 - t, 3); }
  function easeIn2(t)  { return t * t; }

  function drawHyperspace(now) {
    const e = now - hsStart;
    if (e >= HS_TOTAL) {
      hsActive = false;
      if (hsCb) { hsCb(); hsCb = null; }
      return;
    }

    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, W, H);

    const diag = Math.hypot(W, H);

    if (e < HS_BUILDUP) {
      // Phase 1: short vector dashes grow outwards from the centre
      const t = easeIn2(e / HS_BUILDUP);
      const void0 = diag * 0.05;

      ctx.lineCap = 'square';
      for (const ray of HS_RAYS) {
        const cos = Math.cos(ray.angle), sin = Math.sin(ray.angle);
        const head = void0 + diag * t * t * 0.65 * ray.speed;
        if (head <= void0) continue;
        ctx.beginPath();
        ctx.moveTo(cx + cos * void0, cy + sin * void0);
        ctx.lineTo(cx + cos * head,  cy + sin * head);
        ctx.strokeStyle = `rgba(255,255,255,${ray.bri * Math.min(1, t * 3.5)})`;
        ctx.lineWidth = ray.w;
        ctx.stroke();
      }

    } else if (e < HS_BUILDUP + HS_JUMP) {
      // Phase 2: full-length streaks plus a bright white centre glow
      const t = (e - HS_BUILDUP) / HS_JUMP;

      const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, diag * 0.28);
      grd.addColorStop(0,    `rgba(255,255,255,${0.12 + t * 0.12})`);
      grd.addColorStop(0.15, `rgba(255,255,255,${0.04 + t * 0.06})`);
      grd.addColorStop(0.40, 'transparent');
      grd.addColorStop(1,    'transparent');
      ctx.fillStyle = grd;
      ctx.fillRect(0, 0, W, H);

      // Centre void grows while ray heads push past the screen edge
      const voidR   = diag * 0.05 * (1 + t * 4);
      const headMul = diag * (0.75 + t * 0.80);

      ctx.lineCap = 'square';
      for (const ray of HS_RAYS) {
        const cos = Math.cos(ray.angle), sin = Math.sin(ray.angle);
        const head = headMul * ray.speed;
        ctx.beginPath();
        ctx.moveTo(cx + cos * voidR, cy + sin * voidR);
        ctx.lineTo(cx + cos * head,  cy + sin * head);
        ctx.strokeStyle = `rgba(255,255,255,${ray.bri})`;
        ctx.lineWidth = ray.w * (1 + t * 0.35);
        ctx.stroke();
      }

    } else {
      // Phase 3: white flash dissolving back to black
      const t = (e - HS_BUILDUP - HS_JUMP) / HS_FLASH;
      const a = 1 - t;
      for (const ray of HS_RAYS) {
        const cos = Math.cos(ray.angle), sin = Math.sin(ray.angle);
        ctx.beginPath();
        ctx.moveTo(cx + cos * diag * 0.18, cy + sin * diag * 0.18);
        ctx.lineTo(cx + cos * diag * 2.2,  cy + sin * diag * 2.2);
        ctx.strokeStyle = `rgba(255,255,255,${ray.bri * a * 0.85})`;
        ctx.lineWidth = ray.w * 0.7;
        ctx.stroke();
      }
      ctx.fillStyle = `rgba(255,255,255,${a * 0.90})`;
      ctx.fillRect(0, 0, W, H);
    }
  }

  function draw(now) {
    rot += ROT_SPEED;
    frame++;

    if (hsActive) { drawHyperspace(now); requestAnimationFrame(draw); return; }

    ctx.clearRect(0, 0, W, H);
    const elapsed = now - t0;
    const warpT   = Math.min(easeOut(elapsed / WARP_MS), 1);
    const inWarp  = elapsed < WARP_MS;

    if (inWarp) {
      // First 3.2 seconds: stars streak inward, simulating warp arrival
      const prevT = Math.max(0, easeOut(Math.max(0, elapsed - 16) / WARP_MS));
      for (const s of stars) {
        const nx = s.fx - 0.5, ny = s.fy - 0.5;
        ctx.beginPath();
        ctx.moveTo(cx + nx * W * 2 * prevT, cy + ny * H * 2 * prevT);
        ctx.lineTo(cx + nx * W * 2 * warpT, cy + ny * H * 2 * warpT);
        ctx.strokeStyle = `rgba(${s.r},${s.g},${s.b},${s.bri * warpT * 0.9})`;
        ctx.lineWidth = s.size * 0.5;
        ctx.stroke();
      }
    } else {
      // Steady state: very slow rotation of nebulas + constellations + stars
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rot);
      ctx.translate(-cx, -cy);

      // Nebulas - each layer is a radial gradient drawn over the full canvas
      for (const nb of NEBULAS) {
        const nx = nb.fx * W, ny = nb.fy * H;
        const baseR = nb.fr * Math.min(W, H);
        for (const lyr of nb.layers) {
          const lx = nx + lyr.ox * baseR;
          const ly = ny + lyr.oy * baseR;
          const lr = lyr.rs * baseR;
          const grd = ctx.createRadialGradient(lx, ly, 0, lx, ly, lr);
          grd.addColorStop(0,    `rgba(${lyr.r},${lyr.g},${lyr.b},${lyr.a})`);
          grd.addColorStop(0.45, `rgba(${lyr.r},${lyr.g},${lyr.b},${+(lyr.a * 0.35).toFixed(3)})`);
          grd.addColorStop(1,    'transparent');
          ctx.fillStyle = grd;
          ctx.fillRect(0, 0, W, H);
        }
      }

      // Constellation lines - alpha follows the average twinkle of both endpoints
      ctx.lineWidth = 0.6;
      for (const [i, j] of constellations) {
        const si = stars[i], sj = stars[j];
        const twA = 0.5 + 0.5 * Math.sin(frame * si.ts + si.to);
        const twB = 0.5 + 0.5 * Math.sin(frame * sj.ts + sj.to);
        const alpha = (twA + twB) * 0.5 * 0.10;
        ctx.beginPath();
        ctx.moveTo(si.fx * W, si.fy * H);
        ctx.lineTo(sj.fx * W, sj.fy * H);
        ctx.strokeStyle = `rgba(180,210,255,${alpha})`;
        ctx.stroke();
      }

      // Stars - bright ones get a soft halo behind their core circle
      for (const s of stars) {
        const tw = 0.6 + 0.4 * Math.sin(frame * s.ts + s.to);
        const x = s.fx * W, y = s.fy * H;
        const alpha = s.bri * tw;
        if (s.size > 1.8) {
          ctx.beginPath();
          ctx.arc(x, y, s.size * 2.8, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${s.r},${s.g},${s.b},${alpha * 0.07})`;
          ctx.fill();
        }
        ctx.beginPath();
        ctx.arc(x, y, s.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${s.r},${s.g},${s.b},${alpha})`;
        ctx.fill();
      }

      ctx.restore();
    }

    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
})();
