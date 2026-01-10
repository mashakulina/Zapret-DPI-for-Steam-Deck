import tkinter as tk
import webbrowser
import os
from ui.components.button_styler import create_hover_button

class DonationWindow:
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("Поддержать разработчика")

        self.setup_ui()

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.geometry("380x460")
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)

        # Устанавливаем WM_CLASS
        try:
            self.root.wm_class("ZapretDPIManager")
        except:
            pass

        # Устанавливаем иконку
        try:
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
            icon_path = os.path.join(manager_dir, "ico/zapret.png")
            if os.path.exists(icon_path):
                icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon)
        except Exception as e:
            print(f"Не удалось установить иконку: {e}")

    def setup_ui(self):
        """Создает элементы интерфейса"""
        # Основной фрейм
        main_frame = tk.Frame(self.root, bg='#182030', padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame,
                              text="Поддержать разработчика",
                              font=("Arial", 16, "bold"),
                              bg='#182030', fg='white')
        title_label.pack(pady=(0, 15))

        # Текст с благодарностью
        thank_you_text = (
            "Спасибо, что используете\nZapret DPI Manager!\n\n"
            "Если вам нравится проект и вы хотите поддержать его развитие, "
            "вы можете сделать это через систему донатов."
        )

        thank_you_label = tk.Label(main_frame,
                                  text=thank_you_text,
                                  font=('Arial', 11),
                                  bg='#182030',
                                  fg='white',
                                  wraplength=350,
                                  justify=tk.CENTER)
        thank_you_label.pack(pady=(0, 15))

        # Фрейм для QR кода
        qr_frame = tk.Frame(main_frame, bg='#182030')
        qr_frame.pack(pady=10)

        # Загружаем QR код
        try:
            # Путь к QR коду
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
            qr_path = os.path.join(manager_dir, "utils/qr.png")

            if os.path.exists(qr_path):
                self.qr_image = tk.PhotoImage(file=qr_path)
                qr = tk.Label(qr_frame, image=self.qr_image, bg='#182030')
                qr.pack(side=tk.LEFT, padx=(0, 10))
            else:
                raise FileNotFoundError("QR код не найден")

        except Exception as e:
            # Если QR код не найден, показываем сообщение
            error_label = tk.Label(qr_frame,
                                  text="QR-код не найден",
                                  font=('Arial', 10),
                                  bg='#182030',
                                  fg='#ff3b30',
                                  justify=tk.CENTER)
            error_label.pack()

        # Текст под QR кодом
        qr_caption = tk.Label(main_frame,
                             text="Отсканируйте QR-код для перевода в Вашем банке",
                             font=('Arial', 10),
                             bg='#182030',
                             fg='#5BA06A',
                             justify=tk.CENTER)
        qr_caption.pack(pady=(5, 15))

        # Кнопка закрытия
        button_frame = tk.Frame(main_frame, bg='#182030')
        button_frame.pack(fill=tk.X, pady=(10, 0))

        close_style = {
            'font': ('Arial', 10),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 8,
            'width': 12,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        close_btn = create_hover_button(button_frame,
                                       text="Закрыть",
                                       command=self.root.destroy,
                                       **close_style)
        close_btn.pack()

        # Обработка клавиш
        self.root.bind('<Escape>', lambda e: self.root.destroy())
        self.root.bind('<Return>', lambda e: self.root.destroy())

    def create_donation_link(self, parent, icon, text, command_func):
        """Создает ссылку для доната"""
        link_frame = tk.Frame(parent, bg='#182030')
        link_frame.pack(anchor=tk.CENTER, pady=5)

        # Иконка
        icon_label = tk.Label(link_frame,
                             text=icon,
                             font=('Arial', 12),
                             bg='#182030',
                             fg='#3CAA3C',
                             cursor='hand2')
        icon_label.pack(side=tk.LEFT)
        icon_label.bind("<Button-1>", command_func)

        # Текст
        text_label = tk.Label(link_frame,
                             text=text,
                             font=('Arial', 11, 'underline'),
                             bg='#182030',
                             fg='#3CAA3C',
                             cursor='hand2')
        text_label.pack(side=tk.LEFT, padx=(5, 0))
        text_label.bind("<Button-1>", command_func)

        # Эффекты при наведении
        for label in [icon_label, text_label]:
            label.bind("<Enter>", lambda e, l=text_label: l.config(fg='#4d8058'))
            label.bind("<Leave>", lambda e, l=text_label: l.config(fg='#3CAA3C'))

    def run(self):
        """Запускает окно"""
        self.root.wait_window()
