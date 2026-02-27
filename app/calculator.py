from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .config import IncentivosConfig
from .utils import normalize_int, normalize_list_value, parse_iso_date


@dataclass
class BarResult:
    slot: int
    codigo: Optional[int]
    paga: Optional[bool]
    monto: Optional[int]
    error: Optional[str]
    missing: bool = False


def _get_cf(custom_fields: Dict[str, Any], key: str) -> Any:
    # En tu cuenta: keys suelen ser nombres. Igual soportamos IDs por si acaso.
    return custom_fields.get(key) or custom_fields.get(str(key))


def calc_bar(slot: int, cfg: IncentivosConfig, custom_fields: Dict[str, Any]) -> BarResult:
    r = cfg.bars[str(slot)]
    raw = _get_cf(custom_fields, r.field_id)

    raw_id, raw_label = normalize_list_value(raw)
    raw_int = normalize_int(raw_id or raw_label)

    if raw_int is None:
        # Regla solicitada: si falta BAR en un deal, no se "cancela" el deal.
        # Simplemente se omite este BAR del conteo/suma.
        return BarResult(slot=slot, codigo=None, paga=None, monto=None, error=None, missing=True)

    if slot in (4, 5, 6) and not cfg.extras_enabled:
        # Extras apagados => no cuentan para monto
        return BarResult(slot=slot, codigo=raw_int, paga=False, monto=0, error=None)

    # Regla solicitada (última): los montos reales son el MISMO código en pesos.
    # - Si viene el código mínimo (ej 1,2,3,4,5,6) => monto = ese código (pesos)
    # - Si viene el código máximo (ej 8001,5002,...) => monto = ese código (pesos)
    # - Si el campo no viene / null => missing (se omite del conteo y suma)
    max_values = r.max_values or [r.max]
    if raw_int in max_values:
        return BarResult(slot=slot, codigo=raw_int, paga=True, monto=raw_int, error=None)

    if raw_int == r.min:
        return BarResult(slot=slot, codigo=raw_int, paga=False, monto=raw_int, error=None)

    return BarResult(
        slot=slot,
        codigo=raw_int,
        paga=None,
        monto=None,
        error=f"Valor inválido (esperado {r.min} o {r.max})",
    )


def get_collaborators(cfg: IncentivosConfig, custom_fields: Dict[str, Any]) -> Dict[str, Dict[str, Optional[str]]]:
    out: Dict[str, Dict[str, Optional[str]]] = {}
    for role, fid in cfg.collaborator_field_ids.items():
        raw = _get_cf(custom_fields, fid)
        oid, label = normalize_list_value(raw)
        out[role] = {"id": oid, "label": label or oid}
    return out


def calc_deal(cfg: IncentivosConfig, deal: Dict[str, Any]) -> Dict[str, Any]:
    cf = deal.get("custom_fields") or {}

    fecha_cirugia = parse_iso_date(_get_cf(cf, cfg.fecha_cirugia_field_id))
    errors: List[str] = []
    if fecha_cirugia is None:
        errors.append(f"Falta fecha_cirugia (campo '{cfg.fecha_cirugia_field_id}')")

    bars: Dict[str, Any] = {}
    slot_totals: Dict[str, int] = {}

    for slot in range(1, 7):
        br = calc_bar(slot, cfg, cf)
        bars[str(slot)] = {
            "codigo": br.codigo,
            "paga": br.paga,
            "monto": br.monto,
            "error": br.error,
            "missing": br.missing,
        }
        if br.error:
            errors.append(f"BAR{slot}: {br.error}")
        if br.monto is not None:
            slot_totals[str(slot)] = int(br.monto)

    collaborators = get_collaborators(cfg, cf)

    # Pago por rol
    person_totals: Dict[str, Dict[str, Any]] = {}
    role_to_slots = {
        "c1": ("1", "4"),
        "c2": ("2", "5"),
        "c3": ("3", "6"),
    }

    for role, (s_base, s_extra) in role_to_slots.items():
        person = collaborators.get(role) or {"id": None, "label": None}
        pid = person.get("id") or role
        label = person.get("label")

        base = int(slot_totals.get(s_base) or 0)
        extra = int(slot_totals.get(s_extra) or 0)

        if pid not in person_totals:
            person_totals[pid] = {"label": label or pid, "base": 0, "extra": 0, "total": 0, "roles": []}

        person_totals[pid]["base"] += base
        person_totals[pid]["extra"] += extra
        person_totals[pid]["total"] += base + extra
        person_totals[pid]["roles"].append(role)

    return {
        "deal_id": deal.get("id"),
        "name": deal.get("name"),
        "stage_id": deal.get("stage_id"),
        "created_at": deal.get("created_at"),
        "fecha_cirugia": fecha_cirugia.isoformat() if fecha_cirugia else None,
        "bars": bars,
        "slot_totals": slot_totals,
        "collaborators": collaborators,
        "person_totals": person_totals,
        "errors": errors,
    }


def month_bounds(year: int, month: int) -> Tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def calc_month(cfg: IncentivosConfig, deals: List[Dict[str, Any]], year: int, month: int) -> Dict[str, Any]:
    start, end = month_bounds(year, month)

    totals_by_slot = {str(i): 0 for i in range(1, 7)}
    counts_by_slot = {str(i): {"pagados": 0, "no_pagados": 0, "missing": 0, "invalid": 0} for i in range(1, 7)}

    totals_by_person: Dict[str, Dict[str, Any]] = {}

    processed = 0
    month_matched = 0
    deal_errors: List[Dict[str, Any]] = []

    for deal in deals:
        processed += 1
        d = calc_deal(cfg, deal)

        fc = parse_iso_date(d.get("fecha_cirugia"))
        if fc is None or not (start <= fc < end):
            continue
        month_matched += 1

        # Regla solicitada: si falta un BAR, se suman solo los que existan.
        # Si hay valores inválidos, se reporta en auditoría pero no se pierde el resto del deal.
        if d["errors"]:
            deal_errors.append({"deal_id": d["deal_id"], "errors": d["errors"]})

        for slot in range(1, 7):
            slot_s = str(slot)
            b = d["bars"][slot_s]
            if b.get("missing"):
                counts_by_slot[slot_s]["missing"] += 1
                continue
            if b.get("error"):
                counts_by_slot[slot_s]["invalid"] += 1
                continue
            # Existe y es válido
            totals_by_slot[slot_s] += int(b["monto"] or 0)
            if b["paga"] is True:
                counts_by_slot[slot_s]["pagados"] += 1
            elif b["paga"] is False:
                counts_by_slot[slot_s]["no_pagados"] += 1

        for pid, pdata in d["person_totals"].items():
            if pid not in totals_by_person:
                totals_by_person[pid] = {
                    "label": pdata.get("label") or pid,
                    "base": 0,
                    "extra": 0,
                    "total": 0,
                    "deals": 0,
                }
            totals_by_person[pid]["base"] += int(pdata.get("base") or 0)
            totals_by_person[pid]["extra"] += int(pdata.get("extra") or 0)
            totals_by_person[pid]["total"] += int(pdata.get("total") or 0)
            totals_by_person[pid]["deals"] += 1

    return {
        "month": f"{year:04d}-{month:02d}",
        "window": {"start": start.isoformat(), "end_exclusive": end.isoformat()},
        "processed_deals": processed,
        "month_matched_deals": month_matched,
        "totals_by_slot": totals_by_slot,
        "counts_by_slot": counts_by_slot,
        "totals_by_person": totals_by_person,
        "deal_errors": deal_errors,
    }
