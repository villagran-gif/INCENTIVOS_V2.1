import { parse, isValid, startOfMonth, addMonths } from 'date-fns';

function toInt(x) {
  if (x === null || x === undefined || x === '') return null;
  if (typeof x === 'number') return Number.isFinite(x) ? Math.trunc(x) : null;
  if (typeof x === 'object') {
    // list value could be {id, name}
    if ('id' in x) return toInt(x.id);
    if ('value' in x) return toInt(x.value);
  }
  const n = Number(String(x).trim());
  return Number.isFinite(n) ? Math.trunc(n) : null;
}

function normalizeListLabel(x) {
  if (x === null || x === undefined) return null;
  if (typeof x === 'object') return x.name || x.label || (x.id != null ? String(x.id) : null);
  return String(x);
}

export function parseFecha(value) {
  if (!value) return null;
  const s = String(value).trim();
  // Try formats seen in Sell
  const candidates = [
    { fmt: 'yyyy-MM-dd' },
    { fmt: 'M/d/yyyy' },
    { fmt: 'MM/dd/yyyy' },
    { fmt: 'd/M/yyyy' },
    { fmt: 'dd/MM/yyyy' },
  ];

  for (const c of candidates) {
    const d = parse(s, c.fmt, new Date());
    if (isValid(d)) return d;
  }

  const d2 = new Date(s);
  return isValid(d2) ? d2 : null;
}

export function calcDeal(cfg, deal) {
  const cf = deal?.custom_fields || {};
  const fecha = parseFecha(cf[cfg.fecha_cirugia_field_name]);

  const bars = {};
  const slotTotals = {};
  const countsBySlot = {};
  const errors = [];

  for (let slot = 1; slot <= 6; slot += 1) {
    const key = String(slot);
    const barCfg = cfg.bars[key];
    const field = barCfg?.field_name;

    countsBySlot[key] = { present: 0, missing: 0, invalid: 0 };

    const raw = field ? cf[field] : null;
    if (raw === null || raw === undefined || raw === '') {
      bars[key] = { codigo: null, monto: null, error: null };
      countsBySlot[key].missing += 1;
      continue;
    }

    const codigo = toInt(raw);
    if (codigo === null) {
      bars[key] = { codigo: null, monto: null, error: 'Valor no numérico' };
      countsBySlot[key].invalid += 1;
      errors.push(`BAR${slot}: Valor no numérico`);
      continue;
    }

    const allowed = new Set((barCfg?.allowed || []).map((n) => Number(n)));
    if (allowed.size && !allowed.has(codigo)) {
      bars[key] = { codigo, monto: null, error: `Valor inválido (esperado ${Array.from(allowed).sort().join(',')})` };
      countsBySlot[key].invalid += 1;
      errors.push(`BAR${slot}: Valor inválido`);
      continue;
    }

    // Regla: monto en pesos = código
    bars[key] = { codigo, monto: codigo, error: null };
    slotTotals[key] = (slotTotals[key] || 0) + codigo;
    countsBySlot[key].present += 1;
  }

  const collaborators = {
    c1: normalizeListLabel(cf[cfg.collaborator_field_names?.c1]),
    c2: normalizeListLabel(cf[cfg.collaborator_field_names?.c2]),
    c3: normalizeListLabel(cf[cfg.collaborator_field_names?.c3]),
  };

  // Totales por colaborador (solo suma lo presente)
  const personTotals = {};
  const roleToSlots = {
    c1: ['1', '4'],
    c2: ['2', '5'],
    c3: ['3', '6'],
  };

  for (const role of Object.keys(roleToSlots)) {
    const name = collaborators[role] || role;
    if (!personTotals[name]) personTotals[name] = { base: 0, extra: 0, total: 0, roles: [] };

    const [sBase, sExtra] = roleToSlots[role];
    const base = bars[sBase]?.monto || 0;
    const extra = bars[sExtra]?.monto || 0;

    personTotals[name].base += base;
    personTotals[name].extra += extra;
    personTotals[name].total += base + extra;
    personTotals[name].roles.push(role);
  }

  return {
    deal_id: deal?.id,
    name: deal?.name,
    stage_id: deal?.stage_id,
    created_at: deal?.created_at,
    fecha_cirugia: fecha ? fecha.toISOString().slice(0, 10) : null,
    bars,
    slot_totals: slotTotals,
    collaborators,
    person_totals: personTotals,
    errors,
  };
}

export function calcMonth(cfg, deals, year, month) {
  const start = startOfMonth(new Date(Date.UTC(year, month - 1, 1)));
  const end = addMonths(start, 1);

  const totalsBySlot = Object.fromEntries(Array.from({ length: 6 }, (_, i) => [String(i + 1), 0]));
  const countsBySlot = Object.fromEntries(Array.from({ length: 6 }, (_, i) => [String(i + 1), { present: 0, missing: 0, invalid: 0 }]));
  const totalsByPerson = {};

  let processed = 0;
  let included = 0;
  const dealErrors = [];

  for (const deal of deals) {
    processed += 1;
    const d = calcDeal(cfg, deal);
    const fc = d.fecha_cirugia ? new Date(d.fecha_cirugia + 'T00:00:00Z') : null;
    if (!fc || !(fc >= start && fc < end)) continue;
    included += 1;

    for (let slot = 1; slot <= 6; slot += 1) {
      const k = String(slot);
      const b = d.bars[k];
      if (!b || b.error) {
        countsBySlot[k].invalid += b?.error ? 1 : 0;
        continue;
      }
      if (b.monto === null || b.monto === undefined) {
        countsBySlot[k].missing += 1;
        continue;
      }
      countsBySlot[k].present += 1;
      totalsBySlot[k] += Number(b.monto);
    }

    for (const [name, t] of Object.entries(d.person_totals || {})) {
      if (!totalsByPerson[name]) totalsByPerson[name] = { base: 0, extra: 0, total: 0, deals: 0 };
      totalsByPerson[name].base += t.base;
      totalsByPerson[name].extra += t.extra;
      totalsByPerson[name].total += t.total;
      totalsByPerson[name].deals += 1;
    }

    if (d.errors?.length) dealErrors.push({ deal_id: d.deal_id, errors: d.errors });
  }

  return {
    month: `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}`,
    window: {
      start: start.toISOString().slice(0, 10),
      end_exclusive: end.toISOString().slice(0, 10),
    },
    processed_deals: processed,
    included_deals: included,
    totals_by_slot: totalsBySlot,
    counts_by_slot: countsBySlot,
    totals_by_person: totalsByPerson,
    deal_errors: dealErrors,
  };
}
