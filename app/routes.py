from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .calculator import calc_deal, calc_month
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
        "pipeline_id": cfg.pipeline_id,
        "stage_ids": cfg.stage_ids,
        "fecha_cirugia_field_id": cfg.fecha_cirugia_field_id,
        "collaborator_field_ids": cfg.collaborator_field_ids,
        "bars": {
            k: {
                "field_id": v.field_id,
                "min": v.min,
                "max": v.max,
                "max_values": v.max_values,
                "amount": v.amount,
            }
            for k, v in cfg.bars.items()
        },
        "extras_enabled": cfg.extras_enabled,
        "timezone": cfg.timezone,
        "notes": "Monthly endpoint uses v2 deals by stage_id and filters by FECHA DE CIRUGÍA locally.",
    }


@router.get("/v1/deals/{deal_id}")
async def incentives_for_deal(deal_id: int):
    settings = Settings()
    cfg = load_incentivos_config(settings.config_path)

    async with SellClient(settings.sell_base_url, settings.sell_access_token, settings.timeout_s) as sell:
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

    async with SellClient(settings.sell_base_url, settings.sell_access_token, settings.timeout_s) as sell:
        deals_by_id: dict[int, dict] = {}
        for sid in cfg.stage_ids:
            try:
                deals = await sell.list_deals_by_stage(int(sid), per_page=settings.per_page)
            except Exception as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"Error consultando deals stage_id={sid}: {type(e).__name__}: {e}",
                )
            for d in deals:
                did = d.get("id")
                if did is not None:
                    deals_by_id[int(did)] = d

    return calc_month(cfg, list(deals_by_id.values()), year, month)
