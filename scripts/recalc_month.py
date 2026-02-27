#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import sys
from datetime import timedelta

from app.calculator import calc_month, month_bounds
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

    start, end_excl = month_bounds(year, month)
    end_inclusive = end_excl - timedelta(days=1)

    async with SellClient(
        settings.sell_base_url,
        settings.sell_access_token,
        settings.timeout_s,
        search_base_url=settings.sell_search_base_url,
    ) as sell:
        mapping = await sell.get_deal_custom_fields_mapping()
        id_to_name = {str(m.get("id")): m.get("name") for m in mapping if m.get("id") and m.get("name")}
        id_to_search = {str(m.get("id")): m.get("search_api_id") for m in mapping if m.get("id") and m.get("search_api_id")}

        fecha_search = id_to_search.get("2622657")
        if not fecha_search:
            raise RuntimeError("No pude resolver search_api_id de custom field 2622657 (FECHA DE CIRUGÍA)")

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
                {"filter": {"attribute": {"name": "stage_id"}, "parameter": {"any": cfg.stage_ids}}},
                {
                    "filter": {
                        "attribute": {"name": fecha_search},
                        "parameter": {"range": {"gte": start.isoformat(), "lte": end_inclusive.isoformat()}},
                    }
                },
            ]
        }

        deals = await sell.search_deals(filter_obj=filter_obj, projection=projection, per_page=200)

        normalized = []
        for d in deals:
            cf = d.get("custom_fields") or {}
            merged = dict(cf)
            for cid, name in id_to_name.items():
                if cid in cf and name not in merged:
                    merged[name] = cf[cid]
            d2 = dict(d)
            d2["custom_fields"] = merged
            normalized.append(d2)

    out = calc_month(cfg, normalized, year, month)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
