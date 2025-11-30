"""Расчёт коэффициента kc по значениям psi и alphaR."""
from __future__ import annotations

from Table_class import Table2D

# Узлы по оси psi (по горизонтали на графике)
_PSI_GRID = [
    0.0,
    0.1,
    0.2,
    0.3,
    0.5,
    0.75,
    1.0,
    1.5,
    2.0,
    3.0,
]

# Узлы по оси alpha_R (подписи на кривых графика)
_ALPHA_R_GRID = [
    0.01,
    0.1,
    0.2,
    0.3,
    0.4,
    0.5,
    0.6,
]

# Значения kc, считанные с графика: строки соответствуют alpha_R, столбцы — psi.
_KC_VALUES = [
    [0.0, 0.004, 0.007, 0.009, 0.012, 0.015, 0.017, 0.020, 0.021, 0.022],  # alpha_R = 0.01
    [0.0, 0.020, 0.035, 0.045, 0.060, 0.075, 0.085, 0.100, 0.110, 0.115],  # alpha_R = 0.10
    [0.0, 0.040, 0.070, 0.090, 0.120, 0.150, 0.170, 0.200, 0.210, 0.220],  # alpha_R = 0.20
    [0.0, 0.060, 0.100, 0.130, 0.170, 0.210, 0.230, 0.270, 0.290, 0.300],  # alpha_R = 0.30
    [0.0, 0.080, 0.130, 0.170, 0.220, 0.270, 0.300, 0.350, 0.380, 0.400],  # alpha_R = 0.40
    [0.0, 0.100, 0.170, 0.210, 0.280, 0.340, 0.380, 0.430, 0.470, 0.490],  # alpha_R = 0.50
    [0.0, 0.120, 0.200, 0.250, 0.330, 0.400, 0.450, 0.520, 0.560, 0.580],  # alpha_R = 0.60
]

_KC_TABLE = Table2D(row_grid=_ALPHA_R_GRID, col_grid=_PSI_GRID, values=_KC_VALUES)


def kc_from_psi_alpha_r(psi: float, alpha_r: float) -> float:
    """Возвращает kc по psi и alphaR с ограничением диапазонов.

    * psi < 0 → ValueError; psi > 3 прижимается к 3.
    * alphaR < 0 → ValueError; alphaR > 0.6 прижимается к 0.6.
    * Внутри диапазона используется билинейная интерполяция таблицы.
    """
    if psi < 0:
        raise ValueError("psi не может быть отрицательным.")
    if alpha_r < 0:
        raise ValueError("alphaR не может быть отрицательным.")

    psi_clamped = 3.0 if psi > 3.0 else psi
    alpha_r_clamped = 0.6 if alpha_r > 0.6 else alpha_r
    return _KC_TABLE.lookup(alpha_r_clamped, psi_clamped)
