# INCENTIVOS APP_V2.1 (Zendesk Sell)

Backend en **Python + FastAPI** para calcular incentivos desde **Zendesk Sell** (api.getbase.com).

## Qué calcula

1) **Consolidado mensual por slot 1..6** (BAR1..BAR6)
2) **Consolidado mensual por colaborador** con regla:
   - Colaborador1 recibe: BAR1 + BAR4
   - Colaborador2 recibe: BAR2 + BAR5
   - Colaborador3 recibe: BAR3 + BAR6

## Fuente de verdad

- Pipeline cirugía bariátricas: `1290779`
- Stages incluidos (por negocio):
  - `10693256` (CERRADO OPERADO)
  - `35531166` (CERRADO AGENDADO)

## BARs (list con 2 valores en pesos)

Cada campo `ComisionBARx` tiene dos opciones (y **el monto en pesos es el mismo código**):
- **min**: 1..6 (monto = 1..6 pesos)
- **max**: 8001 / 5002 / 5003 / 9004 / 6005 / 6006 (monto = ese mismo número)

Si el campo viene vacío/no existe en `custom_fields`, se considera **missing** y se omite.

## Config

Copia el ejemplo (no necesitas definir montos si usas "código = monto"):

```bash
cp config/incentivos_config.example.json config/incentivos_config.json
```

## Quickstart (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edita .env (SELL_ACCESS_TOKEN)

uvicorn app.main:app --reload
```

API Docs: http://localhost:8000/docs

## Endpoints

- `GET /health`
- `GET /v1/config`
- `GET /v1/deals/{deal_id}` (auditoría por deal)
- `GET /v1/monthly/{YYYY-MM}` (cálculo mensual con filtro por FECHA DE CIRUGÍA)

Ejemplo:

```bash
curl -s http://localhost:8000/v1/monthly/2026-02 | jq
```

## Reglas de scope y auditoría

- **Scope**: solo se consideran deals cuya **FECHA DE CIRUGÍA (custom field 2622657)** cae dentro del mes solicitado.
- Si a un deal le falta algún BAR, **se suman solamente los BAR que existan** (los faltantes se omiten).
- Si un BAR viene con valor inválido (no coincide con min/max), se reporta en `deal_errors` y ese BAR se omite.

## Rendimiento

Para reducir el volumen de datos, el endpoint mensual usa **Search API v3** (POST `/v3/deals/search`) filtrando por:
- `stage_id in [10693256, 35531166]`
- rango de fecha sobre el custom field 2622657

## Script CLI

```bash
python scripts/recalc_month.py 2026-02
```

## Deploy (Render)

Incluye `Dockerfile` y `render.yaml`.
Configura env var `SELL_ACCESS_TOKEN` y sube `config/incentivos_config.json`.
