import tkinter as tk


def message_log(log_text, message):
    """Добавляет сообщение в текстовый лог."""
    log_text.config(state='normal')
    log_text.insert(tk.END, message + "\n")
    log_text.config(state='disabled')
    log_text.yview(tk.END)

