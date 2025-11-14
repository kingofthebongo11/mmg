from bisect import bisect_left
from typing import Dict, List

class TableError(ValueError):
    pass

def _interp1d(x_grid: List[float], y_grid: List[float], x: float) -> float:
    """Линейная интерполяция по одной оси с прижатием к краям."""
    if len(x_grid) != len(y_grid) or len(x_grid) == 0:
        raise TableError("Пустой ряд или разные длины x/y.")
    if x <= x_grid[0]:
        return y_grid[0]
    if x >= x_grid[-1]:
        return y_grid[-1]
    i = bisect_left(x_grid, x)
    x0, x1 = x_grid[i-1], x_grid[i]
    y0, y1 = y_grid[i-1], y_grid[i]
    t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)

def k_from_table(z_over_b: float, a_over_b: float, *,
                 z_rows: List[float],
                 columns: Dict[float, List[float]]) -> float:
    """
    Возвращает k по таблице 7.7:
      z_rows: отсортированный список значений z/b (строки);
      columns: словарь {a/b: [k на каждой строке z_rows]}.
    Интерполяция: по z/b внутри столбцов + по a/b между столбцами.
    Вне диапазонов — прижатие к краям.
    """
    if not z_rows or not columns:
        raise TableError("Не заданы строки/столбцы таблицы.")
    # проверка длин
    for a_key, col in columns.items():
        if len(col) != len(z_rows):
            raise TableError(f"Столбец a/b={a_key} имеет длину {len(col)}, "
                             f"ожидалось {len(z_rows)}.")

    a_keys = sorted(columns.keys())
    # если a/b левее/правее диапазона — берём крайний столбец
    if a_over_b <= a_keys[0]:
        return _interp1d(z_rows, columns[a_keys[0]], z_over_b)
    if a_over_b >= a_keys[-1]:
        return _interp1d(z_rows, columns[a_keys[-1]], z_over_b)

    # найдём соседние столбцы по a/b
    j = bisect_left(a_keys, a_over_b)
    a0, a1 = a_keys[j-1], a_keys[j]
    # интерполируем по z/b в каждом из двух столбцов
    k0 = _interp1d(z_rows, columns[a0], z_over_b)
    k1 = _interp1d(z_rows, columns[a1], z_over_b)
    # интерполяция по a/b
    t = 0.0 if a1 == a0 else (a_over_b - a0) / (a1 - a0)
    return k0 + t * (k1 - k0)