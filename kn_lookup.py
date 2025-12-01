"""Табличная функция для получения коэффициента k_n."""
from __future__ import annotations

from typing import Dict

from Table_class import Number, Table2D

_PSI_GRID = [
    0.1,
    0.25,
    0.5,
    1.0,
    1.5,
    2.5,
    3.5,
]

_BETA_GRID = [0.0, 0.4, 0.8, 1.2, 2.0]

_ROUND_VALUES = [
    [
        0.97,
        0.93,
        0.91,
        0.90,
        0.89,
        0.88,
        0.87
    ],
    [
        0.87,
        0.79,
        0.71,
        0.64,
        0.59,
        0.54,
        0.53
    ],
    [
        0.82,
        0.71,
        0.62,
        0.57,
        0.56,
        0.56,
        0.56
    ],
    [
        0.76,
        0.64,
        0.61,
        0.59,
        0.59,
        0.59,
        0.59
    ],
    [
        0.71,
        0.61,
        0.61,
        0.61,
        0.61,
        0.61,
        0.61
    ],
]

_RECT_RATIO1_VALUES = [
    [
        1.00,
        0.95,
        0.94,
        0.92,
        0.90,
        0.89,
        0.88
    ],
    [
        0.93,
        0.85,
        0.78,
        0.70,
        0.64,
        0.58,
        0.57
    ],
    [
        0.87,
        0.78,
        0.68,
        0.63,
        0.63,
        0.63,
        0.63
    ],
    [
        0.83,
        0.74,
        0.66,
        0.66,
        0.66,
        0.66,
        0.66
    ],
    [
        0.80,
        0.68,
        0.68,
        0.68,
        0.68,
        0.68,
        0.68
    ],
]

_RECT_RATIO2_VALUES = [
    [
        1.00,
        1.00,
        0.99,
        0.97,
        0.96,
        0.95,
        0.94
    ],
    [
        1.00,
        0.97,
        0.95,
        0.90,
        0.87,
        0.84,
        0.83
    ],
    [
        0.99,
        0.92,
        0.88,
        0.82,
        0.82,
        0.82,
        0.82
    ],
    [
        0.97,
        0.89,
        0.85,
        0.85,
        0.85,
        0.85,
        0.85
    ],
    [
        0.96,
        0.96,
        0.87,
        0.87,
        0.87,
        0.87,
        0.87
    ],
]

_ROUND_TABLE = Table2D(row_grid=_BETA_GRID, col_grid=_PSI_GRID, values=_ROUND_VALUES)
_RECT_TABLES: Dict[float, Table2D] = {
    1.0: Table2D(row_grid=_BETA_GRID, col_grid=_PSI_GRID, values=_RECT_RATIO1_VALUES),
    2.0: Table2D(row_grid=_BETA_GRID, col_grid=_PSI_GRID, values=_RECT_RATIO2_VALUES),
}


def _normalize_shape(shape: str) -> str:
    normalized = shape.strip().lower()
    if normalized.startswith("круг") or normalized.startswith("round"):
        return "round"
    if normalized.startswith("прям") or normalized.startswith("rect"):
        return "rect"
    raise ValueError(f"Неизвестная форма фундамента: {shape}")


def _select_rect_table(L: Number, B: Number) -> Table2D:
    if B == 0:
        raise ValueError("Ширина B не может быть нулевой")
    ratio = float(L) / float(B)
    nearest_ratio = min(_RECT_TABLES, key=lambda value: abs(ratio - value))
    return _RECT_TABLES[nearest_ratio]


def kn_from_psi_beta(
    psi: Number,
    beta: Number,
    *,
    shape: str,
    L: Number | None = None,
    B: Number | None = None,
    interpolate: bool = True,
) -> float:
    """Возвращает коэффициент k_n по параметрам ψ и β."""

    if psi < 0:
        raise ValueError("Параметр ψ не может быть отрицательным")
    if beta < 0:
        raise ValueError("Параметр β не может быть отрицательным")

    normalized_shape = _normalize_shape(shape)

    if normalized_shape == "round":
        table = _ROUND_TABLE
    else:
        if L is None or B is None:
            raise ValueError("Для прямоугольного фундамента необходимо задать L и B")
        table = _select_rect_table(L, B)

    return float(table.lookup(beta, psi, interpolate=interpolate, clamp=True))
