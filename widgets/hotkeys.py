from mylibproject.myutils import is_russian_layout


def add_hotkeys(text_widget):
    """Добавляет горячие клавиши для стандартных операций с текстом."""

    def on_key_press(event, text_widget):
        if is_russian_layout():
            if event.state & 0x4:  # Нажата клавиша Control
                if event.keycode == 67:  # C
                    text_widget.event_generate("<<Copy>>")
                elif event.keycode == 86:  # V
                    text_widget.event_generate("<<Paste>>")
                elif event.keycode == 88:  # X
                    text_widget.event_generate("<<Cut>>")
                elif event.keycode == 65:  # A
                    text_widget.event_generate("<<SelectAll>>")

    text_widget.bind('<KeyPress>', lambda event: on_key_press(event, text_widget))

