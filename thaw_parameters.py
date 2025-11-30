"""Функции для расчёта параметров теплового расчёта (alphaR, beta, psi)."""


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
    return lambdaf * (T0 - Tbf) / denominator


def calculate_psi(lambdath: float, Tin: float, t: float, Lv: float, B: float) -> float:
    """Вычисляет ``psi = lambdath * Tin * t / (Lv * B**2)``."""
    denominator = Lv * B**2
    if denominator == 0:
        raise ValueError("Знаменатель в формуле ψ не должен быть равен нулю")
    return lambdath * Tin * t / denominator
