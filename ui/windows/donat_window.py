from ui.components.window_navigation import prepare_window_navigation
import tkinter as tk
from pathlib import Path
from ui.components.button_styler import create_hover_button
from core.dpi_utils import place_toplevel_centered_on_parent

class DonationWindow:
    def __init__(self, parent):
        self.parent = parent
        self.manager_dir = Path(__file__).resolve().parents[2]
        self.root = tk.Toplevel(parent)
        self.root.withdraw()
        self.root.maxsize(self.root.winfo_screenwidth() - 16, self.root.winfo_screenheight() - 60)
        self.setup_window_properties()
        self.root.title("Поддержать разработчика")

        self.setup_ui()
        self.root.update_idletasks()
        width = min(self.root.winfo_screenwidth() - 16, max(340, self.root.winfo_reqwidth() + 8))
        self.thank_you_label.configure(wraplength=max(120, width - 80))
        self.qr_caption.configure(wraplength=max(120, width - 80))
        self.root.update_idletasks()
        height = min(self.root.winfo_screenheight() - 60, max(360, self.root.winfo_reqheight() + 12))
        place_toplevel_centered_on_parent(
            self.root, self.parent, fixed_content_size=(width, height), immediate=True
        )

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)

        # Устанавливаем WM_CLASS
        try:
            self.root.wm_class("ZapretDPIManager")
        except Exception:
            pass

        # Устанавливаем иконку
        try:
            icon_path = self.manager_dir / "ico/zapret.png"
            if icon_path.is_file():
                icon = tk.PhotoImage(master=self.root, file=str(icon_path))
                self.root.iconphoto(True, icon)
        except Exception as e:
            print(f"Не удалось установить иконку: {e}")

    def setup_ui(self):
        """Создает элементы интерфейса"""
        # При нехватке высоты прокручивается содержимое, а кнопка остаётся внизу.
        body_frame = tk.Frame(self.root, bg='#182030')
        body_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(body_frame, bg='#182030', bd=0, highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(body_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        main_frame = tk.Frame(canvas, bg='#182030', padx=20, pady=15)
        content = canvas.create_window((0, 0), window=main_frame, anchor=tk.NW)
        self.body_canvas = canvas

        # Заголовок
        title_label = tk.Label(main_frame,
                              text="Поддержать разработчика",
                              font=("Arial", 16, "bold"),
                              bg='#182030', fg='white')
        title_label.pack(pady=(0, 15))

        # Текст с благодарностью
        thank_you_text = (
            "Спасибо, что используете Zapret DPI Manager! "
            "Если вам нравится проект и вы хотите поддержать его развитие, "
            "вы можете сделать это через систему донатов."
        )

        thank_you_label = tk.Label(
            main_frame,
            text=thank_you_text,
            font=('Arial', 11),
            bg='#182030',
            fg='white',
            wraplength=350,
            justify=tk.CENTER,
        )
        thank_you_label.pack(pady=(0, 15), fill=tk.X)
        self.thank_you_label = thank_you_label

        def _sync_thank_wrap(_event=None):
            try:
                aw = main_frame.winfo_width()
                if aw <= 1:
                    return
                thank_you_label.config(wraplength=max(120, aw - 40))
                qr_caption.config(wraplength=max(120, aw - 40))
                canvas.configure(scrollregion=canvas.bbox(tk.ALL))
                if main_frame.winfo_reqheight() > canvas.winfo_height():
                    if not scrollbar.winfo_manager():
                        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=canvas)
                else:
                    scrollbar.pack_forget()
            except tk.TclError:
                pass

        main_frame.bind("<Configure>", lambda _e: _sync_thank_wrap())
        def _sync_canvas(event):
            canvas.itemconfigure(content, width=event.width)
            _sync_thank_wrap()
        canvas.bind("<Configure>", _sync_canvas)
        self.root.after_idle(_sync_thank_wrap)

        # Фрейм для QR кода
        qr_frame = tk.Frame(main_frame, bg='#182030')
        qr_frame.pack(pady=10)

        # Загружаем QR код
        try:
            # Путь к QR коду
            qr_path = self.manager_dir / "utils/qr.png"

            if qr_path.is_file():
                self._qr_original = tk.PhotoImage(master=self.root, file=str(qr_path))
                side = max(self._qr_original.width(), self._qr_original.height())
                limit = max(1, min(200, self.root.winfo_screenwidth() - 80,
                                   self.root.winfo_screenheight() - 120))
                self._qr_factor = max(1, (side + limit - 1) // limit)
                self.qr_image = self._qr_original.subsample(self._qr_factor, self._qr_factor)
                self.qr_label = tk.Label(qr_frame, image=self.qr_image, bg='#182030')
                self.qr_label.pack()
            else:
                raise FileNotFoundError("QR код не найден")

        except Exception as e:
            print(f"Не удалось загрузить QR-код {qr_path}: {e}")
            error_text = ("QR-код не найден" if not qr_path.is_file() else
                          "Не удалось загрузить QR-код.\nНужен файл в формате PNG.")
            error_label = tk.Label(qr_frame,
                                  text=error_text,
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
                             wraplength=350,
                             justify=tk.CENTER)
        qr_caption.pack(pady=(5, 15))
        self.qr_caption = qr_caption

        # Кнопка закрытия
        button_frame = tk.Frame(self.root, bg='#182030')
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 15), before=body_frame)

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

        def _scroll(event):
            if main_frame.winfo_reqheight() <= canvas.winfo_height():
                return
            direction = -1 if getattr(event, 'num', None) == 4 or getattr(event, 'delta', 0) > 0 else 1
            canvas.yview_scroll(direction, 'units')
            return 'break'

        def _bind_scroll(widget):
            for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                widget.bind(sequence, _scroll, add='+')
            for child in widget.winfo_children():
                _bind_scroll(child)

        _bind_scroll(canvas)
        self.root.update_idletasks()
        canvas.configure(width=main_frame.winfo_reqwidth(),
                         height=min(main_frame.winfo_reqheight(),
                                    self.root.winfo_screenheight() - button_frame.winfo_reqheight() - 100))

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
        prepare_window_navigation(self.root)
        self.root.wait_window()
