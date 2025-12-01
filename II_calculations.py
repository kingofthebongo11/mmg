from dataclasses import dataclass
from typing import List

from borehole_class import Borehole
from function_for_II_calculations import kh, ki, kmui


@dataclass(slots=True)
class ThawSettlementStep:
    soil_code: str
    soil_name: str
    thickness_used: float
    sigma_mid: float
    Ath: float
    mth: float
    contribution: float
    z_top: float
    z_bottom: float


@dataclass(slots=True)
class LoadSettlementStep:
    soil_code: str
    soil_name: str
    overlap_top: float
    overlap_bottom: float
    ki_top: float
    ki_bottom: float
    kmui: float
    mth: float
    contribution: float


@dataclass(slots=True)
class SettlementBreakdown:
    depth: float
    sth: float
    sp: float
    total: float
    p0: float
    kh_value: float
    thaw_steps: List[ThawSettlementStep]
    load_steps: List[LoadSettlementStep]


def full_displacment(sth: float, sp: float) -> float:
    s = sth + sp
    return s


def _disp_sth_details(borehole: Borehole, Hc: float, H: float) -> tuple[float, List[ThawSettlementStep]]:
    """
    Суммарная толщина слоёв в пределах глубины Hc (от устья вниз) и подробности расчёта.
    Если Hc > общей мощности, берём всю скважину.
    """
    if Hc < 0:
        raise ValueError("Hc должно быть ≥ 0.")

    steps: List[ThawSettlementStep] = []
    sth = 0.0
    remaining = Hc
    sigmai = 0.0
    curenztop = borehole.z_top

    for layer in borehole.layers:  # порядок = нумерация: 0-й, 1-й, 2-й...
        if remaining <= 0:
            break
        curenzbottom = curenztop - layer.thickness
        if curenzbottom >= H:
            sigmai += layer.soil.gamma_kNm3 * layer.thickness
            curenztop = curenzbottom
            continue
        take = min(layer.thickness, remaining)  # часть слоя, попадающая в Hc
        if H < curenztop:
            sigmai += layer.soil.gamma_kNm3 * (curenztop - H)
            take -= curenztop - H

        sigmai += take / 2 * layer.soil.gamma_kNm3
        contribution = take * (layer.soil.Ath + layer.soil.mth * sigmai)
        sth += contribution
        steps.append(
            ThawSettlementStep(
                soil_code=layer.soil.code,
                soil_name=layer.soil.name,
                thickness_used=take,
                sigma_mid=sigmai,
                Ath=layer.soil.Ath,
                mth=layer.soil.mth,
                contribution=contribution,
                z_top=curenztop,
                z_bottom=curenztop - take,
            )
        )
        remaining -= take
        curenztop = curenzbottom
        sigmai += take / 2 * layer.soil.gamma_kNm3

    return sth, steps


def _disp_sp_details(
    borehole: Borehole, F: float, a: float, b: float, Hc: float, H: float
) -> tuple[float, float, float, List[LoadSettlementStep]]:
    sp = 0.0
    steps: List[LoadSettlementStep] = []

    # Целевая «сжимаемая» зона по абсолютным отметкам: от H - Hc (ниже) до H (подошва)
    target_bottom = H - Hc   # более низкая (более «глубокая», численно меньше при оси z вверх)
    target_top = H           # подошва фундамента

    curenztop = borehole.z_top  # верх первой толщи по абсолютной отметке

    for layer in borehole.layers:  # 0-й, 1-й, 2-й...
        curenzbottom = curenztop - layer.thickness  # вниз по z

        # Пересечение слоя [curenzbottom, curenztop] с зоной [target_bottom, target_top]
        overlap_top = min(curenztop, target_top)
        overlap_bottom = max(curenzbottom, target_bottom)
        take = overlap_top - overlap_bottom  # толщина части слоя, попавшей в Hc (>=0, если есть пересечение)

        if take > 1e-12:
            # Глубины от подошвы (0 на отметке H, положительно вниз)
            d_top = H - overlap_top         # верх отрезка в глубинах
            d_bottom = H - overlap_bottom   # низ отрезка в глубинах
            d_mid = 0.5 * (d_top + d_bottom)

            # Коэффициенты: ki — перв/послед на границах, kmui — в середине
            kmuicalc = kmui(z=d_mid, b=b, soil_type=layer.soil.soil_type.value)
            ki_top = ki(a=a, b=b, z=d_top)
            ki_bottom = ki(a=a, b=b, z=d_bottom)

            segment = layer.soil.mth * kmuicalc * (ki_bottom - ki_top)
            sp += segment
            steps.append(
                LoadSettlementStep(
                    soil_code=layer.soil.code,
                    soil_name=layer.soil.name,
                    overlap_top=overlap_top,
                    overlap_bottom=overlap_bottom,
                    ki_top=ki_top,
                    ki_bottom=ki_bottom,
                    kmui=kmuicalc,
                    mth=layer.soil.mth,
                    contribution=segment,
                )
            )

        # Переходим к следующему слою
        curenztop = curenzbottom

        # Оптимизация: если уже прошли ниже target_bottom, дальше пересечений не будет
        if curenztop <= target_bottom:
            break

    # Нагрузка и коэффициент kh по полной Hc от подошвы
    p0 = F / (a * b)
    khcalc = kh(z=Hc, b=b)
    sp = sp * p0 * b * khcalc
    return sp, p0, khcalc, steps


def calculate_settlement(
    borehole: Borehole, Hc: float, H: float, F: float, a: float, b: float
) -> SettlementBreakdown:
    sth, thaw_steps = _disp_sth_details(borehole=borehole, Hc=Hc, H=H)
    sp, p0, khcalc, load_steps = _disp_sp_details(
        borehole=borehole, F=F, a=a, b=b, Hc=Hc, H=H
    )
    total = full_displacment(sth, sp)
    return SettlementBreakdown(
        depth=Hc,
        sth=sth,
        sp=sp,
        total=total,
        p0=p0,
        kh_value=khcalc,
        thaw_steps=thaw_steps,
        load_steps=load_steps,
    )


def disp_sth(borehole: Borehole, Hc: float, H: float) -> float:
    sth, _ = _disp_sth_details(borehole=borehole, Hc=Hc, H=H)
    return sth


def disp_sp(borehole: Borehole, F: float, a: float, b: float, Hc: float, H: float) -> float:
    sp, _, _, _ = _disp_sp_details(borehole=borehole, F=F, a=a, b=b, Hc=Hc, H=H)
    return sp


def disp_calculation(borehole: Borehole, Hc: float, H: float, F: float, a: float, b: float) -> float:
    result = calculate_settlement(borehole=borehole, Hc=Hc, H=H, F=F, a=a, b=b)
    return result.total
