from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, HTTPException

from .calculator import calc_deal, calc_month, month_bounds
from .config import Settings, load_incentivos_config
from .sell_client import SellClient

router = APIRouter()


@router.get("/health")
async def health():
    return {"ok": True}


@router.get("/v1/config")
async def get_config():
    settings = Settings()
    cfg = load_incentivos_config(settings.config_path)
    return {
        "sell_base_url": settings.sell_base_url,
        "sell_search_base_url": settings.sell_search_base_url,
        "pipeline_id": cfg.pipeline_id,
        "stage_ids": cfg.stage_ids,
        "fecha_cirugia_field_id": cfg.fecha_cirugia_field_id,
        "collaborator_field_ids": cfg.collaborator_field_ids,
        "bars": {
            k: {"field_id": v.field_id, "min": v.min, "max": v.max, "max_values": v.max_values, "amount": v.amount}
            for k, v in cfg.bars.items()
        },
        "extras_enabled": cfg.extras_enabled,
        "timezone": cfg.timezone,
    }


@router.get("/v1/deals/{deal_id}")
async def incentives_for_deal(deal_id: int):
    settings = Settings()
    cfg = load_incentivos_config(settings.config_path)

    async with SellClient(
        settings.sell_base_url,
        settings.sell_access_token,
        settings.timeout_s,
        search_base_url=settings.sell_search_base_url,
    ) as sell:
        try:
            deal = await sell.get_deal(deal_id)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Error consultando Sell: {type(e).__name__}: {e}")

    if not deal or not deal.get("id"):
        raise HTTPException(status_code=404, detail="Deal no encontrado")

    return calc_deal(cfg, deal)


@router.get("/v1/monthly/{year_month}")
async def incentives_for_month(year_month: str):
    # year_month: YYYY-MM
    try:
        year_s, month_s = year_month.split("-")
        year = int(year_s)
        month = int(month_s)
        if not (1 <= month <= 12):
            raise ValueError
    except Exception:
        raise HTTPException(status_code=400, detail="Formato inválido. Usa YYYY-MM")

    settings = Settings()
    cfg = load_incentivos_config(settings.config_path)

    if not cfg.stage_ids:
        raise HTTPException(status_code=400, detail="Config inválida: stage_ids vacío")

    # Scope eficiente: Search API (v3) filtrando por stage_id y por rango de FECHA DE CIRUGÍA
    # para no descargar miles de deals innecesariamente.
    start, end_excl = month_bounds(year, month)
    end_inclusive = end_excl - timedelta(days=1)

    async with SellClient(
        settings.sell_base_url,
        settings.sell_access_token,
        settings.timeout_s,
        search_base_url=settings.sell_search_base_url,
    ) as sell:
        try:
            mapping = await sell.get_deal_custom_fields_mapping()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Error consultando custom_fields mapping: {type(e).__name__}: {e}")

        id_to_name = {str(m.get("id")): m.get("name") for m in mapping if m.get("id") and m.get("name")}
        id_to_search = {str(m.get("id")): m.get("search_api_id") for m in mapping if m.get("id") and m.get("search_api_id")}
        # Fecha cirugía: campo 2622657
        fecha_search = id_to_search.get("2622657")
        if not fecha_search:
            raise HTTPException(status_code=400, detail="No pude resolver search_api_id de custom field 2622657 (FECHA DE CIRUGÍA)")

        # Proyección: id + stage_id + custom_fields requeridos
        needed_cf_ids = [
            "2622657",
            "2705361",
            "2705362",
            "2705363",
            "2705163",
            "2705188",
            "2705189",
            "2705365",
            "2712466",
            "2712467",
        ]
        projection = ["id", "stage_id"]
        for cid in needed_cf_ids:
            sa = id_to_search.get(cid)
            if sa:
                projection.append(sa)

        filter_obj = {
            "and": [
                {
                    "filter": {
                        "attribute": {"name": "stage_id"},
                        "parameter": {"any": cfg.stage_ids},
                    }
                },
                {
                    "filter": {
                        "attribute": {"name": fecha_search},
                        "parameter": {"range": {"gte": start.isoformat(), "lte": end_inclusive.isoformat()}},
                    }
                },
            ]
        }

        try:
            deals = await sell.search_deals(filter_obj=filter_obj, projection=projection, per_page=200)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Error Search API deals: {type(e).__name__}: {e}")

        # Search API devuelve un objeto plano con keys = projection.
        # Construimos un "deal" compatible con calc_deal(): {id, stage_id, custom_fields:{...}}
        normalized = []
        for row in deals:
            cf = {}
            for cid in needed_cf_ids:
                sa = id_to_search.get(cid)
                if not sa:
                    continue
                if sa not in row:
                    continue
                val = row.get(sa)
                if val is None:
                    continue
                # key por ID
                cf[str(cid)] = val
                # key por nombre
                name = id_to_name.get(str(cid))
                if name:
                    cf[name] = val

            normalized.append(
                {
                    "id": row.get("id"),
                    "stage_id": row.get("stage_id"),
                    "custom_fields": cf,
                }
            )

    return calc_month(cfg, normalized, year, month)
