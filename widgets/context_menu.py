import tkinter as tk


def make_context_menu(widget):
    """Создает стандартное контекстное меню для виджета."""
    context_menu = tk.Menu(widget, tearoff=0)
    context_menu.add_command(label="Вырезать", command=lambda: widget.event_generate("<<Cut>>"))
    context_menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))
    context_menu.add_command(label="Вставить", command=lambda: widget.event_generate("<<Paste>>"))
    context_menu.add_command(label="Выделить все", command=lambda: widget.event_generate("<<SelectAll>>"))

    def show_context_menu(event):
        context_menu.tk_popup(event.x_root, event.y_root)

    widget.bind("<Button-3>", show_context_menu)

