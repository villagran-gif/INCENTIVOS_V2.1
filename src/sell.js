import axios from 'axios';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryableStatus(status) {
  return status === 429 || (status >= 500 && status <= 599);
}

export function createSellClient() {
  const token = process.env.SELL_ACCESS_TOKEN;
  if (!token) throw new Error('SELL_ACCESS_TOKEN requerido');

  const baseURL = (process.env.SELL_BASE_URL || 'https://api.getbase.com').replace(/\/$/, '');
  const timeout = Number(process.env.SELL_TIMEOUT_S || '30') * 1000;

  const http = axios.create({
    baseURL,
    timeout,
    // Importante: forzar HTTP/1.1 ayuda con algunos WAF
    transitional: { clarifyTimeoutError: true },
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
      // User-Agent "browser-like" para reducir falsos positivos de WAF
      'User-Agent': 'Mozilla/5.0 (compatible; IncentivosBot/1.0; +https://incentivos-v2-1.onrender.com)',
      'Accept-Encoding': 'gzip, deflate, br',
    },
  });

  async function get(path, params) {
    const maxAttempts = 6;
    let attempt = 0;
    while (true) {
      attempt += 1;
      try {
        const res = await http.get(path, { params });
        return res.data;
      } catch (err) {
        const status = err?.response?.status;
        const retryable = status ? isRetryableStatus(status) : true;
        if (!retryable || attempt >= maxAttempts) throw err;
        const backoff = Math.min(8000, 400 * 2 ** (attempt - 1));
        await sleep(backoff);
      }
    }
  }

  return {
    baseURL,
    async getDeal(dealId) {
      const payload = await get(`/v2/deals/${dealId}`);
      return payload?.data || {};
    },
    async listDealsByStage(stageId, perPage = 100) {
      const out = [];
      let page = 1;
      while (true) {
        const payload = await get('/v2/deals', { stage_id: stageId, per_page: perPage, page });
        const items = payload?.items || [];
        for (const it of items) out.push(it?.data || {});
        if (items.length < perPage) break;
        page += 1;
      }
      return out;
    },
  };
}
