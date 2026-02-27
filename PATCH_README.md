# Patch: Cache mensual + refresco cada 10 minutos (INCENTIVOS V2.1)

Este ZIP contiene **sólo los archivos cambiados / nuevos** para que puedas crear un branch, copiarlos encima del repo y hacer merge.

## Archivos incluidos
- `src/monthlyCache.js` (NUEVO) cache en memoria + refresh periódico
- `src/server.js` (MODIFICADO) usa el cache y agrega `/ready`
- `src/config.js` (MODIFICADO) cachea lectura del JSON de config (30s)
- `render.yaml` (MODIFICADO) agrega `healthCheckPath` y env vars del refresh

## Cómo aplicarlo (local)
1) Crea un branch:
   ```bash
   git checkout -b feature/monthly-cache-10min
   ```
2) Descomprime este ZIP en la raíz del repo (sobrescribe archivos):
   ```bash
   unzip incentivos_patch_monthly_cache_10min.zip -d .
   ```
3) Ejecuta y prueba local:
   ```bash
   npm install
   npm start
   # Health
   curl http://localhost:8000/health
   # Ready (puede dar 503 hasta que termine el primer refresh)
   curl -i http://localhost:8000/ready
   # Monthly
   curl -i http://localhost:8000/api/monthly/2026-02
   ```
4) Commit + push:
   ```bash
   git add -A
   git commit -m "Add monthly in-memory cache + 10min refresh"
   git push origin feature/monthly-cache-10min
   ```
5) Abre PR y merge.

## Notas
- El refresh inicial corre al arrancar y **no bloquea** el server. `/ready` devuelve 503 hasta que haya un refresh exitoso.
- `/api/monthly/:YYYY-MM` responde desde cache (headers `X-Cache` y `X-Generated-At`).
- Este enfoque es intencionalmente simple para salir urgente. Luego optimizamos (persistencia, jitter/retry-after, rate limit, etc.).
