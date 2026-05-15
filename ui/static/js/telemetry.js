// Polls /telemetry and /history every second/five seconds and re-renders the tables.
// Depends on fmt, fmtTime, carColor, colorMap from utils.js.

async function refreshTelemetry() {
  try {
    const data = await fetch('/telemetry').then(r => r.json());
    const entries = Object.values(data);
    if (!entries.length) return;
    // Sort by race position so leader is on top
    entries.sort((a, b) => (a.race_pos || 99) - (b.race_pos || 99));
    document.getElementById('tel-body').innerHTML = entries.map(e => {
      const col = carColor(e.name);
      return `<tr>
        <td class="td-name" style="border-left:3px solid ${col};padding-left:9px">${e.name}</td>
        <td>${fmt(e.speed, 1)}</td>
        <td>${e.gear ?? '—'}</td>
        <td>${fmt(e.rpm, 0)}</td>
        <td>${fmtTime(e.lap_time)}</td>
        <td class="td-best">${e.best_lap ? fmtTime(e.best_lap) : '—'}</td>
        <td>${e.laps ?? 0}</td>
        <td>${e.race_pos || '—'}</td>
        <td>${fmt(e.damage, 0)}</td>
      </tr>`;
    }).join('');
  } catch (_) {}
}

async function refreshHistory() {
  try {
    const data = await fetch('/history').then(r => r.json());
    if (!data.length) return;
    // Newest lap first - reverse a copy so we do not mutate the response
    document.getElementById('history-body').innerHTML = [...data].reverse().map(e => {
      const col = colorMap[e.name] || '#0f62fe';
      return `<tr>
        <td class="td-name" style="border-left:3px solid ${col};padding-left:9px">${e.name}</td>
        <td>${e.lap}</td>
        <td class="td-best">${fmtTime(e.lap_time)}</td>
        <td style="color:var(--muted);font-size:11px">${(e.timestamp || '').replace('T', ' ')}</td>
      </tr>`;
    }).join('');
  } catch (_) {}
}

setInterval(refreshTelemetry, 1000);
setInterval(refreshHistory, 5000);
refreshTelemetry();
refreshHistory();
