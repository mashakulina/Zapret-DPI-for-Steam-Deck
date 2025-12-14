import tkinter as tk
from ui.components.button_styler import create_hover_button
from ui.windows.strategy_window import StrategyWindow
from ui.windows.custom_strategy_window import CustomStrategyWindow

class StrategySelectorWindow:
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("Выбор типа стратегии")

        self.setup_ui()

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.geometry("250x285")
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg='#182030', padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame, text="Сменить стратегию",
                              font=("Arial", 14, "bold"), fg='white', bg='#182030')
        title_label.pack(pady=(15, 30))

        # Стиль кнопок
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 12,
            'width': 25,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка "Использовать готовые стратегии"
        ready_button = create_hover_button(
            main_frame,
            text="Выбрать готовый пресет",
            command=self.open_ready_strategies,
            **button_style
        )
        ready_button.pack(pady=(0, 15))

        # Кнопка "Собрать свою стратегию"
        custom_button = create_hover_button(
            main_frame,
            text="Собрать свой пресет",
            command=self.open_custom_strategy,
            **button_style
        )
        custom_button.pack(pady=(0, 15))

        # Кнопка "Назад"
        back_button = create_hover_button(
            main_frame,
            text="Назад",
            command=self.close_window,
            **button_style
        )
        back_button.pack(pady=(10, 0))

    def open_ready_strategies(self):
        """Открывает окно готовых стратегий"""
        self.close_window()
        strategy_window = StrategyWindow(self.parent)
        strategy_window.run()

    def open_custom_strategy(self):
        """Открывает окно сборки своей стратегии"""
        self.close_window()
        custom_window = CustomStrategyWindow(self.parent)
        custom_window.run()

    def close_window(self):
        """Закрывает окно"""
        self.root.destroy()

    def run(self):
        """Запускает окно"""
        self.root.wait_window()
