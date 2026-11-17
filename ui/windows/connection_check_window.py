#!/usr/bin/env python3

import tkinter as tk
import threading
import subprocess
import time
import os
import queue
from types import SimpleNamespace
from ui.components.button_styler import create_hover_button
from ui.components.window_navigation import prepare_window_navigation
from core.dpi_utils import place_toplevel_centered_on_parent
from core.connection_check import (YOUTUBE_PROBES, DISCORD_PROBES, INTERNET_PROBES,
                                   run_probe, interpret_results, connection_summary)

class ConnectionCheckWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.closed = threading.Event()
        self.checking = False
        self._local = threading.local()
        self._generation = 0
        self._events = queue.Queue()
        self._poll_after = None
        self._context = self._new_context()

    def _new_context(self):
        return SimpleNamespace(generation=self._generation, cancel=threading.Event(),
                               results=[], zapret_status=None, internet=[], youtube=[], discord=[])

    @property
    def context(self):
        return getattr(self._local, "context", self._context)

    @property
    def results(self):
        return self.context.results

    @property
    def zapret_status(self):
        return self.context.zapret_status

    @zapret_status.setter
    def zapret_status(self, value):
        self.context.zapret_status = value

    def _active(self):
        return not self.closed.is_set() and not self.context.cancel.is_set()

    def _drain_events(self):
        if self.closed.is_set():
            return
        for _ in range(200):
            try:
                generation, callback, args = self._events.get_nowait()
            except queue.Empty:
                break
            if generation == self._generation:
                callback(*args)
        self._poll_after = self.parent.after(30, self._drain_events)

    def run(self):
        """Запускает окно проверки соединения"""
        self.window = tk.Toplevel(self.parent)
        self.window.bind("<Destroy>", self._on_destroy, add="+")
        self.window.title("Проверка соединения")
        self.window.configure(bg='#182030')

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        prepare_window_navigation(self.window)
        self.setup_ui()
        self.window.update_idletasks()
        width = min(self.window.winfo_reqwidth(), self.window.winfo_screenwidth() - 32)
        height = min(self.window.winfo_reqheight(), self.window.winfo_screenheight() - 60)
        self.window.minsize(min(420, width), min(280, height))
        place_toplevel_centered_on_parent(
            self.window, self.parent, fixed_content_size=(width, height), immediate=True
        )

        if self.closed.is_set():
            return
        self.window.bind("<Escape>", lambda _event: self.on_close())
        self._drain_events()
        self.window.wait_window()

    def setup_ui(self):
        """Создает интерфейс окна"""
        main_frame = tk.Frame(self.window, bg='#182030', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(
            main_frame,
            text="Проверка сетевого соединения",
            font=("Arial", 14, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(fill=tk.X, pady=(0, 20))
        main_frame.bind("<Configure>", lambda event: title_label.configure(wraplength=max(100, event.width - 40)))

        # Область вывода результатов
        results_frame = tk.Frame(main_frame, bg='#182030')


        tk.Label(
            results_frame,
            text="Результаты проверки:",
            font=("Arial", 11),
            fg='#8e8e93',
            bg='#182030'
        ).pack(anchor=tk.W, pady=(0, 5))

        # Создаем ScrolledText для вывода
        self.results_text = tk.Text(
            results_frame,
            height=15,
            width=70,
            font=("Courier New", 10),
            bg='#15354D',
            fg='white',
            insertbackground='white',
            wrap=tk.WORD,
            highlightthickness=0,
            state='disabled'
        )
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(results_frame, command=self.results_text.yview)

        def update_scrollbar(first, last):
            scrollbar.set(first, last)
            if float(first) > 0 or float(last) < 1:
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                scrollbar.pack_forget()

        self.results_text.configure(yscrollcommand=update_scrollbar)

        # Панель управления
        control_frame = tk.Frame(main_frame, bg='#182030')
        control_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.summary_label = tk.Label(
            main_frame, text="Итог: проверка не запускалась.",
            font=("Arial", 11), fg="white", bg="#182030", justify=tk.LEFT, anchor=tk.W)
        self.summary_note = tk.Label(
            main_frame, text="Проверка веб-ресурсов. Видео YouTube и голос Discord не проверяются.",
            font=("Arial", 10), fg="#8e8e93", bg="#182030", justify=tk.LEFT, anchor=tk.W)
        self.summary_note.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 15))
        self.summary_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 5))
        # Reserve actions and summary before giving the remaining height to the log.
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        button_group = tk.Frame(control_frame, bg='#182030')
        button_group.pack(anchor=tk.CENTER)

        def wrap_summary(event):
            width = max(1, event.width - 40)
            self.summary_label.configure(wraplength=width)
            self.summary_note.configure(wraplength=width)

        main_frame.bind("<Configure>", wrap_summary, add="+")

        # Кнопки
        button_style = {
            'font': ('Arial', 11),
            'width': 22,
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 8,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Динамическая кнопка Запустить/Остановить
        self.toggle_button = create_hover_button(
            button_group,
            text="Запустить проверку",
            command=self.toggle_check,
            **button_style
        )
        self.toggle_button.pack(side=tk.LEFT, padx=(0, 15))

        # Кнопка назад
        self.back_button = create_hover_button(
            button_group,
            text="Назад",
            command=self.on_close,
            **button_style
        )
        self.back_button.pack(side=tk.LEFT)

        def layout_controls(event):
            needed = self.toggle_button.winfo_reqwidth() + self.back_button.winfo_reqwidth() + 15
            stacked = event.width < needed
            if getattr(self, '_controls_stacked', None) == stacked:
                return
            self._controls_stacked = stacked
            self.toggle_button.pack_forget()
            self.back_button.pack_forget()
            self.toggle_button.pack(side=tk.TOP if stacked else tk.LEFT,
                                    padx=(0, 0 if stacked else 15), pady=(0, 15 if stacked else 0))
            self.back_button.pack(side=tk.TOP if stacked else tk.LEFT)

        control_frame.bind('<Configure>', layout_controls)

    def toggle_check(self):
        """Переключает состояние проверки (запуск/остановка)"""
        if not self.checking:
            self.start_check()
        else:
            self.stop_check()

    def start_check(self):
        """Запускает проверку соединения"""
        if self.checking:
            return

        self.checking = True
        self._generation += 1
        self._context = self._new_context()

        # Обновляем текст кнопки
        self.toggle_button.config(text="Остановить проверку", bg='#15354D')

        # Очищаем результаты перед началом проверки
        self.clear_results()
        self._set_summary("Итог: выполняется проверка…")

        # Все операции с GUI должны выполняться в главном потоке
        self._start_check_ui()

        # Запускаем проверку в отдельном потоке
        thread = threading.Thread(target=self.run_checks, args=(self._context,))
        thread.daemon = True
        thread.start()

    def _start_check_ui(self):
        """Обновляет UI в главном потоке"""
        self.log_message("=" * 60, "#0a84ff")
        self.log_message("НАЧАЛО ПРОВЕРКИ СОЕДИНЕНИЯ", "#0a84ff")
        self.log_message("=" * 60, "#0a84ff")
        self.log_message(f"Время начала: {time.strftime('%H:%M:%S')}")
        self.log_message("")

    def _cancel_poll(self):
        if self._poll_after is not None:
            try:
                self.parent.after_cancel(self._poll_after)
            except tk.TclError:
                pass
            self._poll_after = None

    def _on_destroy(self, event):
        if event.widget is self.window:
            self._cancel_poll()
            self.closed.set()
            self._context.cancel.set()
            self.checking = False

    def _schedule_ui(self, callback, *args):
        """Workers only write Python data; the Tk thread drains the queue."""
        if not self.closed.is_set():
            self._events.put((self.context.generation, callback, args))

    def log_message(self, message, color='white'):
        """Добавляет сообщение в область вывода (безопасно для потоков)"""
        # Worker передаёт только данные в очередь главного потока.
        self._schedule_ui(self._log_message_thread_safe, message, color)

    def _log_message_thread_safe(self, message, color):
        """Безопасное добавление сообщения в главном потоке"""
        self.results_text.config(state='normal')
        self.results_text.insert(tk.END, f"{message}\n")

        # Применяем цвет через теги
        if color != 'white':
            start_index = self.results_text.index(f"end-{len(message)+2}c")  # +2 для символов \n
            end_index = self.results_text.index("end-1c")
            self.results_text.tag_add(color, start_index, end_index)
            self.results_text.tag_config(color, foreground=color)

        self.results_text.see(tk.END)
        self.results_text.config(state='disabled')

    def stop_check(self):
        """Останавливает проверку"""
        if self.checking:
            self._context.cancel.set()
            self.checking = False
            self.log_message("\n[!] Проверка остановлена пользователем", "#ff9500")
            # Обновляем кнопку немедленно
            self._schedule_ui(self._update_button_to_start)
            self._publish_summary()

    def _update_button_to_start(self):
        """Обновляет кнопку в состояние 'Запустить'"""
        self.toggle_button.config(text="Запустить проверку", bg='#15354D')

    def clear_results(self):
        """Очищает область результатов"""
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state='disabled')

    def run_checks(self, context=None):
        """Выполняет проверки соединения с отдельными данными каждого запуска."""
        self._local.context = context or self._context
        try:
            # Проверяем статус Zapret перед началом проверок
            self.zapret_status = self.check_zapret_status()

            # 1. Проверка локальной сети
            self.check_local_network()

            if not self._active():
                return

            # 2. Проверка интернет-соединения
            self.check_internet()

            if not self._active():
                return

            # 3. Проверка YouTube (специальные URL)
            self.check_youtube()

            if not self._active():
                return

            # 4. Проверка Discord
            self.check_discord()

            if not self._active():
                return

           # 5. Итоги
            self.show_summary()

        except Exception as e:
            self.log_message(f"\n[ОШИБКА] {str(e)}", "#ff3b30")
        finally:
            self._publish_summary()
            self._schedule_ui(self.on_check_complete)

    def check_zapret_status(self):
        """Проверяет статус службы Zapret"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "zapret"],
                capture_output=True,
                text=True,
                timeout=3
            )
            status = result.stdout.strip()
            return status
        except subprocess.TimeoutExpired:
            return "timeout"
        except Exception as e:
            return f"error: {str(e)}"

    def check_local_network(self):
        """Проверка локальной сети"""
        self.log_message("🔍 ПРОВЕРКА ЛОКАЛЬНОЙ СЕТИ:", "#0a84ff")

        try:
            # Проверка шлюза
            result = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=3
            )

            if result.stdout:
                lines = result.stdout.strip().split('\n')
                if lines and lines[0]:
                    parts = lines[0].split()
                    if len(parts) >= 3:
                        gateway = parts[2]
                        self.log_message(f"  📡 Шлюз по умолчанию: {gateway}", "#0a84ff")

                        # Пинг шлюза
                        ping_result = subprocess.run(
                            ["ping", "-c", "2", "-W", "1", gateway],
                            capture_output=True,
                            text=True,
                            timeout=4
                        )

                        if ping_result.returncode == 0:
                            self.log_message(f"  ✅ Шлюз доступен", "#30d158")
                            self.results.append(("Локальная сеть", "Шлюз", True))
                        else:
                            self.log_message(f"  ❌ Шлюз недоступен", "#ff3b30")
                            self.results.append(("Локальная сеть", "Шлюз", False))
                    else:
                        self.log_message("  ❌ Не удалось определить шлюз", "#ff3b30")
                else:
                    self.log_message("  ❌ Шлюз не найден", "#ff3b30")
            else:
                self.log_message("  ❌ Шлюз не найден", "#ff3b30")
                self.results.append(("Локальная сеть", "Шлюз", False))

        except Exception as e:
            self.log_message(f"  ❌ Ошибка: {str(e)}", "#ff3b30")
            self.results.append(("Локальная сеть", "Шлюз", False))

        self.log_message("")

    def _check_probes(self, category, probes):
        key = {"Интернет": "internet", "YouTube": "youtube", "Discord": "discord"}[category]
        results = getattr(self.context, key)
        for probe in probes:
            if not self._active():
                break
            result = run_probe(probe, self.context.cancel)
            results.append(result)
            if not self._active():
                break
            self.results.append((category, probe.name, result.success))
            color = '#30d158' if result.success else '#ff9500'
            self.log_message(f"  {probe.name}: {result.diagnosis} ({result.elapsed_ms:.0f} мс)", color)
            if result.final_url:
                self.log_message(f"    Конечный URL: {result.final_url}", '#8e8e93')
        return results

    def check_internet(self):
        self.log_message("🔍 ПРОВЕРКА ИНТЕРНЕТ-СОЕДИНЕНИЯ:", '#0a84ff')
        self._check_probes("Интернет", INTERNET_PROBES)
        self.log_message("")

    def _log_availability(self, category, results, count):
        state = interpret_results(results, count, not self._active())
        descriptions = {
            "available": ("Проверенные HTTP-ресурсы доступны", '#30d158'),
            "partial": ("Проверенные HTTP-ресурсы частично доступны", '#ff9500'),
            "unavailable": ("Проверенные HTTP-ресурсы недоступны", '#ff3b30'),
            "incomplete": ("Проверка не завершена", '#ff9500'),
        }
        message, color = descriptions[state]
        self.log_message(f"{category}: {message} ({sum(r.success for r in results)}/{count})", color)
        return state

    def check_discord(self):
        self.log_message("🔍 ПРОВЕРКА ДОСТУПА К DISCORD:", '#0a84ff')
        results = self._check_probes("Discord", DISCORD_PROBES)
        self._log_availability("Discord", results, len(DISCORD_PROBES))
        self.log_message("Голосовая связь Discord не проверялась.", '#8e8e93')
        self.log_message("")

    def check_youtube(self):
        self.log_message("🔍 ПРОВЕРКА HTTP-РЕСУРСОВ YOUTUBE:", '#0a84ff')
        self.context.youtube = self._check_probes("YouTube", YOUTUBE_PROBES)
        self.interpret_youtube_results()

    def interpret_youtube_results(self):
        state = self._log_availability("YouTube", self.context.youtube, len(YOUTUBE_PROBES))
        self.log_message("Сайт, generate_204 и изображения не подтверждают воспроизведение видео.", '#8e8e93')
        self.log_message("Видеопоток не проверялся. Ошибка запроса сама по себе не доказывает DPI-блокировку.", '#8e8e93')
        self.log_message("")
        return state

    def _set_summary(self, text):
        """Only called on the Tk thread, via the generation-filtered event queue."""
        self.summary_label.configure(text=text)

    def _publish_summary(self):
        context = self.context
        text = connection_summary(context.internet, context.youtube, context.discord)
        self._schedule_ui(self._set_summary, text)
        self.log_message(text, "#0a84ff")

    def show_summary(self):

        # Используем сохраненный статус Zapret
        zapret_is_active = self.zapret_status == "active" if self.zapret_status else False

        # Выводим информацию о состоянии службы Zapret
        self.log_message("")
        self.log_message("📊 ИНФОРМАЦИЯ О ZAPRET:", "#0a84ff")

        # Статус службы
        if zapret_is_active:
            self.log_message("✅ Служба Zapret: АКТИВНА", "#30d158")
        else:
            status_display = str(self.zapret_status).upper() if self.zapret_status else 'НЕ АКТИВНА'
            self.log_message(f"❌ Служба Zapret: {status_display}", "#ff3b30")

        # Получаем выбранную стратегию
        try:
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
            name_strategy_file = os.path.join(manager_dir, "utils", "name_strategy.txt")

            if os.path.exists(name_strategy_file):
                with open(name_strategy_file, 'r', encoding='utf-8') as f:
                    strategy_name = f.read().strip()
                    if strategy_name:
                        self.log_message(f"📋 Стратегия: {strategy_name}", "#0a84ff")
                    else:
                        self.log_message("📋 Стратегия: Не выбрана", "#ff9500")
            else:
                self.log_message("📋 Стратегия: Файл стратегии не найден", "#ff9500")
        except Exception as e:
            self.log_message(f"📋 Стратегия: Ошибка чтения ({str(e)})", "#ff3b30")

    def on_check_complete(self):
        """Вызывается при завершении проверки"""
        self.checking = False
        # Обновляем кнопку обратно в состояние "Запустить проверку"
        self.toggle_button.config(text="Запустить проверку", bg='#15354D')

    def on_close(self):
        """Закрывает окно"""
        self._cancel_poll()
        self.closed.set()
        self._context.cancel.set()
        self.checking = False
        if self.window:
            self.window.destroy()
    def log_full_response(self, response):
        """Логирование полного ответа для отладки"""
        self.log_message(f"    Status: {response.status}", "#8e8e93")
        self.log_message(f"    Reason: {response.reason}", "#8e8e93")
        headers = response.getheaders()
        for header, value in headers[:5]:  # Первые 5 заголовков
            self.log_message(f"    {header}: {value}", "#8e8e93")
