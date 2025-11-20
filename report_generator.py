from __future__ import annotations

import datetime as _dt
import math
import zipfile
from pathlib import Path
from typing import Iterable, Sequence
from xml.sax.saxutils import escape

from II_calculations import SettlementBreakdown, LoadSettlementStep, ThawSettlementStep


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
            f"a={_format_value(params['a'],3)} м; b={_format_value(params['b'],3)} м; "
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
