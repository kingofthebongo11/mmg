"""Пакет с функциями для работы с различными виджетами."""

from .context_menu import make_context_menu
from .hotkeys import add_hotkeys
from .select_path import select_path
from .message_log import message_log
from .text_widget import create_text, clear_text
from .plot_editor import PlotEditor
from .dialogs import ask_directory, ask_file, ask_save_file, show_error

__all__ = [
    "make_context_menu",
    "add_hotkeys",
    "select_path",
    "message_log",
    "create_text",
    "clear_text",
    "PlotEditor",
    "ask_directory",
    "ask_file",
    "ask_save_file",
    "show_error",
]

