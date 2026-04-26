"""Всплывающие подсказки статуса и иконок."""
import tkinter as tk


class MainTooltipsMixin:
    def show_status_tooltip(self, event=None):
        """Показывает всплывающее окошко со статусом службы"""
        if self.status_tooltip:
            return

        # Индикатор всегда "⬤", а состояние хранится в fg.
        indicator_color = str(self.status_indicator.cget("fg")).strip().lower()
        if indicator_color in {"#30d158"}:  # Зеленый
            status_text = "Статус службы: активен"
        elif indicator_color in {"#ff3b30"}:  # Красный
            status_text = "Статус службы: неактивен"
        elif indicator_color in {"#ff9500"}:  # Оранжевый
            status_text = "Статус службы: неизвестный"
        else:
            # Безопасный фолбэк, если цвет задан именем или системой.
            status_text = "Статус службы: активен" if self.service_running else "Статус службы: неактивен"

        # Позиционируем подсказку рядом с индикатором
        x = self.status_indicator.winfo_rootx() - 20
        y = self.status_indicator.winfo_rooty() + self.status_indicator.winfo_height() + 5

        # Создаем всплывающее окно
        self.status_tooltip = tk.Toplevel(self.root)
        self.status_tooltip.wm_overrideredirect(True)
        self.status_tooltip.geometry(f"+{x}+{y}")
        self.status_tooltip.configure(bg='#15354D', relief=tk.SOLID, bd=1)

        # Добавляем текст
        label = tk.Label(self.status_tooltip,
                        text=status_text,
                        font=("Arial", 10),
                        fg='white',
                        bg='#15354D',
                        padx=10,
                        pady=5)
        label.pack()


    def show_icon_tooltip(self, event, description):
        """Показывает всплывающее окошко для иконки"""
        if hasattr(self, 'icon_tooltip') and self.icon_tooltip:
            self.hide_icon_tooltip()

        # Определяем виджет-источник события
        widget = event.widget

        # Позиционируем подсказку рядом с иконкой
        x = widget.winfo_rootx() - 20
        y = widget.winfo_rooty() + widget.winfo_height() + 5

        # Создаем всплывающее окно
        self.icon_tooltip = tk.Toplevel(self.root)
        self.icon_tooltip.wm_overrideredirect(True)
        self.icon_tooltip.geometry(f"+{x}+{y}")
        self.icon_tooltip.configure(bg='#15354D', relief=tk.SOLID, bd=1)

        # Добавляем текст с заголовком и описанием
        text_frame = tk.Frame(self.icon_tooltip, bg='#15354D')
        text_frame.pack(padx=10, pady=5)

        # Описание
        desc_label = tk.Label(text_frame,
                            text=description,
                            font=("Arial", 9),
                            fg='white',
                            bg='#15354D',
                            justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)

    def hide_icon_tooltip(self, event=None):
        """Скрывает всплывающее окошко для иконки"""
        if hasattr(self, 'icon_tooltip') and self.icon_tooltip:
            try:
                self.icon_tooltip.destroy()
            except Exception:
                pass  # Если окно уже уничтожено
            self.icon_tooltip = None

    def hide_status_tooltip(self, event=None):
        """Скрывает всплывающее окошко со статусом"""
        if self.status_tooltip:
            try:
                self.status_tooltip.destroy()
            except Exception:
                pass
            self.status_tooltip = None
