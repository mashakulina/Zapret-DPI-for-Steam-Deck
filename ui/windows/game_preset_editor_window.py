"""Creation of game presets from a local draft; never writes the live config."""
from pathlib import Path
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import ttk

from core.dpi_utils import place_toplevel_centered_on_parent
from core.game_filter_settings import validate_game_filter_custom_ports
from core.game_presets import PresetExistsError, get_manager_dir, read_current_filter_settings, save_custom_preset
from ui.components.button_styler import create_hover_button, uniform_button_width_for_font
from ui.components.custom_messagebox import ask_yesno, show_error, show_info
from ui.windows.strategy_import_window import SettingsWindow


class GamePresetEditorWindow(SettingsWindow):
    def __init__(self, parent, manager_dir=None):
        self.parent = parent
        self.manager_dir = Path(manager_dir or get_manager_dir())
        config = self.manager_dir / 'config.txt'
        self.config_before = config.read_bytes().decode('utf-8') if config.exists() else ''
        self.config_after = self.config_before
        self.filter_settings = read_current_filter_settings(self.manager_dir)
        self._draft_directory = None
        self._draft_path = None
        self._kate_process = None
        self._kate_poll_id = None
        self._kate_had_grab = False

    def create_window(self):
        self.setup('Добавление пресета для игры', place_window=False)
        # Match IPSet/strategy settings: Tk already scales point-sized fonts.
        self.font = ('Arial', 11)
        self.style.update(font=self.font, padx=self.s(10), pady=self.s(8))
        self.window.bind('<Destroy>', self._on_destroy, add='+')
        footer = self._footer = tk.Frame(self.window, bg='#182030', padx=self.s(10), pady=self.s(10))
        self.body.pack_forget()
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        viewport = tk.Frame(self.window, bg='#182030')
        viewport.pack(fill=tk.BOTH, expand=True)
        canvas = self._canvas = tk.Canvas(viewport, bg='#182030', highlightthickness=0,
                                         bd=0, width=self.s(480), height=1)
        scrollbar = self._scrollbar = tk.Scrollbar(viewport, command=canvas.yview)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        self.body.destroy()
        self.body = tk.Frame(canvas, bg='#182030', padx=self.s(20), pady=self.s(15))
        self._form_item = canvas.create_window((0, 0), window=self.body, anchor='nw')
        self.window.bind('<Button-4>', lambda event: canvas.yview_scroll(-1, 'units'))
        self.window.bind('<Button-5>', lambda event: canvas.yview_scroll(1, 'units'))
        self.window.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
        self.heading = tk.Label(self.body, text='Добавление пресета для игры',
                                font=('Arial', 14, 'bold'), bg='#182030', fg='white',
                                wraplength=self.s(450))
        self.heading.pack(fill=tk.X, pady=(0, self.s(15)))
        self.heading.bind('<Configure>', lambda event: self.heading.configure(wraplength=max(40, event.width)))
        self._labels = [self.heading]
        self.label('Название пресета').pack_configure(pady=0)
        self.name_var = tk.StringVar(self.window)
        tk.Entry(self.body, textvariable=self.name_var, font=self.font,
                 bg='#2A3B5C', fg='white', insertbackground='white', bd=0, relief=tk.FLAT,
                 highlightthickness=2, highlightbackground='#3A4B6C',
                 highlightcolor='#4A8FE7').pack(fill=tk.X, pady=(self.s(5), self.s(12)))
        self.include_ipset = tk.BooleanVar(self.window, value=False)
        self.include_hostlist = tk.BooleanVar(self.window, value=False)
        self._check('Добавить ipset-all (копия ipset-all_user.txt)', self.include_ipset)
        self._check('Добавить list-general (копия list-general_user.txt)', self.include_hostlist)
        self.label('В Kate открывается черновик config.txt. Сохраните изменения в Kate, затем сохраните пресет.', muted=True)
        self.button('Открыть config.txt в Kate', self.open_config, anchor=tk.CENTER)
        gf = self.filter_settings['game_filter']
        self.game_mode = None
        if gf['enabled']:
            self.label('GameFilter включён — сохранить его настройки:')
            self.game_mode = tk.StringVar(self.window, value=gf['mode'])
            ttk.Combobox(self.body, textvariable=self.game_mode, values=['both', 'tcp', 'udp'],
                         state='disabled' if gf.get('custom_ports') else 'readonly', font=self.font).pack(fill=tk.X, pady=self.s(6))
            if gf.get('custom_ports'):
                self.label("Сохранённые порты: " + "; ".join(
                    f"{protocol.upper()}: {ports}" for protocol, ports in gf['custom_ports'].items()))
                self.label('Режим закреплён за этими диапазонами. Измените его в настройках GameFilter перед созданием пресета.', muted=True)
        else:
            self.label('GameFilter выключен. При применении пресета он останется выключен.', muted=True)
        ipset = self.filter_settings['ipset_filter']
        self.ipset_mode = None
        if ipset != 'none':
            self.label('IPSet Filter включён — сохранить режим:')
            self.ipset_mode = tk.StringVar(self.window, value=ipset)
            for value, label in [('loaded', 'Загруженные IP (loaded)'), ('any', 'Любой IP (any)')]:
                tk.Radiobutton(self.body, text=label, variable=self.ipset_mode, value=value,
                               font=self.font, bg='#182030', fg='white', selectcolor='#1E4A6E',
                               activebackground='#182030', activeforeground='white',
                               highlightthickness=0, bd=0).pack(anchor=tk.W)
        else:
            self.label('IPSet Filter выключен. При применении будет установлен none.', muted=True)
        self._footer_center = tk.Frame(footer, bg='#182030')
        self._footer_center.pack()
        button_width = max(12, uniform_button_width_for_font(
            self._footer_center, self.font, 'Сохранить пресет', 'Назад'))
        self._footer_buttons = [create_hover_button(
            self._footer_center, text=text, command=command, **dict(self.style, width=button_width))
            for text, command in [('Сохранить пресет', self.save), ('Назад', self.close)]]
        self._footer_stacked = None
        self._fit_form_to_content()
        canvas.bind('<Configure>', self._resize_form)
        self.body.bind('<Configure>', self._update_form_scroll)
        self._update_form_scroll()
        return self.window

    def _arrange_footer(self, width):
        gap = 15
        available = width - 2 * self.s(10)
        stacked = sum(button.winfo_reqwidth() for button in self._footer_buttons) + gap > available
        if stacked == self._footer_stacked:
            return
        self._footer_stacked = stacked
        for index, button in enumerate(self._footer_buttons):
            button.pack_forget()
            button.pack(side=tk.TOP if stacked else tk.LEFT,
                        padx=(0, 0 if stacked or index else gap),
                        pady=(0, 10 if stacked and not index else 0))

    def _fit_form_to_content(self):
        self.window.update_idletasks()
        max_width = max(1, self.window.winfo_screenwidth() - 32)
        max_height = max(1, self.window.winfo_screenheight() - 80)
        button_width = sum(button.winfo_reqwidth() for button in self._footer_buttons) + 15 + 2 * self.s(10)
        width = min(max(self.body.winfo_reqwidth(), button_width), max_width)
        self._arrange_footer(width)
        self._canvas.configure(width=width)
        self._canvas.itemconfigure(self._form_item, width=width)
        self.window.update_idletasks()
        available = max(1, max_height - self._footer.winfo_reqheight())
        if self.body.winfo_reqheight() > available:
            self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self._canvas)
            bar_width = self._scrollbar.winfo_reqwidth()
            width = min(width + bar_width, max_width)
            self._canvas.configure(width=max(1, width - bar_width))
            self._canvas.itemconfigure(self._form_item, width=max(1, width - bar_width))
            self.window.update_idletasks()
        self._canvas.configure(height=min(self.body.winfo_reqheight(), available))
        self.window.update_idletasks()
        height = min(self.body.winfo_reqheight() + self._footer.winfo_reqheight(), max_height)
        place_toplevel_centered_on_parent(
            self.window, self._anchor, fixed_content_size=(width, height), immediate=True)

    def _resize_form(self, event):
        self._canvas.itemconfigure(self._form_item, width=event.width)
        self._arrange_footer(self.window.winfo_width())
        self._update_form_scroll()

    def _update_form_scroll(self, event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))
        if self.body.winfo_reqheight() > self._canvas.winfo_height() + 1:
            if not self._scrollbar.winfo_manager():
                self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self._canvas)
        elif self._scrollbar.winfo_manager():
            self._scrollbar.pack_forget()
            self._canvas.yview_moveto(0)

    def _check(self, text, variable):
        check = tk.Checkbutton(self.body, text=text, variable=variable, font=self.font, bg='#182030',
                               fg='white', selectcolor='#1E4A6E', activebackground='#182030',
                               activeforeground='white', anchor=tk.W, justify=tk.LEFT,
                               wraplength=self.s(450), bd=0, highlightthickness=0, relief=tk.FLAT)
        check.pack(fill=tk.X, pady=self.s(5))
        check.bind('<Configure>', lambda event: check.configure(wraplength=max(40, event.width - self.s(36))))

    def open_config(self):
        if self._kate_process is not None:
            if self._kate_process.poll() is None:
                return
            if self._kate_poll_id is not None:
                self.window.after_cancel(self._kate_poll_id)
            self._poll_kate()
        try:
            if self._draft_directory is None:
                self._draft_directory = tempfile.TemporaryDirectory(prefix='zapret-game-preset-')
                self._draft_path = Path(self._draft_directory.name) / 'config.txt'
                self._draft_path.write_bytes(self.config_after.encode('utf-8'))
            self._kate_process = subprocess.Popen(
                ['kate', '--new', '--block', '--encoding', 'UTF-8', str(self._draft_path)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
        except OSError as error:
            self.dialog(show_error, 'Ошибка открытия Kate', f'Не удалось открыть config.txt в Kate.\n{error}')
            return
        self._kate_had_grab = self.window.grab_current() == self.window
        if self._kate_had_grab:
            self.window.grab_release()
        if self._kate_poll_id is not None:
            self.window.after_cancel(self._kate_poll_id)
        self._kate_poll_id = self.window.after(200, self._poll_kate)

    def _read_config_draft(self):
        path = getattr(self, '_draft_path', None)
        if path is not None:
            self.config_after = path.read_bytes().decode('utf-8')

    def _poll_kate(self):
        self._kate_poll_id = None
        result = self._kate_process.poll()
        if result is None:
            self._kate_poll_id = self.window.after(200, self._poll_kate)
            return
        self._kate_process = None
        try:
            self._read_config_draft()
            if result:
                self.dialog(show_error, 'Ошибка Kate',
                            'Kate завершился с ошибкой. Проверьте сохранённый черновик перед сохранением пресета.')
        except (OSError, UnicodeError) as error:
            self.dialog(show_error, 'Ошибка чтения config.txt', str(error))
        finally:
            if self._kate_had_grab:
                self.window.grab_set()
                self.window.lift()
                self.window.focus_set()
            self._kate_had_grab = False

    def _release_draft(self):
        if self._kate_poll_id is not None:
            try:
                self.window.after_cancel(self._kate_poll_id)
            except tk.TclError:
                pass
            self._kate_poll_id = None
        directory = self._draft_directory
        if directory is None:
            return
        self._draft_directory = self._draft_path = None
        process, self._kate_process = self._kate_process, None
        if process is not None and process.poll() is None:
            # Kate owns the draft until its window closes. Cleanup never calls Tk.
            def cleanup():
                try:
                    process.wait()
                finally:
                    directory.cleanup()
            threading.Thread(target=cleanup, daemon=True).start()
        else:
            directory.cleanup()

    def _on_destroy(self, event):
        if event.widget == self.window:
            self._release_draft()

    def close(self):
        self._release_draft()
        super().close()

    def save(self):
        overwritten = False
        game_filter = None
        if self.game_mode is not None:
            game_filter = dict(enabled=True, mode=self.game_mode.get(),
                               main_bypass_enabled=self.filter_settings['game_filter']['main_bypass_enabled'],
                               discord_enabled=self.filter_settings['game_filter']['discord_enabled'])
        try:
            if game_filter is not None:
                ports = validate_game_filter_custom_ports(game_filter['mode'],
                            self.filter_settings['game_filter'].get('custom_ports'))
                if ports is not None:
                    game_filter['custom_ports'] = ports
            self._read_config_draft()
            options = dict(config_before=self.config_before, config_after=self.config_after,
                include_ipset=self.include_ipset.get(), include_hostlist=self.include_hostlist.get(),
                game_filter=game_filter, ipset_filter=self.ipset_mode.get() if self.ipset_mode else 'none',
                manager_dir=self.manager_dir)
            name = self.name_var.get()
            try:
                self.saved_preset_id = save_custom_preset(name, **options)
            except PresetExistsError as error:
                if not self.dialog(ask_yesno, 'Перезаписать пресет?',
                                   f'Пресет «{error.name}» уже существует. Заменить его текущими настройками?'):
                    return False
                self._read_config_draft()
                options.update(config_after=self.config_after, overwrite=True)
                self.saved_preset_id = save_custom_preset(name, **options)
                overwritten = True
        except (OSError, ValueError, UnicodeError) as error:
            self.dialog(show_error, 'Ошибка сохранения пресета', str(error))
            return False
        message = 'Пресет обновлён.' if overwritten else 'Пресет добавлен в список игр.'
        self.dialog(show_info, 'Пресет сохранён',
                    message + ' Выберите его в GameFilter → Включить пресет игры.')
        self.close()
        return True
