"""Strategy settings hub; imports use the system chooser immediately."""
import os
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from core.dpi_utils import application_tk_root, place_toplevel_centered_on_parent
from core.kate_editor import KateEditorSession
from core.strategy_import import StrategyImporter, ReplacementRequired
from core.strategy_settings import ConfigDocument, registered_payloads, fake_slots, replace_fakes, restart_zapret, current_payload_label
from core.tk_scale_lab_helpers import logical_ui_scale, warning_dialog_scale
from ui.components.button_styler import create_hover_button, uniform_button_width_for_font
from ui.components.custom_messagebox import ask_yesno, show_error, show_info
from ui.components.file_picker import ask_open_file
from ui.components.responsive_buttons import pack_responsive_buttons
from ui.components.window_navigation import prepare_window_navigation, run_child_window
from ui.windows.sudo_password_window import SudoPasswordWindow


class SettingsWindow:
    def setup(self, title, width=530, height=400, *, place_window=True, scrollable=False):
        anchor = application_tk_root(self.parent) or self.parent
        logical = float(logical_ui_scale(anchor))
        self._anchor = anchor
        scale = max(float(warning_dialog_scale(anchor)), logical)
        self.s = lambda n: max(1, round(n * scale))
        # Tk scales point sizes itself, as in the existing IPSet menus.
        self.font = ('Arial', 11)
        self.window = tk.Toplevel(self.parent)
        self.window.withdraw()
        self.window.title(title)
        self.window.configure(bg='#182030')
        self.window.transient(anchor)
        body_parent = self.window
        if scrollable:
            self._layout_ready = False
            self.footer = tk.Frame(self.window, bg='#182030', padx=self.s(20), pady=self.s(15))
            self.footer.pack(side=tk.BOTTOM, fill=tk.X)
            viewport = tk.Frame(self.window, bg='#182030')
            viewport.pack(fill=tk.BOTH, expand=True)
            self._canvas = tk.Canvas(viewport, bg='#182030', bd=0, highlightthickness=0,
                                     width=self.s(480), height=1)
            self._scrollbar = tk.Scrollbar(viewport, command=self._canvas.yview)
            self._canvas.pack(fill=tk.BOTH, expand=True)
            self._canvas.configure(yscrollcommand=self._scrollbar.set)
            body_parent = self._canvas
        self.body = tk.Frame(body_parent, bg='#182030', padx=self.s(20), pady=self.s(15))
        if scrollable:
            self._body_item = self._canvas.create_window((0, 0), window=self.body, anchor='nw')
            self._canvas.bind('<Configure>', self._resize_body)
            self.body.bind('<Configure>', self._update_scroll)
            self.window.bind('<Button-4>', lambda event: self._canvas.yview_scroll(-1, 'units'))
            self.window.bind('<Button-5>', lambda event: self._canvas.yview_scroll(1, 'units'))
            self.window.bind('<MouseWheel>', lambda event: self._canvas.yview_scroll(-int(event.delta / 120), 'units'))
        else:
            self.body.pack(fill=tk.BOTH, expand=True)
        self.style = dict(font=self.font, bg='#15354D', fg='white', bd=0,
                          padx=self.s(10), pady=self.s(8), highlightthickness=0, cursor='hand2')
        self.heading = tk.Label(self.body, text=title, bg='#182030', fg='white',
                                font=('Arial', 14, 'bold'), wraplength=self.s(470))
        self.heading.pack(fill=tk.X, pady=(0, self.s(20)))
        self.heading.bind('<Configure>', lambda event: self.heading.configure(wraplength=max(40, event.width))
                          if getattr(self, '_layout_ready', True) else None)
        self._labels = [self.heading]
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        prepare_window_navigation(self.window)
        self.window.bind('<Escape>', lambda event: self.close())
        if place_window:
            dimensions = (min(self.s(width), self.window.winfo_screenwidth() - 32),
                          min(self.s(height), self.window.winfo_screenheight() - 80))
            place_toplevel_centered_on_parent(self.window, anchor, fixed_content_size=dimensions, immediate=True)

    def label(self, text, *, muted=False):
        label = tk.Label(self.body, text=text, bg='#182030', fg='#AAAAAA' if muted else 'white',
                         font=('Arial', 10) if muted else self.font,
                         wraplength=self.s(470), justify=tk.LEFT, anchor=tk.W)
        label.pack(fill=tk.X, pady=(0, self.s(12)))
        label.bind('<Configure>', lambda event: label.configure(wraplength=max(100, event.width))
                   if getattr(self, '_layout_ready', True) else None)
        self._labels.append(label)
        return label

    def _resize_body(self, event):
        if not self._layout_ready:
            return
        self._canvas.itemconfigure(self._body_item, width=event.width)
        self._update_scroll()

    def _update_scroll(self, event=None):
        if not self._layout_ready:
            return
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))
        overflow = self.body.winfo_reqheight() > self._canvas.winfo_height() + 1
        if overflow and not self._scrollbar.winfo_manager():
            self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self._canvas)
        elif not overflow and self._scrollbar.winfo_manager():
            self._scrollbar.pack_forget()
            self._canvas.yview_moveto(0)

    def fit_scrollable_content(self, width=530):
        """Fit a settings form to its contents, keeping actions outside scrolling."""
        self.window.update_idletasks()
        max_width = max(1, self.window.winfo_screenwidth() - 32)
        max_height = max(1, self.window.winfo_screenheight() - 80)
        width = min(self.s(width) if width is not None else self.body.winfo_reqwidth() + self.s(8), max_width)
        self._canvas.configure(width=width)
        self._canvas.itemconfigure(self._body_item, width=width)
        for label in self._labels:
            label.configure(wraplength=max(40, width - self.s(40)))
        # Measure wrapping at the actual viewport width before sizing height.
        self.window.update_idletasks()
        arrange_actions = getattr(self, '_arrange_actions', None)
        if arrange_actions is not None:
            arrange_actions(width=width)
        self.window.update_idletasks()
        available = max(1, max_height - self.footer.winfo_reqheight())
        if self.body.winfo_reqheight() > available:
            self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self._canvas)
            content_width = max(1, width - self._scrollbar.winfo_reqwidth())
            self._canvas.configure(width=content_width)
            self._canvas.itemconfigure(self._body_item, width=content_width)
            for label in self._labels:
                label.configure(wraplength=max(40, content_width - self.s(40)))
            self.window.update_idletasks()
        height = min(self.body.winfo_reqheight(), available)
        self._canvas.configure(height=height)
        self.window.update_idletasks()
        place_toplevel_centered_on_parent(
            self.window, self._anchor,
            fixed_content_size=(width, min(height + self.footer.winfo_reqheight(), max_height)),
            immediate=True)
        self._layout_ready = True
        self._update_scroll()

    def button(self, text, command, **pack):
        button = create_hover_button(self.body, text=text, command=command, **self.style)
        button.pack(pady=self.s(5), **pack)
        return button

    def close(self):
        self.window.destroy()

    def dialog(self, action, *args):
        try:
            return action(self.window, *args)
        finally:
            try:
                if self.window.winfo_exists():
                    self.window.grab_set()
                    self.window.focus_set()
            except tk.TclError:
                pass

    def run(self):
        self.create_window()
        self.window.grab_set()
        self.window.focus_set()
        prepare_window_navigation(self.window)
        self.window.wait_window()


