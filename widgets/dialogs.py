from tkinter import filedialog, messagebox
from logging_utils import get_logger
from typing import Sequence

logger = get_logger(__name__)


def ask_file() -> str:
    """Открывает диалог выбора файла."""
    path = filedialog.askopenfilename()
    if not path:
        logger.info("Файл не выбран")
    return path


def ask_save_file(
    defaultextension: str = "",
    filetypes: Sequence[tuple[str, str]] | None = None,
) -> str:
    """Открывает диалог сохранения файла."""
    path = filedialog.asksaveasfilename(
        defaultextension=defaultextension,
        filetypes=filetypes,
    )
    if not path:
        logger.info("Файл не выбран")
    elif defaultextension and not path.endswith(defaultextension):
        path += defaultextension
    return path


def ask_directory() -> str:
    """Открывает диалог выбора папки."""
    path = filedialog.askdirectory()
    if not path:
        logger.info("Папка не выбрана")
    return path


def show_error(title: str, message: str) -> None:
    """Показывает сообщение об ошибке и логирует его."""
    logger.error("%s: %s", title, message)
    messagebox.showerror(title, message)
