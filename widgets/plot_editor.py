"""Tkinter-панель для интерактивной настройки линий графика.

Виджет повторяет возможности Qt-версии и дополняет их отдельной панелью
фильтрации точек.  Для каждой кривой отображаются элементы управления
цветом, типом линии и толщиной, а также пара ползунков «до» и «от»,
расположенных на одной линии.  Ползунки позволяют ограничить диапазон
данных без повторного чтения файлов: исходные точки сохраняются в объекте
линии и переиспользуются при перемещении бегунков.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import tkinter as tk
from tkinter import ttk, colorchooser

from color_palettes import PALETTES
from .range_line import RangeLine
from .text_widget import create_text


@dataclass
class _RowWidgets:
    """Хранит элементы управления, связанные с одной кривой."""

    frame: ttk.Frame
    label: ttk.Label
    colour: tk.Label
    style: ttk.Combobox
    width: ttk.Scale


@dataclass
class _RangeWidgets:
    """Набор виджетов панели диапазона для одной кривой."""

    frame: ttk.Frame
    slider: RangeLine
    upper_value: tk.StringVar
    lower_value: tk.StringVar
    upper_label: ttk.Label
    lower_label: ttk.Label
    manual_lower: tk.StringVar
    manual_upper: tk.StringVar
    manual_lower_entry: tk.Entry
    manual_upper_entry: tk.Entry
    line: object
    index: int


class PlotEditor(ttk.Frame):
    """Компактная панель с настройками внешнего вида и диапазона кривых."""

    def __init__(
        self,
        parent: tk.Widget,
        ax,
        canvas,
        saved_data: Optional[List[dict]] = None,
    ) -> None:
        super().__init__(parent)
        self.ax = ax
        self.canvas = canvas
        self.saved_data = saved_data if saved_data is not None else []
        self._rows: List[_RowWidgets] = []
        self._range_controls: List[_RangeWidgets] = []
        self._cached_height = 0
        self._fixed_limits: Optional[
            tuple[tuple[float, float], tuple[float, float]]
        ] = None
        self.fix_axes_var = tk.BooleanVar(value=False)

        self._line_styles = ["-", "--", "-.", ":"]
        self._style_box_width = max(len(style) for style in self._line_styles) + 2

        self.palette_combo = ttk.Combobox(
            self, values=list(PALETTES.keys()), state="readonly"
        )
        self.palette_combo.current(0)
        self.palette_combo.pack(fill=tk.X, pady=2)
        self.palette_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self.apply_selected_palette()
        )

        self.row_container = ttk.Frame(self)
        self.row_container.pack(fill=tk.X, expand=False)

        self.separator = ttk.Separator(self, orient=tk.HORIZONTAL)
        self.range_container = ttk.Frame(self)

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Перестраивает панели на основе текущих линий осей."""

        for row in self._rows:
            row.frame.destroy()
        self._rows.clear()

        for controls in self._range_controls:
            controls.frame.destroy()
        self._range_controls.clear()

        for child in self.range_container.winfo_children():
            child.destroy()
        self.separator.pack_forget()
        self.range_container.pack_forget()

        lines = list(self.ax.lines)
        for idx, line in enumerate(lines, start=1):
            self._append_row(line, idx)

        if lines:
            self.separator.pack(fill=tk.X, pady=(6, 4))
            self.range_container.pack(fill=tk.X, pady=(0, 0))
            self._build_range_controls(lines)

        self.apply_selected_palette()
        self._update_size_hint()

    # ------------------------------------------------------------------
    def _update_size_hint(self) -> None:
        """Запоминает требуемую высоту редактора после перестройки."""

        self.update_idletasks()
        self._cached_height = max(self.winfo_reqheight(), 1)

    @property
    def required_height(self) -> int:
        """Возвращает актуальную высоту, необходимую для отображения всех элементов."""

        if self._cached_height:
            return self._cached_height
        self.update_idletasks()
        return max(self.winfo_reqheight(), 1)

    # ------------------------------------------------------------------
    def _append_row(self, line, index: int) -> None:
        row_frame = ttk.Frame(self.row_container)
        row_frame.pack(fill=tk.X, pady=2)

        name_lbl = ttk.Label(row_frame, text=f"Кривая {index}")
        name_lbl.pack(side=tk.LEFT, padx=5)

        colour_lbl = tk.Label(row_frame, bg=line.get_color(), width=4)
        colour_lbl.pack(side=tk.LEFT, padx=5)
        colour_lbl.bind(
            "<Button-1>", lambda _e, ln=line, lbl=colour_lbl: self._choose_colour(ln, lbl)
        )

        style_box = ttk.Combobox(
            row_frame,
            values=self._line_styles,
            width=self._style_box_width,
        )
        style_box.set(line.get_linestyle())
        style_box.pack(side=tk.LEFT, padx=5)
        style_box.bind(
            "<<ComboboxSelected>>",
            lambda _e, ln=line, box=style_box: self._update_style(ln, box.get()),
        )

        width_scale = ttk.Scale(row_frame, from_=1, to=10, orient=tk.HORIZONTAL)
        width_scale.set(line.get_linewidth())
        width_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        width_scale.configure(
            command=lambda v, ln=line: self._update_width(ln, float(v))
        )

        self._rows.append(
            _RowWidgets(row_frame, name_lbl, colour_lbl, style_box, width_scale)
        )

    # ------------------------------------------------------------------
    def _build_range_controls(self, lines: List) -> None:
        header_frame = ttk.Frame(self.range_container)
        header_frame.pack(fill=tk.X, padx=5)

        header = ttk.Label(header_frame, text="Диапазон точек, %")
        header.pack(side=tk.LEFT)

        fix_axes = ttk.Checkbutton(
            header_frame,
            text="Фиксировать оси",
            variable=self.fix_axes_var,
            command=self._on_fix_axes_toggle,
        )
        fix_axes.pack(side=tk.RIGHT)

        for idx, line in enumerate(lines, start=1):
            self._append_range_row(line, idx)

    def _append_range_row(self, line, index: int) -> None:
        frame = ttk.Frame(self.range_container)
        frame.pack(fill=tk.X, padx=5, pady=6)

        title = ttk.Label(frame, text=f"Кривая {index}")
        title.pack(side=tk.LEFT, padx=(0, 10))

        slider_holder = ttk.Frame(frame)
        slider_holder.pack(side=tk.LEFT, fill=tk.X, expand=True)

        scales_frame = ttk.Frame(slider_holder)
        scales_frame.pack(fill=tk.X)

        start_val, end_val = self._initial_range_values(line, index)

        slider = RangeLine(
            scales_frame,
            from_=0,
            to=100,
            start=start_val,
            end=end_val,
            width=360,
        )
        slider.pack(fill=tk.X, expand=True)

        values_frame = ttk.Frame(frame)
        values_frame.pack(side=tk.RIGHT, padx=(10, 0))

        upper_value = tk.StringVar()
        lower_value = tk.StringVar()
        upper_label = ttk.Label(values_frame, textvariable=upper_value)
        lower_label = ttk.Label(values_frame, textvariable=lower_value)
        upper_label.pack(anchor="e")
        lower_label.pack(anchor="e")

        manual_frame = ttk.Frame(values_frame)
        manual_frame.pack(anchor="e", pady=(6, 0))

        manual_lower = tk.StringVar()
        manual_upper = tk.StringVar()

        lower_caption = ttk.Label(manual_frame, text="X от:")
        lower_caption.grid(row=0, column=0, sticky="e", padx=(0, 4))
        manual_lower_entry = create_text(manual_frame, method="entry")
        manual_lower_entry.configure(width=12, textvariable=manual_lower)
        manual_lower_entry.grid(row=0, column=1, sticky="ew")

        upper_caption = ttk.Label(manual_frame, text="X до:")
        upper_caption.grid(row=1, column=0, sticky="e", padx=(0, 4), pady=(4, 0))
        manual_upper_entry = create_text(manual_frame, method="entry")
        manual_upper_entry.configure(width=12, textvariable=manual_upper)
        manual_upper_entry.grid(row=1, column=1, sticky="ew", pady=(4, 0))

        manual_frame.columnconfigure(1, weight=1)

        controls = _RangeWidgets(
            frame,
            slider,
            upper_value,
            lower_value,
            upper_label,
            lower_label,
            manual_lower,
            manual_upper,
            manual_lower_entry,
            manual_upper_entry,
            line,
            index,
        )
        self._range_controls.append(controls)

        slider.command = (
            lambda lower, upper, ctrl=controls: self._on_range_change(
                ctrl, lower, upper
            )
        )

        manual_lower_entry.bind(
            "<FocusOut>",
            lambda _e, ctrl=controls: self._on_manual_range_change(ctrl),
        )
        manual_lower_entry.bind(
            "<Return>",
            lambda _e, ctrl=controls: self._on_manual_range_change(ctrl),
        )
        manual_upper_entry.bind(
            "<FocusOut>",
            lambda _e, ctrl=controls: self._on_manual_range_change(ctrl),
        )
        manual_upper_entry.bind(
            "<Return>",
            lambda _e, ctrl=controls: self._on_manual_range_change(ctrl),
        )

        self._apply_range(controls)

    # ------------------------------------------------------------------
    def _coerce_percentage(self, value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _initial_range_values(self, line, index: int) -> tuple[float, float]:
        start = getattr(line, "_slider_start", None)
        end = getattr(line, "_slider_end", None)
        if start is None or end is None:
            if len(self.saved_data) >= index:
                saved = self.saved_data[index - 1]
                start = self._coerce_percentage(saved.get("slider_start"), 0.0)
                end = self._coerce_percentage(saved.get("slider_end"), 100.0)
            else:
                start, end = 0.0, 100.0
        start = max(0.0, min(100.0, float(start)))
        end = max(0.0, min(100.0, float(end)))
        if end < start:
            start, end = end, start
        return start, end

    def _update_range_labels(
        self,
        controls: _RangeWidgets,
        lower: Optional[float] = None,
        upper: Optional[float] = None,
    ) -> None:
        if lower is None or upper is None:
            lower, upper = controls.slider.get()
        controls.upper_value.set(f"До: {upper:.2f}%")
        controls.lower_value.set(f"От: {lower:.2f}%")

    def _on_range_change(
        self, controls: _RangeWidgets, lower: float, upper: float
    ) -> None:
        self._apply_range(controls, lower, upper)

    def _apply_range(
        self,
        controls: _RangeWidgets,
        lower: Optional[float] = None,
        upper: Optional[float] = None,
    ) -> None:
        if lower is None or upper is None:
            lower, upper = controls.slider.get()
        else:
            controls.slider.set(lower=lower, upper=upper, notify=False)
        self._update_range_labels(controls, lower, upper)
        self._update_saved_data(controls.index, lower, upper)
        self._update_line_range(controls.line, lower, upper)
        self._update_manual_inputs(controls)

    def _update_saved_data(self, index: int, start: float, end: float) -> None:
        if len(self.saved_data) >= index:
            self.saved_data[index - 1]["slider_start"] = start
            self.saved_data[index - 1]["slider_end"] = end

    def _update_line_range(self, line, start: float, end: float) -> None:
        full_x = getattr(line, "_full_x", None)
        full_y = getattr(line, "_full_y", None)
        if not full_x or not full_y:
            return
        if len(full_x) != len(full_y):
            return
        if len(full_x) <= 1:
            line.set_data(full_x, full_y)
        else:
            max_index = len(full_x) - 1
            start_idx = int(round(max_index * start / 100))
            end_idx = int(round(max_index * end / 100))
            if end_idx < start_idx:
                start_idx, end_idx = end_idx, start_idx
            start_idx = max(0, min(start_idx, max_index))
            end_idx = max(start_idx, min(end_idx, max_index))
            new_x = full_x[start_idx : end_idx + 1]
            new_y = full_y[start_idx : end_idx + 1]
            if not new_x or not new_y:
                return
            line.set_data(new_x, new_y)
        setattr(line, "_slider_start", start)
        setattr(line, "_slider_end", end)
        self._update_axes_limits()
        self._redraw_canvas()

    def _update_manual_inputs(self, controls: _RangeWidgets) -> None:
        x_data = list(controls.line.get_xdata())
        if not x_data:
            controls.manual_lower.set("")
            controls.manual_upper.set("")
            return
        controls.manual_lower.set(self._format_x_value(x_data[0]))
        controls.manual_upper.set(self._format_x_value(x_data[-1]))

    def _format_x_value(self, value: float) -> str:
        return f"{value:.6g}"

    def _on_manual_range_change(self, controls: _RangeWidgets) -> None:
        text_lower = controls.manual_lower.get().strip()
        text_upper = controls.manual_upper.get().strip()
        try:
            lower_val = float(text_lower)
            upper_val = float(text_upper)
        except ValueError:
            self._update_manual_inputs(controls)
            return
        if lower_val > upper_val:
            lower_val, upper_val = upper_val, lower_val
        percentages = self._manual_values_to_percentages(controls, lower_val, upper_val)
        if percentages is None:
            self._update_manual_inputs(controls)
            return
        lower_percent, upper_percent = percentages
        self._apply_range(controls, lower_percent, upper_percent)

    def _manual_values_to_percentages(
        self, controls: _RangeWidgets, lower_val: float, upper_val: float
    ) -> Optional[tuple[float, float]]:
        full_x = getattr(controls.line, "_full_x", None)
        if not full_x:
            full_x = list(controls.line.get_xdata())
        if not full_x:
            return None
        if len(full_x) == 1:
            return 0.0, 100.0
        max_index = len(full_x) - 1
        start_idx = 0
        for idx, value in enumerate(full_x):
            if value >= lower_val:
                start_idx = idx
                break
        else:
            start_idx = max_index
        end_idx = max_index
        for idx in range(max_index, -1, -1):
            if full_x[idx] <= upper_val:
                end_idx = idx
                break
        if end_idx < start_idx:
            end_idx = start_idx
        lower_percent = start_idx * 100.0 / max_index
        upper_percent = end_idx * 100.0 / max_index
        return lower_percent, upper_percent

    # ------------------------------------------------------------------
    def _refresh_legend(self) -> None:
        legend = self.ax.get_legend()
        if legend:
            title = legend.get_title().get_text()
            self.ax.legend(title=title)
        self._redraw_canvas()

    def apply_palette(self, palette_name: str) -> None:
        colors = PALETTES.get(palette_name, [])
        for line, color, row in zip(self.ax.lines, colors, self._rows):
            line.set_color(color)
            row.colour.config(bg=color)
        self._refresh_legend()

    def apply_selected_palette(self) -> None:
        self.apply_palette(self.palette_combo.get())

    # ------------------------------------------------------------------
    def _choose_colour(self, line, label: tk.Label) -> None:
        colour_code = colorchooser.askcolor(color=line.get_color())[1]
        if colour_code:
            line.set_color(colour_code)
            label.config(bg=colour_code)
            self._refresh_legend()

    def _update_style(self, line, style: str) -> None:
        line.set_linestyle(style)
        self._refresh_legend()

    def _update_width(self, line, width: float) -> None:
        line.set_linewidth(width)
        self._redraw_canvas()

    # ------------------------------------------------------------------
    def _on_fix_axes_toggle(self) -> None:
        self._apply_axes_fix_state()

    def _apply_axes_fix_state(self) -> None:
        if self.fix_axes_var.get():
            self._fixed_limits = (self.ax.get_xlim(), self.ax.get_ylim())
            self._apply_fixed_limits()
        else:
            self._fixed_limits = None
            self._autoscale_axes()
        self._redraw_canvas()

    def reset_ranges(self) -> None:
        """Возвращает все ползунки диапазона к значениям 0–100%."""

        for controls in self._range_controls:
            self._apply_range(controls, 0.0, 100.0)

    def reset_axes_lock(self) -> None:
        """Сбрасывает фиксацию осей и возвращает автоматическое масштабирование."""

        self.fix_axes_var.set(False)
        self._apply_axes_fix_state()

    def _apply_fixed_limits(self) -> None:
        if self._fixed_limits is None:
            return
        if hasattr(self.ax, "set_autoscale_on"):
            self.ax.set_autoscale_on(False)
        xlim, ylim = self._fixed_limits
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)

    def _autoscale_axes(self) -> None:
        if hasattr(self.ax, "set_autoscale_on"):
            self.ax.set_autoscale_on(True)
        if hasattr(self.ax, "relim") and hasattr(self.ax, "autoscale_view"):
            self.ax.relim()
            self.ax.autoscale_view()

    def _update_axes_limits(self) -> None:
        if self.fix_axes_var.get():
            if self._fixed_limits is None:
                self._fixed_limits = (self.ax.get_xlim(), self.ax.get_ylim())
            self._apply_fixed_limits()
        else:
            self._fixed_limits = None
            self._autoscale_axes()

    def _redraw_canvas(self) -> None:
        if hasattr(self.canvas, "draw_idle"):
            self.canvas.draw_idle()
        else:
            self.canvas.draw()
