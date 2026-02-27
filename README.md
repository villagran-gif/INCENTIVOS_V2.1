# INCENTIVOS V2.1 (Node Web Service + Render)

Este proyecto es una versión **Node.js** (Express) para desplegar en **Render Web Service**, pensada para evitar bloqueos tipo 403 que a veces pasan con ciertas librerías Python.

## Qué hace

- Consulta Zendesk Sell (api.getbase.com)
- Calcula consolidado mensual por BAR1..BAR6 (monto = código)
- Si falta un BAR en un deal, **se omite ese BAR** (no rompe el deal)
- Filtra por mes usando `FECHA DE CIRUGÍA` (key: `"FECHA DE CIRUGÍA"`) dentro del mes solicitado
- Usa los stages:
  - 10693256 (CERRADO OPERADO)
  - 35531166 (CERRADO AGENDADO)

## Endpoints

- `GET /health`
- `GET /api/config`
- `GET /api/deals/:dealId`
- `GET /api/monthly/YYYY-MM`

UI:
- `GET /` (página simple para probar)

## Config

Copia el ejemplo:

```bash
cp .env.example .env
cp config/incentivos_config.example.json config/incentivos_config.json
```

Edita `.env` y define:

- `SELL_ACCESS_TOKEN=...`

## Local

```bash
npm install
npm run dev
```

Abre:
- http://127.0.0.1:8000

## Render (pasos)

1) New → Web Service → conecta repo
2) Runtime: Node
3) Build Command: `npm install`
4) Start Command: `npm start`
5) Env Vars:
   - `SELL_ACCESS_TOKEN` (Secret)
   - `SELL_BASE_URL=https://api.getbase.com`
   - `INCENTIVOS_CONFIG=config/incentivos_config.json`
   - `SELL_PER_PAGE=100`
   - `SELL_TIMEOUT_S=30`
   - `PORT=8000`

Health Check Path: `/health`
