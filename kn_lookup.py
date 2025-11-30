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
        0.97,
        1.01,
        1.04,
        1.07,
        1.10,
        1.12,
        1.14,
        1.16,
        1.18,
        1.20,
        1.22,
        1.23,
        1.25,
        1.26,
        1.27,
        1.28,
        1.29,
        1.30,
        1.31,
        1.32,
        1.33,
    ],
    [
        0.96,
        1.00,
        1.03,
        1.06,
        1.08,
        1.10,
        1.12,
        1.14,
        1.15,
        1.17,
        1.19,
        1.21,
        1.22,
        1.23,
        1.24,
        1.26,
        1.27,
        1.28,
        1.29,
        1.30,
        1.31,
    ],
    [
        0.95,
        0.99,
        1.01,
        1.04,
        1.06,
        1.08,
        1.10,
        1.11,
        1.13,
        1.14,
        1.16,
        1.17,
        1.19,
        1.20,
        1.21,
        1.22,
        1.23,
        1.24,
        1.25,
        1.26,
        1.27,
    ],
]

_RECT_RATIO1_VALUES = [
    [
        0.97,
        1.00,
        1.02,
        1.05,
        1.07,
        1.10,
        1.12,
        1.14,
        1.16,
        1.18,
        1.20,
        1.22,
        1.23,
        1.24,
        1.25,
        1.26,
        1.27,
        1.28,
        1.29,
        1.30,
        1.31,
    ],
    [
        0.96,
        0.99,
        1.01,
        1.04,
        1.06,
        1.08,
        1.10,
        1.12,
        1.14,
        1.16,
        1.18,
        1.20,
        1.21,
        1.22,
        1.23,
        1.24,
        1.25,
        1.26,
        1.27,
        1.28,
        1.29,
    ],
    [
        0.94,
        0.98,
        1.00,
        1.02,
        1.04,
        1.06,
        1.08,
        1.10,
        1.12,
        1.14,
        1.16,
        1.17,
        1.19,
        1.20,
        1.21,
        1.22,
        1.23,
        1.24,
        1.24,
        1.25,
        1.26,
    ],
]

_RECT_RATIO2_VALUES = [
    [
        0.95,
        0.98,
        1.00,
        1.02,
        1.05,
        1.07,
        1.09,
        1.11,
        1.13,
        1.15,
        1.16,
        1.18,
        1.19,
        1.21,
        1.22,
        1.23,
        1.24,
        1.25,
        1.26,
        1.27,
        1.28,
    ],
    [
        0.93,
        0.97,
        0.98,
        1.00,
        1.03,
        1.05,
        1.07,
        1.09,
        1.10,
        1.12,
        1.14,
        1.15,
        1.16,
        1.17,
        1.18,
        1.19,
        1.20,
        1.21,
        1.22,
        1.23,
        1.24,
    ],
    [
        0.90,
        0.95,
        0.96,
        0.98,
        1.01,
        1.03,
        1.05,
        1.07,
        1.08,
        1.09,
        1.10,
        1.11,
        1.12,
        1.13,
        1.14,
        1.15,
        1.16,
        1.17,
        1.17,
        1.18,
        1.19,
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
