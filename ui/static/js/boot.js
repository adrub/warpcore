// Boot overlay sequence: shown once per session, replayable via PF3 / "Boot Log".
// Animates progress bars for several fake subsystems then triggers the hyperspace
// warp on the canvas and reveals the main UI. Depends on window.triggerHyperspace
// from space.js.

(function () {
  const BAR    = 24;     // characters per progress bar
  const BAR_MS = 520;    // total fill time for a bar

  function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

  async function run() {
    const overlay = document.getElementById('boot-overlay');
    const linesEl = document.getElementById('boot-lines');
    const DRIVERS = parseInt(overlay.dataset.drivers, 10) || 0;

    // Remove the pre-paint hide class so the overlay actually shows during replay
    document.documentElement.classList.remove('booted');

    linesEl.innerHTML = '';
    overlay.classList.remove('fade-out');
    overlay.style.display = 'flex';
    overlay.style.opacity  = '1';

    async function section(title) {
      await wait(420);
      const d = document.createElement('div');
      d.className = 'boot-section'; d.textContent = '[ ' + title + ' ]';
      linesEl.appendChild(d);
      await wait(200);
    }

    // Animated progress bar that fills char-by-char then stamps a status at the end
    async function bar(label, status, cls) {
      const row = document.createElement('div'); row.className = 'boot-row';
      const lbl = document.createElement('span');
      lbl.className = 'boot-label'; lbl.textContent = label;
      const b = document.createElement('span');
      b.className = 'boot-bar boot-bar-empty'; b.textContent = '░'.repeat(BAR);
      row.append(lbl, b); linesEl.appendChild(row);
      for (let i = 1; i <= BAR; i++) {
        await wait(BAR_MS / BAR);
        b.className = 'boot-bar boot-bar-fill';
        b.textContent = '█'.repeat(i) + '░'.repeat(BAR - i);
      }
      const st = document.createElement('span');
      st.className = 'boot-status-' + cls;
      st.textContent = '  ' + status;
      row.appendChild(st);
      await wait(95);
    }

    function line(text, cls) {
      const d = document.createElement('div');
      d.className = cls || ''; d.textContent = text;
      linesEl.appendChild(d);
    }

    await wait(320);

    await section('HARDWARE DIAGNOSTICS');
    await bar('CPU CORES        ', '8 CORES',       'ok');
    await bar('SYSTEM MEMORY    ', '16.0 GB',       'ok');
    await bar('DISPLAY OUTPUT   ', '1920×1080',     'ok');
    await bar('STORAGE ARRAY    ', 'NOMINAL',       'ok');

    await section('NETWORK LAYER');
    await bar('LOCAL INTERFACE  ', 'ACTIVE',        'ok');
    await bar('TORCS HOST LINK  ', 'LOCALHOST',     'ok');
    await bar('TELEMETRY SOCKET ', 'UDP:9999',      'ok');
    await bar('SCR PROTOCOL     ', 'v1.3 READY',   'ok');

    await section('AI SUBSYSTEMS');
    await bar('IBM GRANITE LINK ', 'ESTABLISHED',   'ok');
    await bar('TELEMETRY ARRAY  ', 'ONLINE',        'ok');
    await bar('SENSOR CHANNELS  ', '22 ACTIVE',    'ok');
    await bar('DRIVER REGISTRY  ',
      DRIVERS + (DRIVERS === 1 ? ' DRIVER' : ' DRIVERS'),
      DRIVERS > 0 ? 'ok' : 'warn');

    await section('RACE SYSTEMS');
    await bar('PHYSICS ENGINE   ', 'TORCS 1.3.7',  'ok');
    await bar('TRACK DATABASE   ', 'CORKSCREW',    'ok');
    await bar('COLLISION MODEL  ', 'ACTIVE',        'ok');
    await bar('RACE ORCHESTRATOR', 'READY',         'ok');

    await section('MISSION CONTROL');
    await bar('LIVE TELEMETRY   ', 'ONLINE',        'ok');
    await bar('RACE HISTORY     ', 'RESTORED',      'ok');
    await bar('PROFILE MANAGER  ', 'LOADED',        'ok');
    await bar('COMMAND INTERFACE', 'ONLINE',        'ok');

    await wait(450);
    line('ALL SYSTEMS NOMINAL', 'boot-final');
    await wait(600);
    line('INITIATING MISSION CONTROL...', 'boot-init');
    await wait(900);

    // Pre-hide UI so there's no visible flash between overlay lifting and hyperspace starting
    document.body.classList.add('warp-active');
    overlay.classList.add('fade-out');
    await wait(750);
    overlay.style.display = 'none';

    // Hyperspace plays on the canvas, then the UI fades back in
    if (typeof window.triggerHyperspace === 'function') {
      await new Promise(resolve => window.triggerHyperspace(resolve));
    }
    document.body.classList.remove('warp-active');
  }

  // Only auto-play on the first load per browser session - subsequent reloads skip it
  if (!sessionStorage.getItem('wc-booted')) {
    sessionStorage.setItem('wc-booted', '1');
    run();
  } else {
    document.getElementById('boot-overlay').style.display = 'none';
  }

  // Exposed so PF3 / the "Boot Log" button can replay the sequence
  window.replayBoot = run;
})();
