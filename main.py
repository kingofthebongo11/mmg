from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

from borehole_class import Borehole
from grunt_class import PermafrostSoil, SoilType
from II_calculations import disp_calculation
from widgets import create_text, show_error


class ParameterInput:
    """Виджет для ввода числового параметра с выпадающим списком единиц измерения."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        label: str,
        default: float,
        units: Sequence[Tuple[str, float]],
    ) -> None:
        self._units_map: Dict[str, float] = {name: factor for name, factor in units}
        self.var = tk.StringVar(value=str(default))
        self.unit_var = tk.StringVar(value=units[0][0])

        frame = ttk.Frame(parent)
        frame.grid_columnconfigure(1, weight=1)

        self.label_widget = ttk.Label(frame, text=label)
        self.entry = create_text(frame, method="entry")
        self.entry.configure(textvariable=self.var)
        self.units_widget = ttk.Combobox(
            frame,
            values=[u[0] for u in units],
            textvariable=self.unit_var,
            state="readonly",
            width=8,
        )

        self.label_widget.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.entry.grid(row=0, column=1, sticky="we")
        self.units_widget.grid(row=0, column=2, sticky="e", padx=(8, 0))

        self.container = frame

    def grid(self, **kwargs) -> None:
        self.container.grid(**kwargs)

    def get_value(self) -> float:
        raw = self.var.get().strip()
        if not raw:
            raise ValueError("Поле не должно быть пустым")
        try:
            value = float(raw.replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"Не удалось преобразовать '{raw}' в число") from exc
        unit_name = self.unit_var.get()
        factor = self._units_map.get(unit_name)
        if factor is None:
            raise ValueError(f"Неизвестная размерность: {unit_name}")
        return value * factor


class SoilManager:
    """Хранилище введённых грунтов."""

    def __init__(self) -> None:
        self._soils: Dict[str, PermafrostSoil] = {}
        self._listeners: List[Callable[[], None]] = []

    def add_listener(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def _notify(self) -> None:
        for callback in list(self._listeners):
            callback()

    def add(self, soil: PermafrostSoil) -> None:
        self._soils[soil.code] = soil
        self._notify()

    def remove(self, code: str) -> None:
        if code in self._soils:
            del self._soils[code]
            self._notify()

    def get(self, code: str) -> PermafrostSoil:
        return self._soils[code]

    def items(self) -> Iterable[PermafrostSoil]:
        return self._soils.values()

    def choices(self) -> Tuple[List[str], Dict[str, str]]:
        labels = []
        mapping: Dict[str, str] = {}
        for soil in self._soils.values():
            label = f"{soil.code} — {soil.name}"
            labels.append(label)
            mapping[label] = soil.code
        return labels, mapping


class LayerRow:
    """Строка таблицы слоёв скважины."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        get_choices: Callable[[], Tuple[List[str], Dict[str, str]]],
        on_remove: Callable[["LayerRow"], None],
    ) -> None:
        self._get_choices = get_choices
        self._on_remove = on_remove

        self.var_soil = tk.StringVar()
        self.var_thickness = tk.StringVar()

        self.frame = ttk.Frame(parent)
        self.frame.grid_columnconfigure(0, weight=1)

        self.cmb_soil = ttk.Combobox(
            self.frame,
            textvariable=self.var_soil,
            state="readonly",
        )
        self.entry_thickness = create_text(self.frame, method="entry")
        self.entry_thickness.configure(textvariable=self.var_thickness, width=10)
        self.btn_remove = ttk.Button(self.frame, text="Удалить", command=self._handle_remove)

        self.cmb_soil.grid(row=0, column=0, sticky="we")
        self.entry_thickness.grid(row=0, column=1, padx=8)
        self.btn_remove.grid(row=0, column=2)

        self.update_choices()

    def grid(self, row: int) -> None:
        self.frame.grid(row=row, column=0, sticky="we", pady=2)

    def destroy(self) -> None:
        self.frame.destroy()

    def update_choices(self) -> None:
        labels, _ = self._get_choices()
        self.cmb_soil["values"] = labels
        if labels and not self.var_soil.get():
            self.var_soil.set(labels[0])

    def _handle_remove(self) -> None:
        self._on_remove(self)

    def set_values(self, soil_label: str, thickness: float) -> None:
        self.var_soil.set(soil_label)
        self.var_thickness.set(str(thickness))

    def get_data(self) -> Tuple[str, float]:
        labels, mapping = self._get_choices()
        selected = self.var_soil.get()
        if selected not in mapping:
            raise ValueError("Не выбран грунт для слоя")
        raw_thickness = self.var_thickness.get().strip()
        if not raw_thickness:
            raise ValueError("Толщина слоя не задана")
        try:
            thickness = float(raw_thickness.replace(",", "."))
        except ValueError as exc:
            raise ValueError("Некорректное значение толщины слоя") from exc
        if thickness <= 0:
            raise ValueError("Толщина слоя должна быть больше нуля")
        return mapping[selected], thickness


