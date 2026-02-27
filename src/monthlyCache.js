// src/monthlyCache.js
// Cache en memoria + refresco periódico para evitar recalcular /api/monthly en cada request.

import { loadConfig } from './config.js';
import { createSellClient } from './sell.js';
import { calcMonth } from './calc.js';

function ymFromDateUTC(d) {
  const y = d.getUTCFullYear();
  const m = d.getUTCMonth() + 1;
  return `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}`;
}

function parseYmStrict(ym) {
  const m = String(ym || '').match(/^(\d{4})-(\d{2})$/);
  if (!m) return null;
  const year = Number(m[1]);
  const month = Number(m[2]);
  if (!Number.isFinite(year) || !Number.isFinite(month) || month < 1 || month > 12) return null;
  return { year, month };
}

export function createMonthlyCache() {
  const refreshEveryS = Number(process.env.MONTHLY_REFRESH_EVERY_S || '600'); // 10 min
  const refreshEveryMs = Math.max(60, refreshEveryS) * 1000;

  const prefetchMonths = Math.max(1, Number(process.env.MONTHLY_PREFETCH_MONTHS || '2')); // mes actual + anterior
  const maxTrackedMonths = Math.max(1, Number(process.env.MONTHLY_CACHE_MAX_MONTHS || '6'));

  const maxAgeS = Number(process.env.MONTHLY_CACHE_MAX_AGE_S || String(refreshEveryS * 2));
  const maxAgeMs = Math.max(60, maxAgeS) * 1000;

  const perPage = Math.min(100, Number(process.env.SELL_PER_PAGE || '100'));

  const trackedMonths = new Set();
  const cache = new Map(); // ym -> { data, generatedAt }
  let lastRefreshAt = null;
  let lastRefreshError = null;
  let refreshingPromise = null;

  function shrinkTracked() {
    const arr = Array.from(trackedMonths).sort().reverse(); // YYYY-MM ordena lexicográficamente
    for (let i = maxTrackedMonths; i < arr.length; i += 1) trackedMonths.delete(arr[i]);
  }

  function seedPrefetchMonths() {
    const now = new Date();
    for (let i = 0; i < prefetchMonths; i += 1) {
      const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - i, 1));
      trackedMonths.add(ymFromDateUTC(d));
    }
    shrinkTracked();
  }

  async function fetchDealsAllStages(cfg, sell) {
    const dealsById = new Map();
    for (const stageId of cfg.stage_ids || []) {
      const list = await sell.listDealsByStage(stageId, perPage);
      for (const d of list) {
        if (d?.id != null) dealsById.set(Number(d.id), d);
      }
    }
    return Array.from(dealsById.values());
  }

  async function refreshOnce() {
    if (refreshingPromise) return refreshingPromise;

    refreshingPromise = (async () => {
      try {
        lastRefreshError = null;

        const cfg = loadConfig();
        const sell = createSellClient();

        const deals = await fetchDealsAllStages(cfg, sell);

        const months = Array.from(trackedMonths).sort();
        const nowIso = new Date().toISOString();

        for (const ym of months) {
          const p = parseYmStrict(ym);
          if (!p) continue;
          const out = calcMonth(cfg, deals, p.year, p.month);
          cache.set(ym, { data: out, generatedAt: nowIso });
        }

        lastRefreshAt = nowIso;
      } catch (e) {
        lastRefreshError = e?.message || String(e);
        throw e;
      } finally {
        refreshingPromise = null;
      }
    })();

    return refreshingPromise;
  }

  function getStatus() {
    return {
      refresh_every_s: refreshEveryS,
      cache_max_age_s: maxAgeS,
      tracked_months: Array.from(trackedMonths).sort(),
      cached_months: Array.from(cache.keys()).sort(),
      last_refresh_at: lastRefreshAt,
      last_refresh_error: lastRefreshError,
      refreshing: Boolean(refreshingPromise),
    };
  }

  async function getMonth(ym) {
    const p = parseYmStrict(ym);
    if (!p) {
      const err = new Error('Formato inválido. Usa YYYY-MM');
      err.code = 'BAD_YM';
      throw err;
    }

    trackedMonths.add(ym);
    shrinkTracked();

    const existing = cache.get(ym);
    const isFresh =
      existing?.generatedAt && Date.now() - Date.parse(existing.generatedAt) <= maxAgeMs;

    if (existing && isFresh) {
      return { data: existing.data, cache: 'HIT', generated_at: existing.generatedAt };
    }

    try {
      await refreshOnce();
    } catch (e) {
      if (existing?.data) {
        return {
          data: existing.data,
          cache: 'STALE',
          generated_at: existing.generatedAt,
          warning: 'Upstream error en refresh; devolviendo cache previa',
        };
      }
      throw e;
    }

    const updated = cache.get(ym);
    if (updated?.data) {
      return {
        data: updated.data,
        cache: existing ? 'REFRESHED' : 'MISS',
        generated_at: updated.generatedAt,
      };
    }

    return { data: { month: ym, error: 'No data' }, cache: 'EMPTY', generated_at: null };
  }

  function start() {
    seedPrefetchMonths();

    // Refresh inmediato al arrancar (sin bloquear el server)
    refreshOnce().catch(() => {});

    const t = setInterval(() => {
      refreshOnce().catch(() => {});
    }, refreshEveryMs);

    // No mantener vivo el proceso si Render lo mata
    if (typeof t.unref === 'function') t.unref();
  }

  return {
    start,
    getMonth,
    getStatus,
    parseYmStrict,
    refreshOnce,
  };
}
