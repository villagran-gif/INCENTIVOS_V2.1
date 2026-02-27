import fs from 'node:fs';
import path from 'node:path';

let cached = null;
let cachedAtMs = 0;
let cachedMtimeMs = 0;
let cachedPath = null;

export function loadConfig() {
  const configPath = process.env.INCENTIVOS_CONFIG || 'config/incentivos_config.json';
  const abs = path.isAbsolute(configPath) ? configPath : path.join(process.cwd(), configPath);

  if (!fs.existsSync(abs)) {
    throw new Error(
      `No existe ${abs}. Copia config/incentivos_config.example.json a ${abs} y ajusta si corresponde.`
    );
  }

  const cacheS = Number(process.env.CONFIG_CACHE_S || '30');
  const st = fs.statSync(abs);
  const now = Date.now();

  const canUseCache =
    cached &&
    cachedPath === abs &&
    st.mtimeMs === cachedMtimeMs &&
    cacheS > 0 &&
    now - cachedAtMs <= cacheS * 1000;

  if (canUseCache) return cached;

  const raw = fs.readFileSync(abs, 'utf-8');
  const parsed = JSON.parse(raw);

  cached = parsed;
  cachedAtMs = now;
  cachedMtimeMs = st.mtimeMs;
  cachedPath = abs;

  return parsed;
}
