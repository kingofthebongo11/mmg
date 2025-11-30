"""Табличная функция для получения коэффициента k_n."""
from __future__ import annotations

from typing import Dict

from Table_class import Number, Table2D

_PSI_GRID = [
    0.0,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    1.0,
    1.1,
    1.2,
    1.3,
    1.4,
    1.5,
    1.6,
    1.7,
    1.8,
    1.9,
    2.0,
]

_BETA_GRID = [0.0, 1.0, 2.0]

_ROUND_VALUES = [
    [
        1.00,
        0.99,
        0.98,
        0.96,
        0.95,
        0.94,
        0.93,
        0.92,
        0.91,
        0.90,
        0.89,
        0.89,
        0.88,
        0.87,
        0.86,
        0.85,
        0.85,
        0.84,
        0.83,
        0.83,
        0.82,
    ],
    [
        0.99,
        0.98,
        0.96,
        0.94,
        0.93,
        0.91,
        0.90,
        0.89,
        0.88,
        0.87,
        0.86,
        0.85,
        0.84,
        0.83,
        0.82,
        0.82,
        0.81,
        0.80,
        0.79,
        0.79,
        0.78,
    ],
    [
        0.95,
        0.93,
        0.90,
        0.87,
        0.85,
        0.83,
        0.82,
        0.80,
        0.79,
        0.78,
        0.77,
        0.76,
        0.75,
        0.74,
        0.74,
        0.73,
        0.72,
        0.71,
        0.71,
        0.70,
        0.70,
    ],
]

_RECT_RATIO1_VALUES = [
    [
        0.97,
        0.96,
        0.95,
        0.90,
        0.87,
        0.85,
        0.83,
        0.81,
        0.80,
        0.78,
        0.77,
        0.76,
        0.75,
        0.74,
        0.73,
        0.72,
        0.71,
        0.70,
        0.69,
        0.68,
        0.67,
    ],
    [
        0.96,
        0.94,
        0.91,
        0.89,
        0.86,
        0.84,
        0.82,
        0.80,
        0.79,
        0.77,
        0.76,
        0.75,
        0.74,
        0.73,
        0.72,
        0.71,
        0.70,
        0.69,
        0.68,
        0.67,
        0.66,
    ],
    [
        0.94,
        0.92,
        0.89,
        0.86,
        0.84,
        0.81,
        0.79,
        0.78,
        0.76,
        0.75,
        0.74,
        0.73,
        0.72,
        0.71,
        0.70,
        0.69,
        0.68,
        0.67,
        0.66,
        0.66,
        0.65,
    ],
]

_RECT_RATIO2_VALUES = [
    [
        0.95,
        0.93,
        0.90,
        0.88,
        0.85,
        0.83,
        0.81,
        0.79,
        0.78,
        0.76,
        0.75,
        0.74,
        0.73,
        0.72,
        0.71,
        0.70,
        0.69,
        0.68,
        0.67,
        0.66,
        0.65,
    ],
    [
        0.93,
        0.91,
        0.88,
        0.86,
        0.83,
        0.81,
        0.79,
        0.78,
        0.76,
        0.75,
        0.73,
        0.72,
        0.71,
        0.70,
        0.69,
        0.68,
        0.67,
        0.66,
        0.65,
        0.65,
        0.64,
    ],
    [
        0.90,
        0.88,
        0.85,
        0.83,
        0.80,
        0.78,
        0.76,
        0.75,
        0.73,
        0.72,
        0.70,
        0.69,
        0.68,
        0.67,
        0.66,
        0.65,
        0.64,
        0.63,
        0.62,
        0.62,
        0.61,
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
