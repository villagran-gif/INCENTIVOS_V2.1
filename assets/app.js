/* global ZAFClient */
const client = ZAFClient.init();
const SERVICE = 'https://incentivos-v2-1-1.onrender.com';

function ymNow() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
}

function setOut(obj) {
  document.getElementById('out').textContent = JSON.stringify(obj, null, 2);
}

function toCsv(summary) {
  const lines = [];
  lines.push(['persona','base','extra','total','deals'].join(','));
  const entries = Object.entries(summary.totals_by_person || {})
    .sort((a,b)=>a[0].localeCompare(b[0]));
  for (const [p,v] of entries) lines.push([p, v.base||0, v.extra||0, v.total||0, v.deals||0].join(','));
  return lines.join('\n');
}

function downloadFile(name, text) {
  const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

let lastSummary = null;

async function run() {
  const ym = document.getElementById('month').value || ymNow();
  document.getElementById('download').disabled = true;
  setOut({ status: 'consultando...', month: ym });

  const resp = await fetch(`${SERVICE}/api/monthly/${encodeURIComponent(ym)}`);
  const cache = resp.headers.get('x-cache') || '—';
  document.getElementById('kpiCache').textContent = cache;

  const data = await resp.json();
  lastSummary = data;

  document.getElementById('kpiDeals').textContent = String(data.included_deals ?? '—');
  document.getElementById('kpiProcessed').textContent = String(data.processed_deals ?? '—');

  setOut(data);
  document.getElementById('download').disabled = false;
}

document.getElementById('month').value = ymNow();
document.getElementById('run').addEventListener('click', () => run().catch(e => setOut({error:String(e)})));
document.getElementById('download').addEventListener('click', () => {
  if (!lastSummary) return;
  downloadFile(`incentivos_${lastSummary.month}.csv`, toCsv(lastSummary));
});
