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
    <w:docDefaults>
      <w:rPrDefault>
        <w:rPr>
          <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
          <w:sz w:val="28"/>
          <w:szCs w:val="28"/>
        </w:rPr>
      </w:rPrDefault>
      <w:pPrDefault>
        <w:pPr>
          <w:spacing w:line="360" w:lineRule="auto"/>
          <w:ind w:firstLine="709"/>
          <w:jc w:val="both"/>
        </w:pPr>
      </w:pPrDefault>
    </w:docDefaults>
    <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
      <w:name w:val="Normal"/>
      <w:qFormat/>
      <w:pPr>
        <w:spacing w:line="360" w:lineRule="auto"/>
        <w:ind w:firstLine="709"/>
        <w:jc w:val="both"/>
      </w:pPr>
      <w:rPr>
        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
        <w:sz w:val="28"/>
        <w:szCs w:val="28"/>
      </w:rPr>
    </w:style>
    <w:style w:type="paragraph" w:styleId="Heading1">
      <w:name w:val="heading 1"/>
      <w:basedOn w:val="Normal"/>
      <w:next w:val="Normal"/>
      <w:uiPriority w:val="9"/>
      <w:qFormat/>
      <w:pPr><w:spacing w:after="120"/><w:jc w:val="center"/></w:pPr>
      <w:rPr><w:b/><w:sz w:val="32"/></w:rPr>
    </w:style>
    <w:style w:type="paragraph" w:styleId="Heading2">
      <w:name w:val="heading 2"/>
      <w:basedOn w:val="Normal"/>
      <w:next w:val="Normal"/>
      <w:uiPriority w:val="9"/>
      <w:qFormat/>
      <w:pPr><w:spacing w:after="80"/><w:jc w:val="center"/></w:pPr>
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


def _run(text: str, *, italic: bool = False, subscript: bool = False) -> str:
    rpr_parts: list[str] = []
    if italic:
        rpr_parts.append("<w:i/>")
    if subscript:
        rpr_parts.append('<w:vertAlign w:val="subscript"/>')
    rpr = f"<w:rPr>{''.join(rpr_parts)}</w:rPr>" if rpr_parts else ""
    return f"<w:r>{rpr}<w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>"


def _p_runs(parts: Sequence[tuple[str, bool, bool]], *, style: str | None = None) -> str:
    style_xml = f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""
    runs = "".join(_run(text, italic=italic, subscript=subscript) for text, italic, subscript in parts)
    return f"<w:p>{style_xml}{runs}</w:p>"


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
    return _p_runs(
        [
            ("• ", False, False),
            (
                f"{step.soil_code} ({step.soil_name}) — зона z∈[{_format_value(d_top,3)}; {_format_value(d_bottom,3)}] м при ",
                False,
                False,
            ),
            ("H", True, False),
            ("c", True, True),
            ("=", False, False),
            (f"{_format_value(depth,3)} м: ", False, False),
            ("k", True, False),
            ("μ", False, False),
            ("i", True, True),
            ("=", False, False),
            (f"{_format_value(step.kmui,3)}", False, False),
            (", ", False, False),
            ("k", True, False),
            ("i", True, True),
            ("=", False, False),
            (f"{_format_value(step.ki_bottom - step.ki_top,3)}", False, False),
            (", вклад=", False, False),
            (f"{_format_value(step.contribution,6)}", False, False),
        ]
    )


