import tkinter as tk

from .dialogs import ask_directory, ask_file, ask_save_file


def select_path(
    entry_widget,
    path_type="folder",
    saved_data=None,
    extension: str | None = None,
):
    """Открывает диалог выбора пути и вставляет его в виджет."""
    if path_type == "folder":
        selected_path = ask_directory()
    elif path_type == "file":
        selected_path = ask_file()
    elif path_type == "save_file":
        filetypes = None
        if extension:
            filetypes = [(extension.lstrip("."), f"*{extension}")]
        selected_path = ask_save_file(extension or "", filetypes)
    else:
        raise ValueError(
            "Недопустимый тип пути: используйте 'folder', 'file' или 'save_file'."
        )

    if selected_path:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, selected_path)
        if saved_data is not None:
            key = "path"
            saved_data.update({key: entry_widget.get()})