class StrategyImportWindow(SettingsWindow):
    """Historical public name retained for existing menu integration."""
    def __init__(self, parent, importer=None, config_path=None):
        self.parent = parent
        self.importer = importer or StrategyImporter()
        self.config_path = config_path
        self.window = None
        self._config_editor = None

    def create_window(self):
        self.setup('Настройка стратегий', place_window=False, scrollable=True)
        # Match IpsetMainWindow exactly: Tk scales the point fonts, while
        # its compact menu padding/gaps are pixel values, not dialog geometry.
        self.font = ('Arial', 11)
        self.body.configure(padx=10, pady=10)
        self.footer.configure(padx=10, pady=10)
        self.heading.configure(font=('Arial', 14, 'bold'))
        self.heading.pack_configure(pady=(0, 30))
        actions = [('Добавить стратегию', self.convert_strategy),
                   ('Добавить новый BIN (фейк)', self.add_bin),
                   ('Открыть config', self.open_config),
                   ('Замена используемого фейка', self.open_fakes)]
        # Match the compact, centered menu in IpsetMainWindow.
        menu_style = dict(self.style, font=self.font, padx=10, pady=8, width=max(
            32, uniform_button_width_for_font(self.body, self.font, *[text for text, _ in actions]),
        ))
        for index, (caption, action) in enumerate(actions):
            create_hover_button(self.body, text=caption, command=action,
                                **menu_style).pack(pady=(0, 15 if index < len(actions) - 1 else 5))
        create_hover_button(self.footer, text='Назад', command=self.close,
                            **dict(menu_style, width=20)).pack()
        self.fit_scrollable_content(width=None)
        return self.window

    def _import(self, is_bin):
        suffix = '.bin' if is_bin else '.bat'
        source = ask_open_file(self.window, title='Выберите файл BIN (фейк)' if is_bin else 'Выберите файл BAT',
                               suffix=suffix, initialdir=getattr(self, '_last_directory', Path.home()))
        if not source:
            return
        self._last_directory = Path(source).parent
        action = self.importer.add_bin if is_bin else self.importer.convert
        overwrite = False
        password = None
        while True:
            try:
                kwargs = {'overwrite': overwrite}
                if password is not None:
                    kwargs['password'] = password
                result = action(Path(source), **kwargs)
                self.dialog(show_info, 'Готово',
                          ('Новый BIN (фейк) добавлен' if is_bin else 'Новая стратегия добавлена в список') + f'\n{result}')
                return
            except ReplacementRequired as error:
                if not self.dialog(ask_yesno, 'Замена файла', str(error)):
                    return
                overwrite = True
            except PermissionError:
                if not is_bin or password is not None:
                    self.dialog(show_error, 'Ошибка импорта', 'Нет прав на запись файлов.')
                    return
                password = self.dialog(lambda parent: SudoPasswordWindow(parent).run())
                if password is None:
                    return
            except (OSError, ValueError) as error:
                self.dialog(show_error, 'Ошибка импорта', str(error))
                return

    def convert_strategy(self):
        self._import(False)

    def add_bin(self):
        self._import(True)

    def _open(self, cls):
        try:
            return run_child_window(self.window, lambda: cls(
                self.window, root=self.importer.root, config_path=self.config_path,
                installed_starter=self.importer.installed_starter).run())
        except (OSError, ValueError, UnicodeError) as error:
            self.dialog(show_error, 'Ошибка config', str(error))

    def open_config(self):
        if self._config_editor is not None and self._config_editor._running:
            return
        try:
            editor = KateConfigEditor(self.window, root=self.importer.root,
                                      config_path=self.config_path)
            editor.run()
            self._config_editor = editor
        except (OSError, ValueError) as error:
            self.dialog(show_error, 'Ошибка открытия config', str(error))

    def open_fakes(self):
        self._open(FakeSelectionWindow)


