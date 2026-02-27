import 'dotenv/config';
import express from 'express';

import { loadConfig } from './config.js';
import { createSellClient } from './sell.js';
import { calcDeal } from './calc.js';
import { createMonthlyCache } from './monthlyCache.js';

const app = express();
app.use(express.json());
app.use(express.static('public'));

// Cache mensual + job cada N segundos (default: 10 minutos)
const monthlyCache = createMonthlyCache();
monthlyCache.start();

app.get('/health', (req, res) => {
  res.json({ ok: true, monthly_cache: monthlyCache.getStatus() });
});

// Ready: 200 sólo si ya hubo al menos 1 refresh exitoso
app.get('/ready', (req, res) => {
  const st = monthlyCache.getStatus();
  if (!st.last_refresh_at) return res.status(503).json({ ok: false, monthly_cache: st });
  return res.json({ ok: true, monthly_cache: st });
});

app.get('/api/config', (req, res) => {
  try {
    const cfg = loadConfig();
    res.json({
      sell_base_url: process.env.SELL_BASE_URL || 'https://api.getbase.com',
      pipeline_id: cfg.pipeline_id,
      stage_ids: cfg.stage_ids,
      fecha_cirugia_field_name: cfg.fecha_cirugia_field_name,
      collaborator_field_names: cfg.collaborator_field_names,
      bars: cfg.bars,
      timezone: cfg.timezone,
      notes: cfg.notes,
    });
  } catch (e) {
    res.status(500).json({ error: String(e?.message || e) });
  }
});

app.get('/api/deals/:dealId', async (req, res) => {
  const dealId = Number(req.params.dealId);
  if (!Number.isFinite(dealId)) return res.status(400).json({ error: 'dealId inválido' });

  let cfg;
  try {
    cfg = loadConfig();
  } catch (e) {
    return res.status(500).json({ error: String(e?.message || e) });
  }

  try {
    const sell = createSellClient();
    const deal = await sell.getDeal(dealId);
    if (!deal?.id) return res.status(404).json({ error: 'Deal no encontrado' });
    return res.json(calcDeal(cfg, deal));
  } catch (e) {
    const status = e?.response?.status;
    const url = e?.config?.url;
    return res.status(502).json({
      error: 'Error consultando Zendesk Sell',
      upstream_status: status || null,
      upstream_url: url || null,
      detail: e?.message || String(e),
    });
  }
});

app.get('/api/monthly/:yearMonth', async (req, res) => {
  const ym = String(req.params.yearMonth || '');

  try {
    const result = await monthlyCache.getMonth(ym);
    res.set('X-Cache', result.cache);
    if (result.generated_at) res.set('X-Generated-At', result.generated_at);
    return res.json(result.data);
  } catch (e) {
    if (e?.code === 'BAD_YM') return res.status(400).json({ error: e.message });

    const status = e?.response?.status;
    const url = e?.config?.url;
    return res.status(502).json({
      error: 'Error consultando Zendesk Sell',
      upstream_status: status || null,
      upstream_url: url || null,
      detail: e?.message || String(e),
    });
  }
});

// Root -> UI
app.get('/', (req, res) => res.sendFile('index.html', { root: 'public' }));

const port = Number(process.env.PORT || '8000');
app.listen(port, () => {
  console.log(`INCENTIVOS Node escuchando en puerto ${port}`);
});
