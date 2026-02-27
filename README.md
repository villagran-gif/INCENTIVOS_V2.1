# INCENTIVOS APP_V2.1 (Zendesk Sell)

Backend en **Python + FastAPI** para calcular incentivos desde **Zendesk Sell** (`api.getbase.com`).

## Qué calcula

1) **Consolidado mensual por slot 1..6** (BAR1..BAR6)  
2) **Consolidado mensual por colaborador** (si usas Colaborador1/2/3):
   - Colaborador1 recibe: BAR1 + BAR4
   - Colaborador2 recibe: BAR2 + BAR5
   - Colaborador3 recibe: BAR3 + BAR6

## Fuente de verdad (Sell)

- Pipeline cirugía bariátricas: `1290779`
- Stages incluidos (por negocio):
  - `10693256` (CERRADO OPERADO)
  - `35531166` (CERRADO AGENDADO)

## BARs (lista con 2 valores, en pesos)

Cada campo `ComisionBARx` tiene dos opciones y **el monto en pesos es el mismo código**:

- BAR1: `1` o `8001`
- BAR2: `2` o `5002`
- BAR3: `3` o `5003`
- BAR4: `4` o `9004`
- BAR5: `5` o `6005`
- BAR6: `6` o `6006`

Si el campo viene vacío/no existe en `custom_fields`, se considera **missing** y se omite (equivale a 0).

## Scope del cálculo mensual

- Se consideran solo deals cuya **FECHA DE CIRUGÍA** (custom field `2622657`, key: `FECHA DE CIRUGÍA`) cae dentro del mes solicitado (`YYYY-MM`).
- Si a un deal le falta algún BAR, **se suman solamente los BAR que existan**.
- Si un BAR viene con valor inválido, se reporta en `deal_errors` y ese BAR se omite.

## Config

```bash
cp config/incentivos_config.example.json config/incentivos_config.json
```

> Nota: no necesitas definir montos fijos (`amount`) si usas “código = monto”.

## Quickstart (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edita .env y define SELL_ACCESS_TOKEN

uvicorn app.main:app --reload
```

API Docs: http://localhost:8000/docs

## Endpoints

- `GET /health`
- `GET /v1/config`
- `GET /v1/deals/{deal_id}` (auditoría por deal)
- `GET /v1/monthly/{YYYY-MM}` (cálculo mensual)

Ejemplo:

```bash
curl -s http://localhost:8000/v1/monthly/2026-02 | jq
```

## Nota de permisos / 403

Si desde un entorno (por ejemplo Codespaces) recibes `403 Forbidden`, suele ser por:
- restricciones de permisos del token/usuario,
- o seguridad/red (allowlist de IP, proxy corporativo, etc.).

En ese caso prueba correr el backend desde una red permitida o ajusta la política de seguridad en Zendesk Sell.

## Script CLI

```bash
python scripts/recalc_month.py 2026-02
```

## Deploy (Render)

Incluye `Dockerfile` y `render.yaml`.
Configura env var `SELL_ACCESS_TOKEN` y sube `config/incentivos_config.json`.
