from app.calculator import calc_bar
from app.config import IncentivosConfig, BarRule


def _cfg():
    return IncentivosConfig(
        pipeline_id=1290779,
        stage_ids=[10693256, 35531166],
        fecha_cirugia_field_id="FECHA DE CIRUGÍA",
        collaborator_field_ids={"c1": "Colaborador1", "c2": "Colaborador2", "c3": "Colaborador3"},
        bars={
            "1": BarRule(field_id="ComisionBAR1", min=1, max=8001, amount=100),
            "2": BarRule(field_id="ComisionBAR2", min=2, max=5002, amount=200),
            "3": BarRule(field_id="ComisionBAR3", min=3, max=5003, amount=300),
            "4": BarRule(field_id="ComisionBAR4", min=4, max=9004, amount=400),
            "5": BarRule(field_id="ComisionBAR5", min=5, max=6005, amount=500),
            "6": BarRule(field_id="ComisionBAR6", min=6, max=6006, amount=600),
        },
        extras_enabled=True,
    )


def test_bar_paga_max():
    cfg = _cfg()
    cf = {"ComisionBAR1": "8001"}
    r = calc_bar(1, cfg, cf)
    assert r.paga is True
    assert r.monto == 8001


def test_bar_no_paga_min():
    cfg = _cfg()
    cf = {"ComisionBAR1": "1"}
    r = calc_bar(1, cfg, cf)
    assert r.paga is False
    assert r.monto == 1


def test_bar_invalid():
    cfg = _cfg()
    cf = {"ComisionBAR1": "999"}
    r = calc_bar(1, cfg, cf)
    assert r.error


def test_bar_missing_is_ignored():
    cfg = _cfg()
    cf = {}
    r = calc_bar(1, cfg, cf)
    assert r.missing is True
    assert r.error is None