class ConfigWindow(SettingsWindow):
    def __init__(self, parent, root=None, config_path=None, installed_starter='/opt/zapret/starter.sh'):
        self.parent = parent
        self.document = ConfigDocument(config_path, root, installed_starter)
        self.installed_starter = installed_starter

    def action_buttons(self, caption, command):
        footer = getattr(self, 'footer', None)
        if footer is None:
            footer = tk.Frame(self.body, bg='#182030')
            footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(self.s(10), 0))
        style = dict(self.style, width=max(
            12, uniform_button_width_for_font(footer, self.font, caption, 'Назад'),
        ))
        buttons = [create_hover_button(footer, text=text, command=action, **style)
                   for text, action in ((caption, command), ('Назад', self.close))]
        self._arrange_actions = pack_responsive_buttons(footer, buttons, gap=15)

    def saved(self, changed):
        if not changed or not self.document.active:
            return
        if not self.dialog(ask_yesno, 'Config сохранён', 'Изменения сохранены. Перезапустить Zapret для применения?'):
            return
        password = None
        if os.geteuid() != 0:
            password = self.dialog(lambda parent: SudoPasswordWindow(parent).run())
            if password is None:
                return
        try:
            restart_zapret(password)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            previous = getattr(self.document, 'previous', None)
            if previous is None:
                self.dialog(show_error, 'Ошибка применения', f'Перезапуск не удался. Проверьте config и состояние службы.\n{error}')
                return
            try:
                self.document.save_bytes(previous)
                if hasattr(self, 'fields'):
                    restored_slots = fake_slots(self.document.text, self.document.root)
                    for kind, (variable, _slot) in list(self.fields.items()):
                        slot = restored_slots[kind]
                        label = next((label for label, alias in self.display_aliases.items()
                                      if alias == slot.current_alias), None)
                        if label is not None:
                            variable.set(label)
                        self.fields[kind] = (variable, slot)
            except (OSError, ValueError) as restore_error:
                self.dialog(show_error, 'Ошибка применения', f'{error}\nНе удалось восстановить прежний config: {restore_error}')
                return
            if isinstance(error, (ValueError, FileNotFoundError, PermissionError)):
                self.dialog(show_error, 'Ошибка применения', f'{error}\nПрежний config восстановлен; перезапуск не выполнялся.')
                return
            try:
                restart_zapret(password)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as restore_error:
                self.dialog(show_error, 'Ошибка применения', f'{error}\nПрежний config восстановлен, но восстановить запуск не удалось: {restore_error}')
            else:
                self.dialog(show_error, 'Ошибка применения', f'{error}\nПрежний config и запуск восстановлены.')


