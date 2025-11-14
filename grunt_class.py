from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# --- Базовые типы как раньше ---
class SoilType(Enum):
    COARSE = "крупнообломочные"
    SAND_AND_SUPES = "песчаные и супеси"
    LOAM = "суглинки"
    CLAY = "глины"

@dataclass(slots=True, kw_only=True)
class Soil:
    code: str
    name: str
    soil_type: SoilType
    rho: float  # кг/м³

    def __post_init__(self):
        if not self.code or not self.name:
            raise ValueError("code/name не должны быть пустыми.")
        if self.rho <= 0:
            raise ValueError("rho должно быть > 0.")
        if not (900 <= self.rho <= 3000):
            raise ValueError("rho выглядит нетипично (≈900–3000 кг/м³).")

    @property
    def gamma_kNm3(self) -> float:
        return self.rho * 9.81 / 1000.0

# --- Пустые фазы ---
class SoilPhase(Enum):
    THAWED = "талый"
    FROZEN = "мерзлый"

@dataclass(slots=True)
class Phase:
    """Пустой контейнер-фаза: сейчас без полей, потом можно расширить."""
    pass

# --- ММГ-наследник с пустыми фазами + Ath, mth ---
@dataclass(slots=True, kw_only=True)
class PermafrostSoil(Soil):
    thawed: Phase = field(default_factory=Phase)
    frozen: Phase = field(default_factory=Phase)
    Ath: Optional[float] = None   # коэффициент оттаивания
    mth: Optional[float] = None   # коэффициент сжимаемости при оттаивании

    def __post_init__(self):
        Soil.__post_init__(self)  # <-- вместо super().__post_init__()
        if self.Ath is not None and self.Ath < 0:
            raise ValueError("Ath не может быть отрицательным.")
        if self.mth is not None and self.mth < 0:
            raise ValueError("mth не может быть отрицательным.")