class SoilDialog:
    """Окно для управления справочником грунтов."""

    def __init__(self, parent: tk.Tk, manager: SoilManager) -> None:
        self._manager = manager
        self.window = tk.Toplevel(parent)
        self.window.title("Справочник грунтов")
        self.window.grab_set()

        form = ttk.LabelFrame(self.window, text="Новый грунт")
        form.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        self.var_code = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_soil_type = tk.StringVar(value=list(SoilType)[0].name)
        self.var_rho = tk.StringVar()
        self.var_Ath = tk.StringVar()
        self.var_mth = tk.StringVar()

        ttk.Label(form, text="Код").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
        entry_code = create_text(form, method="entry")
        entry_code.configure(textvariable=self.var_code, width=12)
        entry_code.grid(row=0, column=1, sticky="we", pady=2)

        ttk.Label(form, text="Название").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=2)
        entry_name = create_text(form, method="entry")
        entry_name.configure(textvariable=self.var_name)
        entry_name.grid(row=1, column=1, sticky="we", pady=2)

        ttk.Label(form, text="Тип грунта").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=2)
        self.cmb_soil_type = ttk.Combobox(
            form,
            values=[st.name for st in SoilType],
            textvariable=self.var_soil_type,
            state="readonly",
        )
        self.cmb_soil_type.grid(row=2, column=1, sticky="we", pady=2)

        ttk.Label(form, text="Плотность, кг/м³").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=2)
        entry_rho = create_text(form, method="entry")
        entry_rho.configure(textvariable=self.var_rho)
        entry_rho.grid(row=3, column=1, sticky="we", pady=2)

        ttk.Label(form, text="Ath").grid(row=4, column=0, sticky="w", padx=(0, 8), pady=2)
        entry_Ath = create_text(form, method="entry")
        entry_Ath.configure(textvariable=self.var_Ath)
        entry_Ath.grid(row=4, column=1, sticky="we", pady=2)

        ttk.Label(form, text="mth, кПа⁻¹").grid(row=5, column=0, sticky="w", padx=(0, 8), pady=2)
        entry_mth = create_text(form, method="entry")
        entry_mth.configure(textvariable=self.var_mth)
        entry_mth.grid(row=5, column=1, sticky="we", pady=2)

        ttk.Button(form, text="Добавить", command=self._add_soil).grid(
            row=6, column=0, columnspan=2, pady=(8, 0)
        )

        columns = ("code", "name", "type", "rho", "Ath", "mth")
        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=8)
        headings = {
            "code": "Код",
            "name": "Название",
            "type": "Тип",
            "rho": "ρ, кг/м³",
            "Ath": "Ath",
            "mth": "mth, кПа⁻¹",
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=100, anchor="center")
        self.tree.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="nsew")

        ttk.Button(self.window, text="Удалить выбранный", command=self._remove_selected).grid(
            row=2, column=0, padx=12, pady=(0, 12), sticky="e"
        )

        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=1)

        self._refresh_tree()

    def _parse_float(self, value: str, *, allow_none: bool = False) -> float | None:
        value = value.strip()
        if not value:
            if allow_none:
                return None
            raise ValueError("Значение не может быть пустым")
        try:
            return float(value.replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"Не удалось преобразовать '{value}' в число") from exc

    def _add_soil(self) -> None:
        code = self.var_code.get().strip()
        name = self.var_name.get().strip()
        rho = self._parse_float(self.var_rho)
        Ath = self._parse_float(self.var_Ath, allow_none=True)
        mth = self._parse_float(self.var_mth, allow_none=True)
        if rho is None:
            raise AssertionError("rho не может быть None")
        soil_type_name = self.var_soil_type.get()
        try:
            soil_type = SoilType[soil_type_name]
        except KeyError:
            show_error("Ошибка", f"Неизвестный тип грунта: {soil_type_name}")
            return
        try:
            soil = PermafrostSoil(
                code=code,
                name=name,
                soil_type=soil_type,
                rho=rho,
                Ath=Ath,
                mth=mth,
            )
        except Exception as exc:
            show_error("Ошибка", str(exc))
            return
        self._manager.add(soil)
        self._refresh_tree()
        self.var_code.set("")
        self.var_name.set("")
        self.var_rho.set("")
        self.var_Ath.set("")
        self.var_mth.set("")

    def _remove_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        code = self.tree.set(item_id, "code")
        self._manager.remove(code)
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for soil in self._manager.items():
            self.tree.insert(
                "",
                "end",
                values=(
                    soil.code,
                    soil.name,
                    soil.soil_type.name,
                    soil.rho,
                    soil.Ath if soil.Ath is not None else "",
                    soil.mth if soil.mth is not None else "",
                ),
            )


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Расчёт осадки основания")

        self.soil_manager = SoilManager()
        self.soil_manager.add_listener(self._update_layer_choices)
        self.soil_dialog: SoilDialog | None = None

        main_frame = ttk.Frame(root, padding=12)
        main_frame.grid(row=0, column=0, sticky="nsew")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        params_frame = ttk.LabelFrame(main_frame, text="Исходные данные")
        params_frame.grid(row=0, column=0, sticky="nsew")

        self.inputs: Dict[str, ParameterInput] = {}
        self.inputs["Hc"] = ParameterInput(
            params_frame,
            label="Глубина оттаивания Hc",
            default=8.0,
            units=[("м", 1.0)],
        )
        self.inputs["F"] = ParameterInput(
            params_frame,
            label="Нагрузка F",
            default=6821.0,
            units=[("кН", 1.0)],
        )
        self.inputs["a"] = ParameterInput(
            params_frame,
            label="Размер a",
            default=10.0,
            units=[("м", 1.0)],
        )
        self.inputs["b"] = ParameterInput(
            params_frame,
            label="Размер b",
            default=1.9,
            units=[("м", 1.0)],
        )
        self.inputs["H"] = ParameterInput(
            params_frame,
            label="Отметка плиты H",
            default=98.0,
            units=[("м", 1.0)],
        )
        for idx, widget in enumerate(self.inputs.values()):
            widget.grid(row=idx, column=0, pady=4, sticky="we")

        borehole_frame = ttk.LabelFrame(main_frame, text="Скважина")
        borehole_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        borehole_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(borehole_frame, text="Название скважины").grid(row=0, column=0, sticky="w")
        self.var_borehole_code = tk.StringVar(value="BH-01")
        borehole_code_entry = create_text(borehole_frame, method="entry")
        borehole_code_entry.configure(textvariable=self.var_borehole_code)
        borehole_code_entry.grid(row=0, column=1, sticky="we", padx=(8, 0))

        ttk.Label(borehole_frame, text="Отметка устья, м").grid(row=1, column=0, sticky="w")
        self.var_borehole_top = tk.StringVar(value="100")
        borehole_top_entry = create_text(borehole_frame, method="entry")
        borehole_top_entry.configure(textvariable=self.var_borehole_top)
        borehole_top_entry.grid(row=1, column=1, sticky="we", padx=(8, 0))

        ttk.Button(
            borehole_frame,
            text="Справочник грунтов",
            command=self._open_soil_dialog,
        ).grid(row=0, column=2, rowspan=2, padx=(12, 0))

        layers_frame = ttk.LabelFrame(main_frame, text="Слои скважины")
        layers_frame.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        layers_frame.grid_columnconfigure(0, weight=1)

        header = ttk.Frame(layers_frame)
        header.grid(row=0, column=0, sticky="we")
        header.grid_columnconfigure(0, weight=1)
        ttk.Label(header, text="Грунт").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Толщина, м").grid(row=0, column=1, padx=8)

        self.layers_container = ttk.Frame(layers_frame)
        self.layers_container.grid(row=1, column=0, sticky="nsew")
        self.layers_container.grid_columnconfigure(0, weight=1)

        ttk.Button(layers_frame, text="Добавить слой", command=self._add_layer_row).grid(
            row=2, column=0, pady=(8, 0), sticky="w"
        )

        result_frame = ttk.Frame(main_frame)
        result_frame.grid(row=3, column=0, sticky="we", pady=(12, 0))
        ttk.Button(result_frame, text="Расчёт", command=self._calculate).grid(
            row=0, column=0, padx=(0, 12)
        )
        ttk.Label(result_frame, text="Результат, м").grid(row=0, column=1)
        self.result_var = tk.StringVar()
        result_entry = create_text(result_frame, method="entry", state="readonly")
        result_entry.configure(textvariable=self.result_var, width=20)
        result_entry.grid(row=0, column=2)

        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        self.layer_rows: List[LayerRow] = []

        self._populate_defaults()

    def _populate_defaults(self) -> None:
        default_soils = [
            PermafrostSoil(
                code="L1",
                name="Loam",
                soil_type=SoilType.SAND_AND_SUPES,
                rho=1700,
                Ath=0.01,
                mth=0.0000306,
            ),
            PermafrostSoil(
                code="L2",
                name="Loam",
                soil_type=SoilType.LOAM,
                rho=1800,
                Ath=0.016,
                mth=0.000051,
            ),
        ]
        for soil in default_soils:
            self.soil_manager.add(soil)

        self._add_layer_row()
        self._add_layer_row()

        labels, _ = self.soil_manager.choices()
        if labels:
            if len(self.layer_rows) >= 1:
                self.layer_rows[0].set_values(labels[0], 5.0)
            if len(self.layer_rows) >= 2 and len(labels) > 1:
                self.layer_rows[1].set_values(labels[1], 10.0)

    def _add_layer_row(self) -> None:
        row = LayerRow(
            self.layers_container,
            get_choices=self.soil_manager.choices,
            on_remove=self._remove_layer_row,
        )
        self.layer_rows.append(row)
        self._regrid_layers()

    def _remove_layer_row(self, row: LayerRow) -> None:
        if row in self.layer_rows:
            self.layer_rows.remove(row)
            row.destroy()
            self._regrid_layers()

    def _regrid_layers(self) -> None:
        for idx, row in enumerate(self.layer_rows):
            row.grid(row=idx)

    def _update_layer_choices(self) -> None:
        for row in self.layer_rows:
            row.update_choices()

    def _open_soil_dialog(self) -> None:
        if self.soil_dialog is not None and tk.Toplevel.winfo_exists(self.soil_dialog.window):
            self.soil_dialog.window.lift()
            return
        self.soil_dialog = SoilDialog(self.root, self.soil_manager)

    def _parse_float(self, value: str, *, allow_empty: bool = False) -> float:
        value = value.strip()
        if not value:
            if allow_empty:
                return 0.0
            raise ValueError("Поле не должно быть пустым")
        try:
            return float(value.replace(",", "."))
        except ValueError as exc:
            raise ValueError("Ожидалось числовое значение") from exc

    def _calculate(self) -> None:
        try:
            params = {name: widget.get_value() for name, widget in self.inputs.items()}
            borehole_code = self.var_borehole_code.get().strip()
            if not borehole_code:
                raise ValueError("Название скважины не задано")
            borehole_top = self._parse_float(self.var_borehole_top.get())

            if not self.layer_rows:
                raise ValueError("Не задан ни один слой скважины")

            borehole = Borehole(code=borehole_code, z_top=borehole_top)
            for row in self.layer_rows:
                soil_code, thickness = row.get_data()
                soil = self.soil_manager.get(soil_code)
                borehole.add(soil, thickness)

            result = disp_calculation(
                borehole=borehole,
                Hc=params["Hc"],
                H=params["H"],
                F=params["F"],
                a=params["a"],
                b=params["b"],
            )
            self.result_var.set(f"{result:.6f}")
        except Exception as exc:
            show_error("Ошибка", str(exc))


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