def _add_breakdown_paragraphs(paragraphs: list[str], breakdown: SettlementBreakdown, *, H: float) -> None:
    paragraphs.append(_p(f"Расчёт для глубины оттаивания {breakdown.depth:.3f} м", style="Heading2"))
    paragraphs.append(
        _p_runs(
            [
                ("Формула: ", False, False),
                ("S", True, False),
                (" = ", False, False),
                ("S", True, False),
                ("th", True, True),
                (" + ", False, False),
                ("S", True, False),
                ("p", True, True),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("S", True, False),
                ("th", True, True),
                (" = Σ ", False, False),
                ("h", True, False),
                ("i", True, True),
                (" · (", False, False),
                ("A", True, False),
                ("th", True, True),
                ("i", True, True),
                (" + ", False, False),
                ("m", True, False),
                ("th", True, True),
                ("i", True, True),
                (" · σ̄", False, False),
                ("i", True, True),
                ("; ", False, False),
                ("S", True, False),
                ("p", True, True),
                (" = ", False, False),
                ("p", True, False),
                ("0", False, True),
                (" · ", False, False),
                ("b", True, False),
                (" · ", False, False),
                ("k", True, False),
                ("h", True, True),
                (" · Σ ", False, False),
                ("m", True, False),
                ("th", True, True),
                ("i", True, True),
                (" · k", True, False),
                ("μ", False, True),
                ("i", True, True),
                (" · (k", True, False),
                ("i", True, True),
                (",низ − k", False, False),
                ("i", True, True),
                (",верх)", False, False),
            ]
        )
    )

    paragraphs.append(
        _p_runs(
            [
                ("Площадная нагрузка ", False, False),
                ("p", True, False),
                ("0", False, True),
                (" = ", False, False),
                ("F", True, False),
                ("/(", False, False),
                ("a", True, False),
                ("·", False, False),
                ("b", True, False),
                (") = ", False, False),
                (f"{_format_value(breakdown.p0,3)} кПа", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("Коэффициент ", False, False),
                ("k", True, False),
                ("h", True, True),
                ("(", False, False),
                ("z", True, False),
                ("/", False, False),
                ("b", True, False),
                (") = ", False, False),
                (f"{_format_value(breakdown.kh_value,3)}", False, False),
            ]
        )
    )

    paragraphs.append(_p(f"Расчёт S_th (оттаивание), суммарно {_format_value(breakdown.sth, 6)} м:"))
    for step in breakdown.thaw_steps:
        paragraphs.append(_p(_render_thaw_step(step)))

    paragraphs.append(
        _p_runs(
            [
                ("Расчёт ", False, False),
                ("S", True, False),
                ("p", True, True),
                (" (нагрузка), суммарно ", False, False),
                (f"{_format_value(breakdown.sp, 6)} м:", False, False),
            ]
        )
    )
    for step in breakdown.load_steps:
        paragraphs.append(_render_load_step(step, H=H, depth=breakdown.depth))

    paragraphs.append(
        _p_runs(
            [
                ("Итого при ", False, False),
                ("H", True, False),
                ("c", True, True),
                ("=", False, False),
                (f"{_format_value(breakdown.depth,3)} м: ", False, False),
                ("S", True, False),
                (" = ", False, False),
                ("S", True, False),
                ("th", True, True),
                (" + ", False, False),
                ("S", True, False),
                ("p", True, True),
                (" = ", False, False),
                (f"{_format_value(breakdown.sth,6)}", False, False),
                (" + ", False, False),
                (f"{_format_value(breakdown.sp,6)}", False, False),
                (" = ", False, False),
                (f"{_format_value(breakdown.total,6)} м", False, False),
            ]
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
        f"Полученное значение ψ={_format_value(psi, 3)} превышает 3.5. "
        f"Для поиска по таблицам берём граничное значение ψ={_format_value(psi_for_tables, 3)}, "
        "дальнейшая интерполяция автоматически прижимает аргумент к верхней границе сетки."
    )
    if psi == psi_clamped:
        clamping_note = "ψ находится в допустимом диапазоне 0…3.5, корректировка не требуется."

    paragraphs: list[str] = []
    paragraphs.append(_p("Отчёт по расчёту глубины оттаивания", style="Heading1"))
    paragraphs.append(_p(f"Дата: {_dt.datetime.now().strftime('%d.%m.%Y %H:%M')}"))
    paragraphs.append(
        _p_runs(
            [
                ("Форма фундамента: ", False, False),
                (foundation_shape, False, False),
                ("; ", False, False),
                ("L", True, False),
                (f"={_format_value(L, 3)} м; ", False, False),
                ("B", True, False),
                (f"={_format_value(B, 3)} м", False, False),
            ]
        )
    )

    paragraphs.append(_p("Исходные параметры:"))
    paragraphs.append(
        _p_runs(
            [
                ("λ", False, False),
                ("th", True, True),
                (" — теплопроводность талого грунта = ", False, False),
                (f"{_format_value(parameters['lambdath'], 6)} Вт/(м·°С)", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("λ", False, False),
                ("f", True, True),
                (" — теплопроводность мёрзлого грунта = ", False, False),
                (f"{_format_value(parameters['lambdaf'], 6)} Вт/(м·°С)", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("R", True, False),
                ("0", False, True),
                (" — сопротивление теплопередаче пола = ", False, False),
                (f"{_format_value(parameters['R0'], 6)} м²·°С/Вт", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("T", True, False),
                ("0", False, True),
                (" — среднегодовая температура многолетнемёрзлых грунтов = ", False, False),
                (f"{_format_value(parameters['T0'], 3)} °С", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("T", True, False),
                ("bf", True, True),
                (" — температура начала замерзания грунта = ", False, False),
                (f"{_format_value(parameters['Tbf'], 3)} °С", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("T", True, False),
                ("in", True, True),
                (" — расчётная температура воздуха внутри сооружения = ", False, False),
                (f"{_format_value(parameters['Tin'], 3)} °С", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("t", True, False),
                (" — длительность периода = ", False, False),
                (f"{_format_value(parameters['t'], 3)} с", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("L", True, False),
                ("v", True, True),
                (" — теплота таяния мёрзлого грунта = ", False, False),
                (f"{_format_value(parameters['Lv'], 3)} Дж/м³", False, False),
            ]
        )
    )

    paragraphs.append(_p("Промежуточные вычисления параметров:"))
    paragraphs.append(
        _p_runs(
            [
                ("α", False, False),
                ("r", True, True),
                (" = ", False, False),
                ("λ", False, False),
                ("th", True, True),
                (" · ", False, False),
                ("R", True, False),
                ("0", False, True),
                (" / ", False, False),
                ("B", True, False),
                (" = ", False, False),
                (f"{_format_value(parameters['lambdath'], 3)} · {_format_value(parameters['R0'], 3)} / {_format_value(B, 3)} = ", False, False),
                (f"{_format_value(alpha_r, 6)}", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("β", False, False),
                (" = −", False, False),
                ("λ", False, False),
                ("f", True, True),
                (" · (", False, False),
                ("T", True, False),
                ("0", False, True),
                (" − ", False, False),
                ("T", True, False),
                ("bf", True, True),
                (") / (", False, False),
                ("λ", False, False),
                ("th", True, True),
                (" · (", False, False),
                ("T", True, False),
                ("in", True, True),
                (" − ", False, False),
                ("T", True, False),
                ("bf", True, True),
                (")) = ", False, False),
                (f"−{_format_value(parameters['lambdaf'], 3)} · ({_format_value(parameters['T0'], 3)} − {_format_value(parameters['Tbf'], 3)}) / (", False, False),
                (f"{_format_value(parameters['lambdath'], 3)} · ({_format_value(parameters['Tin'], 3)} − {_format_value(parameters['Tbf'], 3)})) = {_format_value(beta, 6)}", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("ψ", False, False),
                (" = ", False, False),
                ("λ", False, False),
                ("th", True, True),
                (" · ", False, False),
                ("T", True, False),
                ("in", True, True),
                (" · ", False, False),
                ("t", True, False),
                (" / (", False, False),
                ("L", True, False),
                ("v", True, True),
                (" · ", False, False),
                ("B", True, False),
                ("2", False, True),
                (") = ", False, False),
                (f"{_format_value(parameters['lambdath'], 3)} · {_format_value(parameters['Tin'], 3)} · {_format_value(parameters['t'], 3)} / (", False, False),
                (f"{_format_value(parameters['Lv'], 3)} · {_format_value(B, 3)}²) = {_format_value(psi, 6)}", False, False),
            ]
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
        psi_kn_note = _p_runs(
            [
                ("Коэффициент ", False, False),
                ("k", True, False),
                ("n", True, True),
                ("=", False, False),
                (f"{_format_value(kn_value, 6)} получен из раздела таблицы К.1 для круглого фундамента: ", False, False),
                ("использованы ψ=", False, False),
                (f"{_format_value(psi_for_tables, 3)} и β={_format_value(beta, 3)}, поиск выполнен ", False, False),
                ("с интерполяцией по обоим параметрам и прижиманием аргументов к диапазону 0…2.", False, False),
            ]
        )
    else:
        ratio = float(L) / float(B)
        nearest_ratio = 1.0 if abs(ratio - 1.0) <= abs(ratio - 2.0) else 2.0
        psi_kn_note = _p_runs(
            [
                ("Коэффициент ", False, False),
                ("k", True, False),
                ("n", True, True),
                ("=", False, False),
                (f"{_format_value(kn_value, 6)} получен из раздела таблицы К.1 для прямоугольного ", False, False),
                ("фундамента: фактическое отношение ", False, False),
                ("L", True, False),
                ("/", False, False),
                ("B", True, False),
                ("=", False, False),
                (f"{_format_value(ratio, 3)}", False, False),
                (", выбрана часть таблицы с ", False, False),
                ("L", True, False),
                ("/", False, False),
                ("B", True, False),
                ("=", False, False),
                (f"{nearest_ratio:.1f}", False, False),
                (". Значение определено по ψ=", False, False),
                (f"{_format_value(psi_for_tables, 3)}", False, False),
                (" и β=", False, False),
                (f"{_format_value(beta, 3)}", False, False),
                (" с интерполяцией и прижиманием аргументов к диапазону 0…2.", False, False),
            ]
        )
    paragraphs.append(psi_kn_note)

    paragraphs.append(
        _p_runs(
            [
                ("По графикам ", False, False),
                ("k", True, False),
                ("c", True, True),
                ("(ψ, α", False, False),
                ("r", True, True),
                (") при ψ=", False, False),
                (f"{_format_value(psi_for_tables, 3)}", False, False),
                (" и α", False, False),
                ("r", True, True),
                ("=", False, False),
                (f"{_format_value(alpha_r, 3)} ", False, False),
                ("принято ", False, False),
                ("k", True, False),
                ("c", True, True),
                ("=", False, False),
                (f"{_format_value(kc_value, 6)}", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("По графикам ", False, False),
                ("k", True, False),
                ("e", True, True),
                ("(ψ, α", False, False),
                ("r", True, True),
                (") при ψ=", False, False),
                (f"{_format_value(psi_for_tables, 3)}", False, False),
                (" и α", False, False),
                ("r", True, True),
                ("=", False, False),
                (f"{_format_value(alpha_r, 3)} ", False, False),
                ("принято ", False, False),
                ("k", True, False),
                ("e", True, True),
                ("=", False, False),
                (f"{_format_value(ke_value, 6)}", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("По графикам ξ", False, False),
                ("c", True, True),
                ("(ψ, β) при ψ=", False, False),
                (f"{_format_value(psi_for_tables, 3)}", False, False),
                (" и β=", False, False),
                (f"{_format_value(beta, 3)} ", False, False),
                ("принято ξ", False, False),
                ("c", True, True),
                ("=", False, False),
                (f"{_format_value(xi_c, 6)}", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("По графикам ξ", False, False),
                ("e", True, True),
                ("(ψ, β) при ψ=", False, False),
                (f"{_format_value(psi_for_tables, 3)}", False, False),
                (" и β=", False, False),
                (f"{_format_value(beta, 3)} ", False, False),
                ("принято ξ", False, False),
                ("e", True, True),
                ("=", False, False),
                (f"{_format_value(xi_e, 6)}", False, False),
            ]
        )
    )

    paragraphs.append(
        _p_runs(
            [
                ("Расчёт глубины в центре: ", False, False),
                ("H", True, False),
                ("c", True, True),
                (" = ", False, False),
                ("k", True, False),
                ("n", True, True),
                (" · (ξ", False, False),
                ("c", True, True),
                (" − k", False, False),
                ("c", True, True),
                (") · ", False, False),
                ("B", True, False),
                (" = ", False, False),
                (f"{_format_value(kn_value, 6)} · ({_format_value(xi_c, 6)} − {_format_value(kc_value, 6)}) · {_format_value(B, 3)} = {_format_value(hc, 6)} м", False, False),
            ]
        )
    )
    paragraphs.append(
        _p_runs(
            [
                ("Расчёт глубины у края: ", False, False),
                ("H", True, False),
                ("e", True, True),
                (" = ", False, False),
                ("k", True, False),
                ("n", True, True),
                (" · (ξ", False, False),
                ("e", True, True),
                (" − k", False, False),
                ("e", True, True),
                (" − 0.18·β·√ψ) · ", False, False),
                ("B", True, False),
                (" = ", False, False),
                (f"{_format_value(kn_value, 6)} · ({_format_value(xi_e, 6)} − {_format_value(ke_value, 6)} − 0.18·{_format_value(beta, 6)}·√{_format_value(psi, 6)}) · {_format_value(B, 3)} = {_format_value(he, 6)} м", False, False),
            ]
        )
    )

    paragraphs.append(
        _p_runs(
            [
                ("Глубина оттаивания под центром ", False, False),
                ("H", True, False),
                ("c", True, True),
                ("=", False, False),
                (f"{_format_value(hc, 6)} м; глубина оттаивания под краем ", False, False),
                ("H", True, False),
                ("e", True, True),
                ("=", False, False),
                (f"{_format_value(he, 6)} м", False, False),
            ]
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
        _p_runs(
            [
                ("Исходные данные: ", False, False),
                ("H", True, False),
                ("=", False, False),
                (f"{_format_value(params['H'],3)} м; ", False, False),
                ("F", True, False),
                ("=", False, False),
                (f"{_format_value(params['F'],3)} кН; ", False, False),
                ("L", True, False),
                ("=", False, False),
                (f"{_format_value(params['L'],3)} м; ", False, False),
                ("B", True, False),
                ("=", False, False),
                (f"{_format_value(params['B'],3)} м; ", False, False),
                ("H", True, False),
                ("c", True, True),
                ("=", False, False),
                (f"{_format_value(params['Hc'],3)} м; ", False, False),
                ("H", True, False),
                ("e", True, True),
                ("=", False, False),
                (f"{_format_value(params['He'],3)} м", False, False),
            ]
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
