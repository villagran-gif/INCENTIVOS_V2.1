from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, List

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BarRule(BaseModel):
    field_id: str
    min: int
    # Código "PAGA" principal.
    max: int
    # Si existe más de un código equivalente a "PAGA" (por ejemplo por legacy),
    # puedes listarlos acá. Si se define, se usa en vez de `max`.
    max_values: Optional[list[int]] = None
    amount: int = 0


class IncentivosConfig(BaseModel):
    # Contexto negocio
    pipeline_id: int
    stage_ids: List[int] = Field(default_factory=list)

    # Campos Sell (en tu cuenta: custom_fields viene por NOMBRE)
    fecha_cirugia_field_id: str
    collaborator_field_ids: Dict[str, str]
    bars: Dict[str, BarRule]

    # Etapa 1: extras siempre aplican (true). Etapa futura: false + regla.
    extras_enabled: bool = True

    timezone: str = "America/Sao_Paulo"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    sell_access_token: str = Field(..., alias="SELL_ACCESS_TOKEN")
    sell_base_url: str = Field("https://api.getbase.com", alias="SELL_BASE_URL")
    sell_search_base_url: str = Field("https://api.getbase.com", alias="SELL_SEARCH_BASE_URL")

    config_path: str = Field("config/incentivos_config.json", alias="INCENTIVOS_CONFIG")

    # API tuning
    per_page: int = Field(100, alias="SELL_PER_PAGE")
    timeout_s: float = Field(30.0, alias="SELL_TIMEOUT_S")

    # Server
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")


def load_incentivos_config(path: str | Path) -> IncentivosConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"No existe {p}. Copia config/incentivos_config.example.json a {p} y ajusta montos (amount)."
        )

    raw: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    return IncentivosConfig.model_validate(raw)
