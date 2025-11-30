"""
Расчёт коэффициента \u03be_e по графику (\u03c8, \u03b2) → \u03be_e.

Основа — табличная аппроксимация значений с графика: ось \u03c8 (0..3.5), ось \u03b2 (0..2.0).
"""
from Table_class import Table2D

# Сетка по ψ (горизонтальная ось на графике)
PSI_GRID = [
    0.0,
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
    3.5,
]

# Подписи линий β на графике: от 0 до 2.0
BETA_GRID = [
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
    2.0,
]

# Наклоны линий (\u03be_e / \u03c8) оценены по графику.
# Все линии почти лучи из начала координат, поэтому используем постоянный коэффициент на выбранной β.
_COEFF_BY_BETA = [0.2 + 0.0715 * beta for beta in BETA_GRID]

# Матрица ξ_e(ψ, β): размер len(PSI_GRID) x len(BETA_GRID)
_KSIE_VALUES = [
    [psi * k for k in _COEFF_BY_BETA]
    for psi in PSI_GRID
]

_KSIE_TABLE = Table2D(PSI_GRID, BETA_GRID, _KSIE_VALUES)


def ksi_e(psi: float, beta: float, *, interpolate: bool = True) -> float:
    """
    Возвращает значение \u03be_e по заданным \u03c8 и \u03b2.

    * \u03c8 ограничивается диапазоном [0, 3.5]; при \u03c8 < 0 выбрасывается ValueError.
    * \u03b2 ограничивается диапазоном [0, 2.0]; при \u03b2 < 0 выбрасывается ValueError.
    * Билинейная интерполяция включена по умолчанию.
    """
    if psi < 0:
        raise ValueError("psi должно быть неотрицательным.")
    if beta < 0:
        raise ValueError("beta должно быть неотрицательным.")

    capped_psi = min(psi, PSI_GRID[-1])
    capped_beta = min(beta, BETA_GRID[-1])
    return _KSIE_TABLE.lookup(capped_psi, capped_beta, interpolate=interpolate, clamp=True)
