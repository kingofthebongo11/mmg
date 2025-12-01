"""Функции для расчёта параметров теплового расчёта (alphaR, beta, psi)."""

from math import sqrt

from kc_table import kc_from_psi_alpha_r
from ke_lookup import ke_from_psi_alpha
from kn_lookup import kn_from_psi_beta
from ksi_e_lookup import ksi_e
from ksic_table import ksic


def calculate_alpha_r(lambdath: float, R0: float, B: float) -> float:
    """Вычисляет ``alphaR = lambdath * R0 / B``.

    :param lambdath: Теплопроводность талого грунта, Вт/(м·°C).
    :param R0: Сопротивление теплопередаче пола первого этажа или подвала, м²·°C/Вт.
    :param B: Размер фундамента B, м.
    """
    if B == 0:
        raise ValueError("B не должно быть равно нулю")
    return lambdath * R0 / B


def calculate_beta(lambdaf: float, T0: float, Tbf: float, lambdath: float, Tin: float) -> float:
    """Вычисляет ``beta = lambdaf * (T0 - Tbf) / (lambdath * (Tin - Tbf))``."""
    denominator = lambdath * (Tin - Tbf)
    if denominator == 0:
        raise ValueError("Знаменатель в формуле β не должен быть равен нулю")
    return -1*lambdaf * (T0 - Tbf) / denominator


def calculate_psi(lambdath: float, Tin: float, t: float, Lv: float, B: float) -> float:
    """Вычисляет ``psi = lambdath * Tin * t / (Lv * B**2)``."""
    denominator = Lv * B**2
    if denominator == 0:
        raise ValueError("Знаменатель в формуле ψ не должен быть равен нулю")
    return lambdath * Tin * t / denominator


def calculate_hc(
    *,
    alpha_r: float,
    beta: float,
    psi: float,
    B: float,
    shape: str,
    L: float,
) -> float:
    """Рассчитывает глубину оттаивания под центром площадки Hc."""

    if psi < 0:
        raise ValueError("Параметр ψ должен быть неотрицательным")

    kn = kn_from_psi_beta(psi, beta, shape=shape, L=L, B=B)
    xi_c = ksic(psi, beta)
    kc = kc_from_psi_alpha_r(psi, alpha_r)
    return kn * (xi_c - kc) * B


def calculate_he(
    *,
    alpha_r: float,
    beta: float,
    psi: float,
    B: float,
    shape: str,
    L: float,
) -> float:
    """Рассчитывает глубину оттаивания под краем площадки He."""

    if psi < 0:
        raise ValueError("Параметр ψ должен быть неотрицательным")

    kn = kn_from_psi_beta(psi, beta, shape=shape, L=L, B=B)
    xi_e = ksi_e(psi, beta)

    if alpha_r == 0:
        return kn * xi_e * B

    ke = ke_from_psi_alpha(psi, alpha_r)
    correction = 0.18 * beta * sqrt(psi)
    return kn * (xi_e - ke - correction) * B
