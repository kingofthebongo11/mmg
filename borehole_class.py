from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Union


from grunt_class import Soil, PermafrostSoil   # <-- импортируем из вашего файла

SoilLike = Union[Soil, PermafrostSoil]

@dataclass(slots=True)
class BoreholeLayer:
    soil: SoilLike      # грунт (любой ваш Soil или PermafrostSoil)
    thickness: float    # толщина слоя, м ( > 0 )

@dataclass(slots=True, kw_only=True)
class Borehole:
    """Скважина со стратиграфией сверху вниз.
    z_top — абсолютная отметка устья (м). z возрастает вверх.
    """
    code: str
    z_top: float
    layers: List[BoreholeLayer] = field(default_factory=list)

    def add(self, soil: SoilLike, thickness: float) -> "Borehole":
        """Добавить слой с указанной толщиной (м). Возвращает self для чейнинга."""
        if thickness <= 0:
            raise ValueError("Толщина слоя должна быть > 0 м.")
        self.layers.append(BoreholeLayer(soil=soil, thickness=thickness))
        return self

    @property
    def total_thickness(self) -> float:
        return sum(L.thickness for L in self.layers)

    @property
    def z_bottom(self) -> float:
        """Абсолютная отметка низа скважины (последнего слоя)."""
        return self.z_top - self.total_thickness

    def stratigraphy(self) -> List[Tuple[SoilLike, float, float, float]]:
        """Возвращает список (soil, z_top_layer, z_bottom_layer, thickness)."""
        out: List[Tuple[SoilLike, float, float, float]] = []
        z_current = self.z_top
        for L in self.layers:
            z_next = z_current - L.thickness
            out.append((L.soil, z_current, z_next, L.thickness))
            z_current = z_next
        return out

    def layer_at_depth(self, depth: float) -> BoreholeLayer | None:
        """Найти слой по глубине от устья (м). depth ≥ 0.
        Пример: depth=1.2 м — слой, в котором находится отметка z = z_top - 1.2.
        """
        if depth < 0:
            raise ValueError("Глубина не может быть отрицательной.")
        acc = 0.0
        for L in self.layers:
            acc_next = acc + L.thickness
            if depth < acc_next or abs(depth - acc_next) < 1e-9:
                return L
            acc = acc_next
        return None

    def __str__(self) -> str:
        rows = [f"Скважина {self.code}: z_top={self.z_top:.3f} м, z_bottom={self.z_bottom:.3f} м"]
        for soil, zt, zb, h in self.stratigraphy():
            rows.append(f"  {soil.code:>6} | {zt:8.3f} → {zb:8.3f}  (h={h:.3f} м)")
        return "\n".join(rows)