class KateConfigEditor(ConfigWindow):
    """Watch Kate saves on the Tk event loop while keeping the settings menu open."""
    def __init__(self, parent, root=None, config_path=None):
        super().__init__(parent, root=root, config_path=config_path)
        self.window = parent
        self.session = KateEditorSession(self.document)
        self._running = False
        self._timer = None
        self._destroy_binding = None
        self._pending_change = False

    def run(self):
        self.session.start()
        self._running = True
        self._destroy_binding = self.window.bind('<Destroy>', self._on_destroy, add='+')
        self._schedule_poll()

    def _schedule_poll(self):
        if self._running:
            self._timer = self.window.after(500, self._poll)

    def _can_notify(self):
        if self.window.state() in ('withdrawn', 'iconic'):
            return False
        grab = self.window.grab_current()
        return grab is None or grab == self.window

    def _poll(self):
        self._timer = None
        if not self._running:
            return
        if not self.window.winfo_exists():
            self._stop()
            return
        error = None
        try:
            # Kate can replace the file atomically, so compare its actual bytes.
            if self.session.check_saved():
                self.document = self.session.document
                self._pending_change = True
        except (OSError, ValueError) as exception:
            # An incomplete save can be transient. Report it only after Kate exits.
            error = str(exception)
        code = self.session.poll()
        can_notify = self._can_notify()
        if self._pending_change and error is None and can_notify:
            self._pending_change = False
            self.saved(True)
            if not self._running or not self.window.winfo_exists():
                return
        if code is not None:
            if not can_notify and (self._pending_change or error or code):
                self._schedule_poll()
                return
            self._stop()
            if error:
                self.dialog(show_error, 'Ошибка config', error)
            elif code:
                self.dialog(show_error, 'Ошибка Kate', 'Kate завершился с ошибкой. Проверьте сохранение config.')
        else:
            self._schedule_poll()

    def _on_destroy(self, event):
        if event.widget == self.window:
            self._stop()

    def _stop(self):
        self._running = False
        try:
            if self._timer is not None:
                self.window.after_cancel(self._timer)
            if self._destroy_binding is not None:
                self.window.unbind('<Destroy>', self._destroy_binding)
        except tk.TclError:
            pass
        self._timer = None
        self._destroy_binding = None

    def close(self):
        # Kate owns its documents/unsaved-change prompt and must remain open.
        self._stop()


ConfigEditorWindow = KateConfigEditor


class FakeSelectionWindow(ConfigWindow):
    def create_window(self):
        self.payloads = registered_payloads(self.document.root, self.installed_starter)
        self.setup('Замена используемого фейка', place_window=False, scrollable=True)
        self.label('Поддерживаются только Discord UDP (Voice) и GameFilter UDP.\nИзменяется только выбранный config:\n' + str(self.document.path), muted=True)
        self.fields = {}
        slots = fake_slots(self.document.text, self.document.root)
        self.display_aliases = {p.filename: p.alias for p in self.payloads if not p.filename.startswith('ACTIVE_')}
        for kind, title in [('discord', 'Discord UDP (Voice)'), ('game', 'GameFilter UDP')]:
            self.label(title)
            slot = slots[kind]
            default_alias = 'ACTIVE_DISCORD_UDP' if kind == 'discord' else 'ACTIVE_GAME_UDP'
            default_label = None
            if default_alias in {p.alias for p in self.payloads}:
                default_label = current_payload_label(default_alias, self.payloads, self.document.root)
                self.display_aliases[default_label] = default_alias
            value = current_payload_label(slot.current_alias, self.payloads, self.document.root) if slot.current_alias else ''
            if slot.current_alias in {p.alias for p in self.payloads}:
                self.display_aliases[value] = slot.current_alias
            variable = tk.StringVar(self.window, value=value)
            combo = ttk.Combobox(self.body, textvariable=variable, values=[p.filename for p in self.payloads if not p.filename.startswith('ACTIVE_')] + ([default_label] if default_label else []),
                                 state='readonly' if slot.enabled and self.payloads else 'disabled', font=self.font)
            combo.pack(fill=tk.X, pady=(0, self.s(8)))
            self.fields[kind] = (variable, slot)
            if slot.reason:
                self.label(slot.reason, muted=True)
        self.action_buttons('Применить', self.apply)
        self.fit_scrollable_content()
        return self.window

    def apply(self):
        try:
            # Recheck files and installed mappings immediately before committing.
            payloads = registered_payloads(self.document.root, self.installed_starter)
            available = {p.alias for p in payloads}
            names = {label: alias for label, alias in self.display_aliases.items() if alias in available}
            selections = {}
            for kind, (variable, slot) in self.fields.items():
                if slot.enabled:
                    value = variable.get()
                    if value not in names:
                        if value.startswith('{' + str(slot.current_alias) + '}'):
                            continue
                        raise ValueError('Выбранный BIN отсутствует или больше не зарегистрирован.')
                    selections[kind] = names[value]
            text = replace_fakes(self.document.text, selections, payloads, self.document.root)
            self.document.installed_starter = self.installed_starter
            changed = self.document.save_bytes(text.encode('utf-8'))
        except (OSError, ValueError, UnicodeError) as error:
            self.dialog(show_error, 'Ошибка замены', str(error))
            return False
        self.saved(changed)
        return True


StrategySettingsWindow = StrategyImportWindow
