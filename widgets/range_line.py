# ui/widgets/range_line.py
import tkinter as tk
from tkinter import ttk


class RangeLine(ttk.Frame):
    def __init__(
        self,
        master,
        from_=0,
        to=100,
        start=20,
        end=80,
        width=360,
        height=28,
        command=None,
    ):
        super().__init__(master)
        self.from_ = float(from_)
        self.to = float(to)
        self.command = command  # callback(lower, upper)

        self._width = width
        self._h = height
        self._pad = 10
        self._bar_h = 4
        self._r = 7

        self.canvas = tk.Canvas(
            self, width=self._width, height=self._h, highlightthickness=0, bd=0
        )
        self.canvas.pack(fill=tk.X, expand=True)

        self.lower = float(start)
        self.upper = float(end)
        if self.lower > self.upper:
            self.lower, self.upper = self.upper, self.lower

        self._ids = {}
        self._draw_static()
        self._draw_dynamic()

        self._dragging = None
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    # --- внешнее API ---
    def get(self):
        return self.lower, self.upper

    def set(self, lower=None, upper=None, notify=True):
        if lower is not None:
            self.lower = self._quantize(self._clamp(lower))
        if upper is not None:
            self.upper = self._quantize(self._clamp(upper))
        if self.lower > self.upper:
            self.lower, self.upper = self.upper, self.lower
        self._draw_dynamic()
        if notify and self.command:
            self.command(self.lower, self.upper)

    # --- рисование ---
    def _draw_static(self):
        y = self._h // 2
        x0 = self._pad
        x1 = self._width - self._pad
        self._ids["track"] = self.canvas.create_line(x0, y, x1, y, width=self._bar_h, capstyle="round")
        self._ids["range"] = self.canvas.create_line(x0, y, x1, y, width=self._bar_h, capstyle="round")
        self._ids["lower"] = self.canvas.create_oval(0, 0, 0, 0, outline="", fill="")
        self._ids["upper"] = self.canvas.create_oval(0, 0, 0, 0, outline="", fill="")

        self.canvas.itemconfigure(self._ids["track"], fill="#D0D0D0")
        self.canvas.itemconfigure(self._ids["range"], fill="#7FA9F7")
        self.canvas.itemconfigure(self._ids["lower"], outline="#4A6EE0", fill="#4A6EE0")
        self.canvas.itemconfigure(self._ids["upper"], outline="#1E88E5", fill="#1E88E5")

    def _draw_dynamic(self):
        y = self._h // 2
        x_l = self._val2x(self.lower)
        x_u = self._val2x(self.upper)
        self.canvas.coords(self._ids["range"], x_l, y, x_u, y)
        self._set_handle(self._ids["lower"], x_l, y)
        self._set_handle(self._ids["upper"], x_u, y)

    def _set_handle(self, hid, x, y):
        r = self._r
        self.canvas.coords(hid, x - r, y - r, x + r, y + r)

    def _val2x(self, v):
        x0, x1 = self._pad, self._width - self._pad
        t = 0 if self.to == self.from_ else (v - self.from_) / (self.to - self.from_)
        return x0 + t * (x1 - x0)

    def _x2val(self, x):
        x0, x1 = self._pad, self._width - self._pad
        t = (x - x0) / (x1 - x0)
        v = self.from_ + t * (self.to - self.from_)
        return max(self.from_, min(self.to, v))

    def _clamp(self, value):
        return max(self.from_, min(float(value), self.to))

    def _quantize(self, value):
        return round(float(value) * 100) / 100

    # --- события ---
    def _nearest_handle(self, x):
        xl = self._val2x(self.lower)
        xu = self._val2x(self.upper)
        return "lower" if abs(x - xl) <= abs(x - xu) else "upper"

    def _on_click(self, e):
        self._dragging = self._nearest_handle(e.x)
        self._move_handle(self._dragging, e.x, notify=False)

    def _on_drag(self, e):
        if self._dragging:
            self._move_handle(self._dragging, e.x, notify=True)

    def _on_release(self, _e):
        self._dragging = None

    def _move_handle(self, which, x, notify=True):
        v = self._quantize(self._x2val(x))
        if which == "lower":
            self.lower = self._quantize(min(v, self.upper))
        else:
            self.upper = self._quantize(max(v, self.lower))
        self._draw_dynamic()
        if notify and self.command:
            self.command(self.lower, self.upper)
