#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import sys

from app.calculator import calc_month
from app.config import Settings, load_incentivos_config
from app.sell_client import SellClient


async def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python scripts/recalc_month.py YYYY-MM", file=sys.stderr)
        return 2

    year_month = sys.argv[1]
    try:
        y, m = year_month.split("-")
        year = int(y)
        month = int(m)
        if not (1 <= month <= 12):
            raise ValueError
    except Exception:
        print("Formato inválido. Usa YYYY-MM", file=sys.stderr)
        return 2

    settings = Settings()
    cfg = load_incentivos_config(settings.config_path)

    if not cfg.stage_ids:
        print("Config inválida: stage_ids vacío", file=sys.stderr)
        return 2

    async with SellClient(settings.sell_base_url, settings.sell_access_token, settings.timeout_s) as sell:
        deals_by_id = {}
        for sid in cfg.stage_ids:
            deals = await sell.list_deals_by_stage(int(sid), per_page=settings.per_page)
            for d in deals:
                did = d.get("id")
                if did is not None:
                    deals_by_id[int(did)] = d

    out = calc_month(cfg, list(deals_by_id.values()), year, month)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
