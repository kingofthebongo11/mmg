import tkinter as tk
from tkinter import ttk

from .context_menu import make_context_menu
from .hotkeys import add_hotkeys


def create_text(parent, method='text', height=10, wrap='word', state='normal', scrollbar=False, max_lines=0):
    """Создает текстовый или строковый виджет с необязательной прокруткой."""
    if method == 'entry':
        text_widget = tk.Entry(parent, state=state)

    elif method == 'text':
        text_widget = tk.Text(parent, height=height, wrap=wrap, state=state)
        if max_lines > 0:
            def limit_text_lines(text_widget, max_lines):
                def check_lines(event):
                    if max_lines > 0:
                        current_text = text_widget.get("1.0", tk.END)
                        lines = current_text.splitlines()
                        if len(lines) > max_lines:
                            text_widget.delete(f"{max_lines + 1}.0", tk.END)

                text_widget.bind("<KeyRelease>", check_lines)

            limit_text_lines(text_widget, max_lines)

        if scrollbar:
            def bind_scrollbar(log_text, log_scrollbar):
                def update_scrollbar(log_text, log_scrollbar):
                    log_scrollbar.config(command=log_text.yview)
                    log_text["yscrollcommand"] = log_scrollbar.set

                log_text.bind("<KeyRelease>", lambda event: update_scrollbar(log_text, log_scrollbar))
                log_text.bind("<MouseWheel>", lambda event: update_scrollbar(log_text, log_scrollbar))
                log_text.bind("<Configure>", lambda event: update_scrollbar(log_text, log_scrollbar))

            text_scrollbar = ttk.Scrollbar(parent, command=text_widget.yview)
            text_widget["yscrollcommand"] = text_scrollbar.set
            bind_scrollbar(text_widget, text_scrollbar)
    else:
        raise ValueError("Некорректное значение параметра method. Должно быть 'entry' или 'text'.")

    make_context_menu(text_widget)
    add_hotkeys(text_widget)
    if scrollbar and method == "text":
        return text_widget, text_scrollbar
    return text_widget


def clear_text(text_widget):
    """Очищает содержимое текстового виджета."""
    text_widget.config(state='normal')
    text_widget.delete(1.0, tk.END)
    text_widget.config(state='disabled')

