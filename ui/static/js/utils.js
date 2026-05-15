// Small helpers shared across the page: number formatting, slider sync,
// profile deletion, per-car colour assignment, and the terminal clock.

function fmt(v, dp) { return typeof v === 'number' ? v.toFixed(dp) : '—'; }

function fmtTime(s) {
  if (!s || typeof s !== 'number') return '—';
  const m = Math.floor(s / 60);
  const sec = (s % 60).toFixed(2).padStart(5, '0');
  return m > 0 ? `${m}:${sec}` : `${sec}s`;
}

// Called from the slider's oninput - keeps the numeric label in sync with the thumb
function updateSlider(el) {
  document.getElementById(el.dataset.valId).textContent =
    parseFloat(el.value).toFixed(parseInt(el.dataset.dp));
}

// Profile delete is a GET-style action so we synthesise a POST form and submit it
function deleteProfile(btn) {
  const sel = document.getElementById('prof-sel-' + btn.dataset.idx);
  if (!sel) return;
  const f = document.createElement('form');
  f.method = 'post';
  f.action = '/profile/delete/' + btn.dataset.dtype + '/' + encodeURIComponent(sel.value);
  document.body.appendChild(f);
  f.submit();
}

// Colour palette assigned to cars on first sight - stable across telemetry refreshes
const CAR_COLORS = ['#0f62fe','#00b4d8','#24a148','#f1c21b','#8a3ffc','#fa4d56','#08bdba','#ff7eb6','#d2a106','#007d79'];
const colorMap = {};
let colorIdx = 0;
function carColor(name) {
  if (!colorMap[name]) colorMap[name] = CAR_COLORS[colorIdx++ % CAR_COLORS.length];
  return colorMap[name];
}

// Live clock in the top terminal-ID bar
(function () {
  const el = document.getElementById('tid-time');
  function tick() {
    if (!el) return;
    const n = new Date();
    const t = n.toTimeString().slice(0, 8);
    const d = n.toLocaleDateString('en-GB');
    el.textContent = t + '  ' + d;
  }
  tick(); setInterval(tick, 1000);
})();
