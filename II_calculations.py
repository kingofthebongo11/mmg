from borehole_class import Borehole
from function_for_II_calculations import kh,ki,kmui


def full_displacment(sth: float, sp: float) -> float:
    s = sth + sp
    return s


def disp_sth(borehole: Borehole, Hc: float, H:float) -> float:
    """
    Суммарная толщина слоёв в пределах глубины Hc (от устья вниз).
    Если Hc > общей мощности, берём всю скважину.
    """
    if Hc < 0:
        raise ValueError("Hc должно быть ≥ 0.")

    sth = 0.0
    remaining = Hc
    sigmai=0
    curenztop =borehole.z_top

    for layer in borehole.layers:  # порядок = нумерация: 0-й, 1-й, 2-й...
        if remaining <= 0:
            break
        curenzbottom =curenztop- layer.thickness
        if curenzbottom>=H:
            sigmai += layer.soil.gamma_kNm3*layer.thickness
            curenztop = curenzbottom
            continue
        take = min(layer.thickness, remaining)  # часть слоя, попадающая в Hc
        if  H<curenztop:
            sigmai += layer.soil.gamma_kNm3*(curenztop-H)
            take -= curenztop-H

        sigmai += take / 2 * layer.soil.gamma_kNm3
        sth += take*(layer.soil.Ath+layer.soil.mth*sigmai)
        remaining -= take
        curenztop = curenzbottom
        sigmai += take / 2 * layer.soil.gamma_kNm3


    return sth


def disp_sp(borehole: Borehole, F: float, a: float, b: float, Hc: float, H: float) -> float:
    sp = 0.0

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

            sp += layer.soil.mth * kmuicalc * (ki_bottom - ki_top)

        # Переходим к следующему слою
        curenztop = curenzbottom

        # Оптимизация: если уже прошли ниже target_bottom, дальше пересечений не будет
        if curenztop <= target_bottom:
            break

    # Нагрузка и коэффициент kh по полной Hc от подошвы
    p0 = F / (a * b)
    khcalc = kh(z=Hc, b=b)
    sp = sp * p0 * b * khcalc
    return sp



def disp_calculation(borehole: Borehole, Hc: float,H: float,F: float, a: float, b: float) -> float:
    sth=disp_sth(borehole=borehole,Hc=Hc, H=H)
    sp=disp_sp(borehole=borehole, F=F, a=a, b=b,Hc=Hc,H=H)
    s= full_displacment(sth, sp)
    return s