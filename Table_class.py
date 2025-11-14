from __future__ import annotations
from dataclasses import dataclass
from bisect import bisect_left
from typing import List, Tuple, Sequence, Union, Dict

Number = Union[int, float]
Interval = Tuple[Number, Number]  # (lo, hi)

# ---------- 1D ----------
@dataclass(slots=True)
class Table1D:
    """
    Универсальная 1D-таблица.
    Можно задать:
      - nodes: X-узлы (возр.) и Y-значения такой же длины
      - intervals: список интервалов (lo, hi) и Y на каждый интервал (ступенька)
    """
    nodes: Sequence[Number] | None = None
    values: Sequence[Number] | None = None
    intervals: Sequence[Interval] | None = None

    @classmethod
    def from_nodes(cls, xs: Sequence[Number], ys: Sequence[Number]) -> "Table1D":
        if len(xs) != len(ys) or not xs:
            raise ValueError("Длины xs и ys должны совпадать и быть > 0.")
        if any(xs[i] > xs[i+1] for i in range(len(xs)-1)):
            raise ValueError("xs должны быть неубывающими.")
        return cls(nodes=list(xs), values=list(ys))

    @classmethod
    def from_intervals(cls, intervals: Sequence[Interval], ys: Sequence[Number]) -> "Table1D":
        if len(intervals) != len(ys) or not intervals:
            raise ValueError("Длины intervals и ys должны совпадать и быть > 0.")
        return cls(intervals=list(intervals), values=list(ys))

    def lookup(self, x: Number, *, interpolate: bool = False, clamp: bool = True) -> Number:
        if self.intervals is not None:
            # ступенчатая по интервалам
            for (lo, hi), y in zip(self.intervals, self.values):
                if x >= lo and (x < hi or hi == float("inf")):
                    return y
            if clamp:
                return self.values[0] if x < self.intervals[0][0] else self.values[-1]
            raise ValueError("x вне диапазона интервалов.")
        # по узлам
        xs, ys = self.nodes, self.values
        if xs is None or ys is None:
            raise ValueError("Таблица не инициализирована.")
        if x <= xs[0]:
            return ys[0] if clamp else (_ for _ in ()).throw(ValueError("x меньше минимума."))
        if x >= xs[-1]:
            return ys[-1] if clamp else (_ for _ in ()).throw(ValueError("x больше максимума."))
        i = bisect_left(xs, x)
        x0, x1 = xs[i-1], xs[i]
        y0, y1 = ys[i-1], ys[i]
        if not interpolate:
            return y0  # ступенька слева
        t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

# ---------- 2D ----------
@dataclass(slots=True)
class Table2D:
    """
    Универсальная 2D-таблица на регулярной сетке узлов.
    row_grid[i] ↔ values[i][j] ↔ col_grid[j]
    """
    row_grid: Sequence[Number]
    col_grid: Sequence[Number]
    values: Sequence[Sequence[Number]]  # размер [len(row_grid)] x [len(col_grid)]

    def __post_init__(self):
        n_rows, n_cols = len(self.row_grid), len(self.col_grid)
        if n_rows == 0 or n_cols == 0:
            raise ValueError("Пустые row_grid/col_grid.")
        if len(self.values) != n_rows or any(len(r) != n_cols for r in self.values):
            raise ValueError("Размеры values не совпадают с сеткой.")

        if any(self.row_grid[i] > self.row_grid[i+1] for i in range(n_rows-1)):
            raise ValueError("row_grid должен быть неубывающим.")
        if any(self.col_grid[i] > self.col_grid[i+1] for i in range(n_cols-1)):
            raise ValueError("col_grid должен быть неубывающим.")

    @staticmethod
    def _interp1d(xg: Sequence[Number], yg: Sequence[Number], x: Number, clamp: bool=True) -> Number:
        if x <= xg[0]:
            return yg[0] if clamp else (_ for _ in ()).throw(ValueError("x меньше минимума."))
        if x >= xg[-1]:
            return yg[-1] if clamp else (_ for _ in ()).throw(ValueError("x больше максимума."))
        i = bisect_left(xg, x)
        x0, x1 = xg[i-1], xg[i]
        y0, y1 = yg[i-1], yg[i]
        t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    def lookup(self, row_key: Number, col_key: Number, *, interpolate: bool=True, clamp: bool=True) -> Number:
        rg, cg, V = self.row_grid, self.col_grid, self.values

        if not interpolate:
            # ступенька по ближайшему левому узлу в обеих осях
            def left_idx(g: Sequence[Number], x: Number) -> int:
                if x <= g[0]: return 0
                if x >= g[-1]: return max(0, len(g)-2) if len(g) >= 2 else 0
                j = bisect_left(g, x)
                return max(0, j-1)
            i = left_idx(rg, row_key)
            j = left_idx(cg, col_key)
            return V[i][j]

        # билинейная интерполяция: сначала по строкам в двух соседних столбцах, затем между столбцами
        # индексы по столбцу
        if col_key <= cg[0]:
            j0, j1, t = 0, 0, 0.0
        elif col_key >= cg[-1]:
            j0, j1, t = len(cg)-1, len(cg)-1, 0.0
        else:
            j1 = bisect_left(cg, col_key)
            j0 = j1 - 1
            c0, c1 = cg[j0], cg[j1]
            t = 0.0 if c1 == c0 else (col_key - c0) / (c1 - c0)

        col0 = [V[i][j0] for i in range(len(rg))]
        col1 = [V[i][j1] for i in range(len(rg))]
        v0 = self._interp1d(rg, col0, row_key, clamp=clamp)
        v1 = self._interp1d(rg, col1, row_key, clamp=clamp)
        return v0 + t * (v1 - v0)
