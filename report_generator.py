from __future__ import annotations

import datetime as _dt
import math
import zipfile
from pathlib import Path
from typing import Iterable, Sequence
from xml.sax.saxutils import escape

from II_calculations import SettlementBreakdown, LoadSettlementStep, ThawSettlementStep
from kc_table import kc_from_psi_alpha_r
from ke_lookup import ke_from_psi_alpha
from kn_lookup import _normalize_shape, kn_from_psi_beta
from ksi_e_lookup import ksi_e
from ksic_table import ksic


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
    <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:uiPriority w:val="9"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:uiPriority w:val="9"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="80"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="28"/></w:rPr>
  </w:style>
</w:styles>
"""

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _p(text: str, *, style: str | None = None) -> str:
    style_xml = f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""
    return (
        f"<w:p>{style_xml}<w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"
    )


def _body(paragraphs: Sequence[str]) -> str:
    sect = (
        "<w:sectPr>"
        "<w:pgSz w:w=\"11906\" w:h=\"16838\"/>"
        "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
        "</w:sectPr>"
    )
    joined = "".join(paragraphs)
    return (
        f"<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<w:document xmlns:w=\"{W_NS}\"><w:body>{joined}{sect}</w:body></w:document>"
    )


def _format_value(value: float, precision: int = 6) -> str:
    if math.isnan(value):
        return "н/д"
    return f"{value:.{precision}f}"


def _render_thaw_step(step: ThawSettlementStep) -> str:
    return (
        f"• {step.soil_code} ({step.soil_name}) — h= {_format_value(step.thickness_used, 3)} м, "
        f"σ̄={_format_value(step.sigma_mid, 3)} кПа, Ath={_format_value(step.Ath, 6)}, "
        f"mth={_format_value(step.mth, 6)}, вклад={_format_value(step.contribution, 6)} м"
    )


def _render_load_step(step: LoadSettlementStep, *, H: float, depth: float) -> str:
    d_top = H - step.overlap_top
    d_bottom = H - step.overlap_bottom
    return (
        f"• {step.soil_code} ({step.soil_name}) — зона z∈[{_format_value(d_top,3)}; {_format_value(d_bottom,3)}] м при Hc={_format_value(depth,3)} м: "
        f"kμi={_format_value(step.kmui,3)}, k_i={_format_value(step.ki_bottom - step.ki_top,3)}, вклад={_format_value(step.contribution,6)}"
    )


def _add_breakdown_paragraphs(paragraphs: list[str], breakdown: SettlementBreakdown, *, H: float) -> None:
    paragraphs.append(_p(f"Расчёт для глубины оттаивания {breakdown.depth:.3f} м", style="Heading2"))
    paragraphs.append(_p("Формула: S = S_th + S_p"))
    paragraphs.append(
        _p(
            "S_th = Σ h_i · (Ath_i + mth_i · σ̄_i); S_p = p0 · b · kh · Σ mth_i · kμi · (k_i,низ − k_i,верх)"
        )
    )

    paragraphs.append(_p(f"Площадная нагрузка p0 = F/(a·b) = {_format_value(breakdown.p0,3)} кПа"))
    paragraphs.append(_p(f"Коэффициент kh(z/b) = {_format_value(breakdown.kh_value,3)}"))

    paragraphs.append(_p(f"Расчёт S_th (оттаивание), суммарно {_format_value(breakdown.sth, 6)} м:"))
    for step in breakdown.thaw_steps:
        paragraphs.append(_p(_render_thaw_step(step)))

    paragraphs.append(_p(f"Расчёт S_p (нагрузка), суммарно {_format_value(breakdown.sp, 6)} м:"))
    for step in breakdown.load_steps:
        paragraphs.append(_p(_render_load_step(step, H=H, depth=breakdown.depth)))

    paragraphs.append(
        _p(
            f"Итого при Hc={_format_value(breakdown.depth,3)} м: S = S_th + S_p = {_format_value(breakdown.sth,6)} + {_format_value(breakdown.sp,6)} = {_format_value(breakdown.total,6)} м"
        )
    )


def build_thaw_depth_report(
    path: str | Path,
    *,
    foundation_shape: str,
    L: float,
    B: float,
    parameters: dict[str, float],
    alpha_r: float,
    beta: float,
    psi: float,
    hc: float,
    he: float,
) -> Path:
    """Формирует отчёт по расчёту глубины оттаивания."""

    psi_clamped = min(max(psi, 0.0), 3.5)
    psi_for_tables = psi_clamped
    clamping_note = (
        f"Исходное значение ψ={_format_value(psi, 3)} превышает 3.5. "
        f"Для поиска по таблицам берём граничное значение ψ={_format_value(psi_for_tables, 3)}, "
        "дальнейшая интерполяция автоматически прижимает аргумент к верхней границе сетки."
    )
    if psi == psi_clamped:
        clamping_note = "ψ находится в допустимом диапазоне 0…3.5, корректировка не требуется."

    paragraphs: list[str] = []
    paragraphs.append(_p("Отчёт по расчёту глубины оттаивания", style="Heading1"))
    paragraphs.append(_p(f"Дата: {_dt.datetime.now().strftime('%d.%m.%Y %H:%M')}"))
    paragraphs.append(
        _p(
            "Форма фундамента: "
            f"{foundation_shape}; L={_format_value(L, 3)} м; B={_format_value(B, 3)} м"
        )
    )

    paragraphs.append(_p("Исходные параметры:"))
    paragraphs.append(
        _p(
            f"λth={_format_value(parameters['lambdath'], 6)} Вт/(м·°С); "
            f"λf={_format_value(parameters['lambdaf'], 6)} Вт/(м·°С); "
            f"R0={_format_value(parameters['R0'], 6)} м²·°С/Вт"
        )
    )
    paragraphs.append(
        _p(
            f"T0={_format_value(parameters['T0'], 3)} °С; "
            f"Tbf={_format_value(parameters['Tbf'], 3)} °С; "
            f"Tin={_format_value(parameters['Tin'], 3)} °С"
        )
    )
    paragraphs.append(
        _p(
            f"t={_format_value(parameters['t'], 3)} с; "
            f"Lv={_format_value(parameters['Lv'], 3)} Дж/м³"
        )
    )

    paragraphs.append(_p("Промежуточные вычисления параметров:"))
    paragraphs.append(
        _p(
            "α_r = λ_th · R0 / B = "
            f"{_format_value(parameters['lambdath'], 3)} · {_format_value(parameters['R0'], 3)} / {_format_value(B, 3)} "
            f"= {_format_value(alpha_r, 6)}"
        )
    )
    paragraphs.append(
        _p(
            "β = −λ_f · (T0 − Tbf) / (λ_th · (Tin − Tbf)) = "
            f"−{_format_value(parameters['lambdaf'], 3)} · ({_format_value(parameters['T0'], 3)} − {_format_value(parameters['Tbf'], 3)}) / "
            f"({_format_value(parameters['lambdath'], 3)} · ({_format_value(parameters['Tin'], 3)} − {_format_value(parameters['Tbf'], 3)})) "
            f"= {_format_value(beta, 6)}"
        )
    )
    paragraphs.append(
        _p(
            "ψ = λ_th · Tin · t / (Lv · B²) = "
            f"{_format_value(parameters['lambdath'], 3)} · {_format_value(parameters['Tin'], 3)} · {_format_value(parameters['t'], 3)} / "
            f"({_format_value(parameters['Lv'], 3)} · {_format_value(B, 3)}²) = {_format_value(psi, 6)}"
        )
    )
    paragraphs.append(_p(clamping_note))

    kn_value = kn_from_psi_beta(psi_for_tables, beta, shape=foundation_shape, L=L, B=B)
    xi_c = ksic(psi_for_tables, beta)
    kc_value = kc_from_psi_alpha_r(psi_for_tables, alpha_r)
    xi_e = ksi_e(psi_for_tables, beta)
    ke_value = ke_from_psi_alpha(psi_for_tables, alpha_r)
    correction = 0.18 * beta * math.sqrt(psi_for_tables)

    normalized_shape = _normalize_shape(foundation_shape)
    if normalized_shape == "round":
        psi_kn_note = (
            "Коэффициент k_n="
            f"{_format_value(kn_value, 6)} получен из раздела таблицы К.1 для круглого фундамента: "
            "использованы ψ="
            f"{_format_value(psi_for_tables, 3)} и β={_format_value(beta, 3)}, поиск выполнен "
            "с интерполяцией по обоим параметрам и прижиманием аргументов к диапазону 0…2."
        )
    else:
        ratio = float(L) / float(B)
        nearest_ratio = 1.0 if abs(ratio - 1.0) <= abs(ratio - 2.0) else 2.0
        psi_kn_note = (
            "Коэффициент k_n="
            f"{_format_value(kn_value, 6)} получен из раздела таблицы К.1 для прямоугольного "
            f"фундамента: фактическое отношение L/B={_format_value(ratio, 3)}, выбрана часть таблицы "
            f"с L/B={nearest_ratio:.1f}. Значение определено по ψ={_format_value(psi_for_tables, 3)} "
            f"и β={_format_value(beta, 3)} с интерполяцией и прижиманием аргументов к диапазону 0…2."
        )
    paragraphs.append(_p(psi_kn_note))

    paragraphs.append(
        _p(
            f"По таблице k_c(ψ, α_r) при ψ={_format_value(psi_for_tables, 3)} и α_r={_format_value(alpha_r, 3)} "
            f"принято k_c={_format_value(kc_value, 6)}"
        )
    )
    paragraphs.append(
        _p(
            f"По таблице k_e(ψ, α_r) при ψ={_format_value(psi_for_tables, 3)} и α_r={_format_value(alpha_r, 3)} "
            f"принято k_e={_format_value(ke_value, 6)}"
        )
    )
    paragraphs.append(
        _p(
            f"По таблице ξ_c(ψ, β) при ψ={_format_value(psi_for_tables, 3)} и β={_format_value(beta, 3)} "
            f"принято ξ_c={_format_value(xi_c, 6)}"
        )
    )
    paragraphs.append(
        _p(
            f"По таблице ξ_e(ψ, β) при ψ={_format_value(psi_for_tables, 3)} и β={_format_value(beta, 3)} "
            f"принято ξ_e={_format_value(xi_e, 6)}"
        )
    )

    paragraphs.append(
        _p(
            "Расчёт глубины в центре: Hc = k_n · (ξ_c − k_c) · B = "
            f"{_format_value(kn_value, 6)} · ({_format_value(xi_c, 6)} − {_format_value(kc_value, 6)}) · {_format_value(B, 3)} "
            f"= {_format_value(hc, 6)} м"
        )
    )
    paragraphs.append(
        _p(
            "Расчёт глубины у края: He = k_n · (ξ_e − k_e − 0.18·β·√ψ) · B = "
            f"{_format_value(kn_value, 6)} · ({_format_value(xi_e, 6)} − {_format_value(ke_value, 6)} − "
            f"0.18·{_format_value(beta, 6)}·√{_format_value(psi, 6)}) · {_format_value(B, 3)} = {_format_value(he, 6)} м"
        )
    )

    paragraphs.append(
        _p(
            f"Глубина оттаивания под центром Hc={_format_value(hc, 6)} м; "
            f"глубина оттаивания под краем He={_format_value(he, 6)} м"
        )
    )

    document_xml = _body(paragraphs)

    path = Path(path)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
        zf.writestr("word/styles.xml", STYLES)
        zf.writestr("word/document.xml", document_xml)

    return path


def build_docx_report(
    path: str | Path,
    *,
    borehole_name: str,
    borehole_top: float,
    layers: Iterable[tuple[str, str, str, float, float, float, float]],
    params: dict[str, float],
    Hc_result: SettlementBreakdown,
    He_result: SettlementBreakdown,
) -> Path:
    paragraphs: list[str] = []
    paragraphs.append(_p("Отчёт по расчёту осадки основания", style="Heading1"))
    paragraphs.append(_p(f"Дата: {_dt.datetime.now().strftime('%d.%m.%Y %H:%M')}"))
    paragraphs.append(_p(f"Скважина {borehole_name}, отметка устья {borehole_top} м"))

    paragraphs.append(
        _p(
            "Исходные данные: H="
            f"{_format_value(params['H'],3)} м; F={_format_value(params['F'],3)} кН; "
            f"L={_format_value(params['L'],3)} м; B={_format_value(params['B'],3)} м; "
            f"Hc={_format_value(params['Hc'],3)} м; He={_format_value(params['He'],3)} м"
        )
    )

    paragraphs.append(_p("Слои скважины (сверху вниз):"))
    for code, name, soil_type, rho, Ath, mth, thickness in layers:
        paragraphs.append(
            _p(
                f"• {code} — {name} ({soil_type}), ρ={_format_value(rho,3)} кг/м³, "
                f"Ath={_format_value(Ath,6)}, mth={_format_value(mth,6)}, h={_format_value(thickness,3)} м"
            )
        )

    _add_breakdown_paragraphs(paragraphs, Hc_result, H=params["H"])
    _add_breakdown_paragraphs(paragraphs, He_result, H=params["H"])

    document_xml = _body(paragraphs)

    path = Path(path)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/_rels/document.xml.rels", DOC_RELS)
        zf.writestr("word/styles.xml", STYLES)
        zf.writestr("word/document.xml", document_xml)

    return path
