import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import sys
import asyncio
import io
import contextlib
from pathlib import Path
from ui.components.button_styler import create_hover_button
from core.dpi_utils import place_toplevel_centered_on_parent
from ui.windows.sudo_password_window import SudoPasswordWindow
from datetime import datetime, timedelta


# Добавляем путь к core для импорта strategy_tester
sys.path.append(str(Path(__file__).parent.parent.parent / 'core'))

class OutputRedirector:
    """Перенаправляет вывод print в GUI окно"""
    def __init__(self, log_callback):
        self.log_callback = log_callback
        self.buffer = io.StringIO()

    def write(self, text):
        self.buffer.write(text)
        # Отправляем текст в GUI
        if text.strip():
            self.log_callback(text.rstrip())

    def flush(self):
        pass

    def get_value(self):
        return self.buffer.getvalue()

class StrategyTesterWindow:
    def __init__(self, parent, strategies_to_test=None):
        home_dir = os.path.expanduser("~")
        project_root = os.path.join(home_dir, "Zapret_DPI_Manager")
        self.parent = parent
        self.project_root = Path(project_root)
        self.strategies_to_test = strategies_to_test  # Сохраняем переданные стратегии
        self.window = None
        self.testing = False
        self.results = []
        self.current_tester = None
        self.current_password = None

        # Добавить эти переменные для таймеров
        self.start_time = None
        self.elapsed_time = 0
        self.total_estimated_time = 0

        # Пытаемся импортировать StrategyTester
        self.StrategyTester = None
        self.test_all_strategies = None
        self.test_button = None

        try:
            from strategy_tester import StrategyTester as ST, test_all_strategies as tas
            self.StrategyTester = ST
            self.test_all_strategies = tas
        except ImportError as e:
            print(f"Warning: Could not import strategy_tester: {e}")

    def run(self):
        """Запускает окно тестировщика стратегий"""
        if not self.StrategyTester:
            messagebox.showerror("Ошибка", "Не удалось загрузить модуль тестировщика стратегий")
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Автоподбор стратегий")
        self.window.configure(bg='#182030')

        self.setup_ui()
        place_toplevel_centered_on_parent(
            self.window, self.parent, min_width=560, min_height=420, margin_width=8, margin_height=12
        )

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.mainloop()



    def setup_ui(self):
        """Создает интерфейс окна"""
        main_frame = tk.Frame(self.window, bg='#182030', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(
            main_frame,
            text="Автоподбор стратегий Zapret DPI",
            font=("Arial", 16, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(pady=(0, 10))

        # Настройки тестирования
        settings_frame = tk.LabelFrame(
            main_frame,
            fg='#4fc3f7',
            bg='#182030',
            relief=tk.FLAT,
            bd=1,
            highlightbackground='#2A3B5C',
            highlightthickness=0
        )
        settings_frame.pack(fill=tk.X, pady=(0, 0), ipadx=10, ipady=0)

        # Режим тестирования
        mode_frame = tk.Frame(settings_frame, bg='#182030')
        mode_frame.pack(fill=tk.X, pady=(5, 10))

        tk.Label(
            mode_frame,
            text="Режим тестирования:",
            font=("Arial", 10),
            fg='white',
            bg='#182030'
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.mode_var = tk.StringVar(value="standard")

        # Режим Стандартный
        tk.Radiobutton(
            mode_frame,
            text="Стандартный",
            variable=self.mode_var,
            value="standard",
            font=("Arial", 10),
            fg='white',
            bg='#182030',
            highlightthickness=0,
            activebackground='#182030',
            activeforeground='#4fc3f7',
            selectcolor='#182030',
            cursor='hand2'
        ).pack(side=tk.LEFT, padx=(0, 20))

        # Режим YouTube/Discord
        tk.Radiobutton(
            mode_frame,
            text="YouTube/Discord",
            variable=self.mode_var,
            value="YouTube/Discord",
            font=("Arial", 10),
            fg='white',
            bg='#182030',
            highlightthickness=0,
            activebackground='#182030',
            activeforeground='#4fc3f7',
            selectcolor='#182030',
            cursor='hand2'
        ).pack(side=tk.LEFT)

        # Область вывода результатов
        results_frame = tk.Frame(main_frame, bg='#182030')
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        tk.Label(
            results_frame,
            text="Лог тестирования:",
            font=("Arial", 11),
            fg='#8e8e93',
            bg='#182030'
        ).pack(anchor=tk.W, pady=(0, 5))

        # Текстовое поле для логов (как в connection_check_window)
        self.results_text = tk.Text(
            results_frame,
            height=15,
            font=("Courier New", 9),
            bg='#15354D',
            fg='white',
            insertbackground='white',
            wrap=tk.WORD,
            highlightthickness=0,
            state='disabled'
        )

        # Размещаем элементы
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Панель управления
        control_frame = tk.Frame(main_frame, bg='#182030')
        control_frame.pack(fill=tk.X, pady=(0, 0))

        # Кнопки
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 8,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Создаем левый фрейм для основных кнопок
        left_buttons_frame = tk.Frame(control_frame, bg='#182030')
        left_buttons_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Создаем правый фрейм для кнопки "Назад"
        right_buttons_frame = tk.Frame(control_frame, bg='#182030')
        right_buttons_frame.pack(side=tk.RIGHT)

        # Кнопка запуска и остановки теста (левая сторона)
        self.test_button = create_hover_button(
            left_buttons_frame,
            text="▶ Запустить тест",
            command=self.toggle_test,
            **button_style
        )
        self.test_button.pack(side=tk.LEFT, padx=(0, 10))

        # Кнопка очистки лога (левая сторона)
        clear_button = create_hover_button(
            left_buttons_frame,
            text="🗑 Очистить лог",
            command=self.clear_log,
            font=('Arial', 11),  # Изменено с 10 на 11 для единого стиля
            bg='#15354D',  # Изменено с зеленого на синий
            fg='white',
            bd=0,
            padx=15,
            pady=8  # Высота 20px
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 10))

        # Кнопка открытия отчета (левая сторона)
        self.report_button = create_hover_button(
            left_buttons_frame,
            text="📄 Отчет",
            command=self.open_report,
            font=('Arial', 11),  # Изменено с 10 на 11
            bg='#15354D',  # Изменено с зеленого на синий
            fg='white',
            bd=0,
            padx=15,
            pady=8  # Высота 20px
        )
        self.report_button.pack(side=tk.LEFT, padx=(0, 10))
        self.report_button.config(state=tk.DISABLED)

        # Кнопка назад (правая сторона)
        back_button = create_hover_button(
            right_buttons_frame,
            text="Назад",
            command=self.on_close,
            **button_style
        )
        back_button.pack(side=tk.RIGHT)

    def toggle_test(self):
        """Переключает состояние тестирования"""
        if not self.testing:
            self.start_test()  # Запускаем тест
        else:
            self.stop_test()   # Останавливаем тест

    def log_message(self, message, color='white'):
        """Добавляет сообщение в область вывода (безопасно для потоков)"""
        # Используем after для безопасного обновления GUI из другого потока
        self.window.after(0, self._log_message_thread_safe, message, color)

    def _log_message_thread_safe(self, message, color):
        """Безопасное добавление сообщения в главном потоке"""
        self.results_text.config(state='normal')

        # Вставляем сообщение
        self.results_text.insert(tk.END, f"{message}\n")

        # Применяем цвет через теги
        if color != 'white':
            # Вычисляем позиции для тега
            start_index = self.results_text.index(f"end-{len(message)+2}c")
            end_index = self.results_text.index("end-1c")

            # Создаем уникальное имя тега
            tag_name = f"color_{color.replace('#', '')}"
            self.results_text.tag_add(tag_name, start_index, end_index)
            self.results_text.tag_config(tag_name, foreground=color)

        # Прокручиваем вниз
        self.results_text.see(tk.END)
        self.results_text.config(state='disabled')
        self.window.update_idletasks()

    def clear_log(self):
        """Очищает область лога"""
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state='disabled')

    def get_current_strategy(self):
        """Получает имя текущей стратегии из файла"""
        strategy_name = None
        try:
            # Проверяем файл name_strategy.txt
            strategy_file = self.project_root / "utils" / "name_strategy.txt"
            if strategy_file.exists():
                with open(strategy_file, 'r', encoding='utf-8') as f:
                    strategy_name = f.read().strip()

            # Если не найдено, получаем первую доступную стратегию
            if not strategy_name:
                tester = self.StrategyTester(self.project_root)
                strategies = tester.get_available_strategies()
                if strategies:
                    strategy_name = strategies[0]

        except Exception as e:
            self.log_message(f"Ошибка получения стратегии: {str(e)}", "#ff3b30")

        return strategy_name

    def start_test(self):
        """Запускает тестирование"""
        if self.testing:
            return

        # Запрашиваем пароль sudo
        password_window = SudoPasswordWindow(self.window)
        password = password_window.run()

        if not password:
            self.log_message("❌ Тестирование отменено: не введен пароль sudo", "#ff3b30")
            return

        # Меняем состояние кнопок
        self.testing = True
        self.test_button.config(text="⏹ Остановить тест")  # Изменяем текст кнопки
        self.report_button.config(state=tk.DISABLED)

        # Очищаем лог
        self.clear_log()

        # Оцениваем общее время (примерно 30 секунд на стратегию)
        tester = self.StrategyTester(self.project_root, password)
        all_strategies = tester.get_available_strategies()
        estimated_time = len(all_strategies) * 30 if all_strategies else 300  # 5 минут по умолчанию

        # Выводим информацию о начале тестирования
        self.log_message("=" * 60, "#4fc3f7")
        self.log_message("🚀 ТЕСТИРОВАНИЕ ВСЕХ СТРАТЕГИЙ", "#4fc3f7")
        self.log_message(f"🎯 РЕЖИМ: {self.mode_var.get().upper()}", "#4fc3f7")
        self.log_message(f"⏰ ВРЕМЯ: {time.strftime('%H:%M:%S')}", "#4fc3f7")
        self.log_message("=" * 60, "#4fc3f7")
        self.log_message("")

        # Запускаем тестирование в отдельном потоке
        thread = threading.Thread(
            target=self.run_test_thread,
            args=(password,),  # Только один аргумент - пароль
            daemon=True
        )
        thread.start()

    def stop_test(self):
        """Останавливает тестирование"""
        if self.testing:
            self.testing = False

            # Меняем кнопку обратно
            self.test_button.config(text="▶ Запустить тест")

            self.log_message("\n⚠️  Остановка тестирования...", "#ff9500")

            # Останавливаем тестировщик, если он существует
            if hasattr(self, 'current_tester') and self.current_tester:
                try:
                    self.current_tester.stop_testing()
                    self.log_message("✓ Запрос на остановку отправлен...", "#30d158")
                except Exception as e:
                    self.log_message(f"⚠️  Ошибка при остановке: {str(e)}", "#ff9500")


    def run_test_thread(self, sudo_password):
        """Запускает тестирование в отдельном потоке"""
        old_stdout = None
        try:
            # Сохраняем пароль для использования в командах
            self.current_password = sudo_password

            # Получаем выбранный режим
            mode = self.mode_var.get()

            # Создаем перехватчик вывода
            redirector = OutputRedirector(self.log_message)

            # Перенаправляем stdout для этого потока
            old_stdout = sys.stdout
            sys.stdout = redirector

            # Создаем новую asyncio loop для потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Создаем тестировщик и сохраняем ссылку
            tester = self.StrategyTester(self.project_root, sudo_password)
            self.current_tester = tester  # Сохраняем для остановки

            # Получаем стратегии для тестирования
            if self.strategies_to_test:
                # Используем переданные стратегии
                strategies_to_test = self.strategies_to_test
                self.log_message(f"🎯 Будет протестировано выбранных стратегий: {len(strategies_to_test)}", "#4fc3f7")
            else:
                # Получаем ВСЕ стратегии для тестирования
                strategies_to_test = tester.get_available_strategies()
                self.log_message(f"📋 Найдено стратегий для тестирования: {len(strategies_to_test)}", "#4fc3f7")

            if not strategies_to_test:
                self.log_message("❌ Не найдено стратегий для тестирования", "#ff3b30")
                return

            # Запускаем ПОЛНОЕ тестирование всех стратегий
            results = loop.run_until_complete(
                tester.run_full_test(mode, strategies_to_test,
                                    stop_callback=lambda: not self.testing)  # Добавляем callback
            )

            # Проверяем, была ли остановка
            if not self.testing:
                self.window.after(0, self.log_message, "\n⏹️ Тестирование остановлено пользователем", "#ff9500")
                return

            # Восстанавливаем stdout
            sys.stdout = old_stdout

            if results and len(results) > 0:
                # Классифицируем стратегии в зависимости от режима
                mode = self.mode_var.get()

                if mode == "YouTube/Discord":
                    # РЕЖИМ YouTube/Discord - классификация только по критическим тестам
                    good_results = []      # Оба работают
                    partial_results = []   # Только один работает
                    bad_results = []       # Оба не работают

                    for result in results:
                        youtube_passed = result.get('youtube_passed', False)
                        discord_passed = result.get('discord_passed', False)
                        success_rate = result.get('success_rate', 0)

                        if youtube_passed is True and discord_passed is True:
                            # Оба работают - хорошая стратегия
                            good_results.append(result)
                            result["status"] = "good"
                        elif (youtube_passed is True and discord_passed is False) or \
                            (youtube_passed is False and discord_passed is True):
                            # Только один работает - частичная стратегия
                            partial_results.append(result)
                            result["status"] = "partial"

                            # Определяем причину частичной работы
                            if youtube_passed and not discord_passed:
                                result["partial_reason"] = "YouTube работает, Discord нет"
                            elif not youtube_passed and discord_passed:
                                result["partial_reason"] = "Discord работает, YouTube нет"
                        else:
                            # Оба не работают или не проверялись - плохая стратегия
                            bad_results.append(result)
                            result["status"] = "bad"

                            if youtube_passed is False and discord_passed is False:
                                result["bad_reason"] = "YouTube и Discord не работают"
                            else:
                                result["bad_reason"] = "Не удалось определить статус"
                else:
                    # СТАНДАРТНЫЙ РЕЖИМ - старая логика
                    good_results = []      # Оба работают + ≥60%
                    partial_results = []   # Только один работает + ≥60%
                    bad_results = []       # Оба не работают или <60%

                    for result in results:
                        success_rate = result.get('success_rate', 0)
                        youtube_passed = result.get('youtube_passed', False)
                        discord_passed = result.get('discord_passed', False)
                        critical_fail = result.get('critical_fail', False)
                        critical_reason = result.get('critical_fail_reason', '')

                        if success_rate >= 60:
                            if youtube_passed and discord_passed:
                                good_results.append(result)
                                result["status"] = "good"
                            elif youtube_passed or discord_passed:
                                partial_results.append(result)
                                result["status"] = "partial"
                                # Определяем причину частичной работы
                                if youtube_passed and not discord_passed:
                                    result["partial_reason"] = "YouTube работает, Discord нет"
                                elif not youtube_passed and discord_passed:
                                    result["partial_reason"] = "Discord работает, YouTube нет"
                            else:
                                bad_results.append(result)
                                result["status"] = "bad"
                                result["bad_reason"] = "YouTube и Discord не работают"
                        else:
                            bad_results.append(result)
                            result["status"] = "bad"
                            result["bad_reason"] = f"Низкая эффективность ({success_rate:.1f}% < 60%)"

                # Анализируем результаты
                successful_tests = sum(r.get('successful', 0) for r in results)
                total_tests = sum(r.get('total_targets', 0) for r in results)

                self.log_message("\n" + "=" * 60, "#4fc3f7")
                self.log_message("📊 ИТОГИ ТЕСТИРОВАНИЯ ВСЕХ СТРАТЕГИЙ", "#4fc3f7")
                self.log_message(f"🎯 РЕЖИМ: {mode.upper()}", "#4fc3f7")
                self.log_message("=" * 60, "#4fc3f7")

                self.log_message(f"✅ Протестировано стратегий: {len(results)}", "#30d158")

                # Показываем статистику по качеству стратегий
                if mode == "YouTube/Discord":
                    self.log_message(f"📊 Полностью рабочих: {len(good_results)}", "#30d158" if good_results else "#ff9500")
                    self.log_message(f"📊 Частично рабочих: {len(partial_results)}", "#ffb74d" if partial_results else "#8e8e93")
                    self.log_message(f"📊 Не рабочих: {len(bad_results)}", "#ff3b30" if bad_results else "#30d158")

                    # Показываем детали по частичным стратегиям
                    if partial_results:
                        self.log_message("\n📊 ЧАСТИЧНО РАБОЧИЕ СТРАТЕГИИ:", "#ffb74d")
                        youtube_only = [r for r in partial_results if r.get('youtube_passed', False) and not r.get('discord_passed', False)]
                        discord_only = [r for r in partial_results if not r.get('youtube_passed', False) and r.get('discord_passed', False)]

                        if youtube_only:
                            best_youtube = max(youtube_only, key=lambda x: x.get('success_rate', 0))
                            yt_name = best_youtube.get('strategy', 'Неизвестная')
                            yt_rate = best_youtube.get('success_rate', 0)
                            self.log_message(f"   Только YouTube: {yt_name} ({yt_rate:.1f}%)", "#ffb74d")

                        if discord_only:
                            best_discord = max(discord_only, key=lambda x: x.get('success_rate', 0))
                            dc_name = best_discord.get('strategy', 'Неизвестная')
                            dc_rate = best_discord.get('success_rate', 0)
                            self.log_message(f"   Только Discord: {dc_name} ({dc_rate:.1f}%)", "#ffb74d")
                else:
                    # Стандартный режим - старая статистика
                    self.log_message(f"📊 Полностью рабочих: {len(good_results)}", "#30d158" if good_results else "#ff9500")
                    self.log_message(f"📊 Частично рабочих: {len(partial_results)}", "#ffb74d" if partial_results else "#8e8e93")
                    self.log_message(f"📊 Не рабочих: {len(bad_results)}", "#ff3b30" if bad_results else "#30d158")


                # Выбираем лучшую стратегию для применения (сначала из хороших, потом из частичных)
                all_working = good_results + partial_results
                sorted_all_working = sorted(all_working, key=lambda x: x.get('success_rate', 0), reverse=True)

                if sorted_all_working:
                    best_result = sorted_all_working[0]  # Лучшая стратегия
                    best_status = best_result.get("status", "")

                    # Сортируем отдельно для топа
                    sorted_good = sorted(good_results, key=lambda x: x.get('success_rate', 0), reverse=True)
                    sorted_partial = sorted(partial_results, key=lambda x: x.get('success_rate', 0), reverse=True)

                    # Объединяем для топа: сначала хорошие, потом частичные
                    top_strategies = sorted_good[:3] + sorted_partial[:max(0, 3 - len(sorted_good))]

                    # Определяем параметры лучшей стратегии
                    best_strategy = best_result.get('strategy', 'Неизвестная')
                    best_rate = best_result.get('success_rate', 0)
                    best_successful = best_result.get('successful', 0)
                    best_total = best_result.get('total_targets', 0)

                    # Выводим информацию о выбранной стратегии
                    self.log_message("\n🏆 ВЫБРАНА СТРАТЕГИЯ:", "#4fc3f7")
                    self.log_message(f"   {best_strategy}", "#FFD700")

                    if best_status == "good":
                        self.log_message(f"   ✅ ПОЛНОСТЬЮ РАБОТАЕТ: {best_successful}/{best_total} ({best_rate:.1f}%)", "#30d158")
                    elif best_status == "partial":
                        reason = best_result.get('partial_reason', 'Частично работает')
                        self.log_message(f"   ⚠️  ЧАСТИЧНО РАБОТАЕТ: {best_successful}/{best_total} ({best_rate:.1f}%)", "#ffb74d")
                        self.log_message(f"   Причина: {reason}", "#ffb74d")

                    # Затем идет вывод топа стратегий (следующий блок)
                    self.log_message("\n🏅 ТОП СТРАТЕГИИ:", "#4fc3f7")
                    for i, result in enumerate(top_strategies[:3], 1):
                        strategy = result.get('strategy', 'Неизвестная')
                        rate = result.get('success_rate', 0)
                        successful = result.get('successful', 0)
                        total = result.get('total_targets', 0)
                        status = result.get('status', '')

                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"

                        if status == "good":
                            self.log_message(f"   {medal} {strategy}: {successful}/{total} ({rate:.1f}%) ✅", "#30d158")
                        elif status == "partial":
                            reason = result.get('partial_reason', 'Частично работает')
                            self.log_message(f"   {medal} {strategy}: {successful}/{total} ({rate:.1f}%) ⚠️  [{reason}]", "#ffb74d")

                    # АВТОМАТИЧЕСКОЕ ПРИМЕНЕНИЕ ЛУЧШЕЙ ХОРОШЕЙ СТРАТЕГИИ
                    self.log_message("\n" + "=" * 60, "#4fc3f7")
                    self.log_message("АВТОМАТИЧЕСКОЕ ПРИМЕНЕНИЕ СТРАТЕГИИ", "#4fc3f7")
                    self.log_message("=" * 60, "#4fc3f7")

                    # Применяем лучшую хорошую стратегию
                    if self.apply_best_strategy(best_strategy):
                        # Перезапускаем службу
                        self.restart_service_with_strategy(best_strategy, sudo_password)
                    else:
                        self.log_message("⚠️  Не удалось применить стратегию автоматически", "#ff9500")

                else:
                    # Нет хороших стратегий
                    self.log_message("\n⚠️  НЕТ РАБОЧИХ СТРАТЕГИЙ", "#ff3b30")
                    self.log_message("   Все протестированные стратегии имеют статус 'ПЛОХО'", "#ff9500")
                    self.log_message("   Автоматическое применение отменено", "#ff9500")

                    # Если есть плохие стратегии, показываем худшую и причины
                    if bad_results:
                        # Сортируем плохие стратегии (лучшие из плохих вверху)
                        sorted_bad = sorted(bad_results, key=lambda x: x.get('success_rate', 0), reverse=True)

                        self.log_message("\n📊 АНАЛИЗ ПЛОХИХ СТРАТЕГИЙ:", "#ff9500")
                        for i, result in enumerate(sorted_bad[:3], 1):  # Показываем первые 3
                            strategy = result.get('strategy', 'Неизвестная')
                            rate = result.get('success_rate', 0)
                            reason = result.get('bad_reason', 'Неизвестная причина')

                            badge = "❶" if i == 1 else "❷" if i == 2 else "❸"
                            self.log_message(f"   {badge} {strategy}: {rate:.1f}% - {reason}", "#ff3b30")

                # Проверяем, есть ли отчет
                report_path = tester.reports_dir
                if report_path.exists():
                    html_files = list(report_path.glob("*.html"))
                    if html_files:
                        self.window.after(0, lambda: self.report_button.config(state=tk.NORMAL))
                        latest_report = max(html_files, key=lambda x: x.stat().st_mtime)
                        self.log_message(f"\n📄 HTML отчет сохранен: {latest_report.name}", "#4fc3f7")

            else:
                self.log_message("\n❌ Тестирование завершено без результатов", "#ff3b30")

        except Exception as e:
            # Восстанавливаем stdout в случае ошибки
            sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout

            self.log_message(f"\n❌ Ошибка тестирования: {str(e)}", "#ff3b30")
            import traceback
            error_details = traceback.format_exc()
            self.log_message(f"Детали ошибки:\n{error_details}", "#ff3b30")

        finally:
            # Восстанавливаем stdout
            if 'old_stdout' in locals():
                sys.stdout = old_stdout

            # Очищаем сохраненный пароль
            if hasattr(self, 'current_password'):
                del self.current_password

            # Закрываем loop
            try:
                if 'loop' in locals():
                    loop.close()
            except:
                pass

            # Восстанавливаем состояние кнопок
            self.window.after(0, self.on_test_complete)
    def on_test_complete(self):
        """Вызывается при завершении тестирования"""
        self.testing = False
        # Возвращаем кнопке исходное состояние
        self.test_button.config(text="▶ Запустить тест")
        # Кнопка запуска теперь всегда активна

    def open_report(self):
        """Открывает последний отчет"""
        try:
            reports_dir = self.project_root / "utils" / "reports"
            if not reports_dir.exists():
                self.log_message("❌ Папка отчетов не найдена", "#ff3b30")
                return

            # Ищем последний HTML файл
            html_files = list(reports_dir.glob("*.html"))
            if not html_files:
                self.log_message("❌ Отчеты не найдены", "#ff3b30")
                return

            # Сортируем по времени изменения
            latest_report = max(html_files, key=lambda x: x.stat().st_mtime)

            # Открываем в браузере
            import webbrowser
            webbrowser.open(f"file://{latest_report}")

            self.log_message(f"📄 Открываю отчет: {latest_report.name}", "#30d158")

        except Exception as e:
            self.log_message(f"❌ Ошибка открытия отчета: {str(e)}", "#ff3b30")

    def apply_best_strategy(self, strategy_name):
        """
        Применяет лучшую стратегию, записывая ее в config.txt и name_strategy.txt
        Добавляет дополнительные проверки
        """
        try:
            strategy_path = self.project_root / "files" / "strategy" / strategy_name

            # ПРОВЕРКА 1: Существует ли файл стратегии
            if not strategy_path.exists():
                # Ищем файл с любым расширением
                matching_files = list(strategy_path.parent.glob(strategy_name + ".*"))
                if not matching_files:
                    self.log_message(f"❌ Файл стратегии не найден: {strategy_name}", "#ff3b30")
                    self.log_message("   Автоматическое применение отменено", "#ff9500")
                    return False
                strategy_path = matching_files[0]

            # ПРОВЕРКА 2: Файл не пустой
            file_size = strategy_path.stat().st_size
            if file_size == 0:
                self.log_message(f"❌ Файл стратегии пустой: {strategy_name}", "#ff3b30")
                self.log_message("   Автоматическое применение отменено", "#ff9500")
                return False

            # ПРОВЕРКА 3: Проверяем содержимое файла (должно содержать ключевые слова)
            with open(strategy_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if len(content.strip()) < 10:  # Минимальный размер конфига
                self.log_message(f"❌ Слишком маленький файл стратегии: {strategy_name}", "#ff3b30")
                self.log_message("   Автоматическое применение отменено", "#ff9500")
                return False

            # ПРОВЕРКА 4: Проверяем, что это валидный конфиг zapret
            required_keywords = ['nfqws', '--dpi-desync', '--ssl-split']
            has_required = any(keyword in content.lower() for keyword in required_keywords)

            if not has_required:
                self.log_message(f"⚠️  Предупреждение: Файл может не быть валидным конфигом zapret", "#ff9500")
                self.log_message("   Но все равно применяем...", "#ff9500")

            # Все проверки пройдены, применяем стратегию
            # Записываем в config.txt
            config_path = self.project_root / "config.txt"
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Записываем имя стратегии в name_strategy.txt
            name_strategy_path = self.project_root / "utils" / "name_strategy.txt"
            with open(name_strategy_path, 'w', encoding='utf-8') as f:
                f.write(strategy_name)

            self.log_message(f"✅ Стратегия '{strategy_name}' применена автоматически", "#30d158")
            self.log_message(f"📝 Записана в: {config_path}", "#4fc3f7")
            self.log_message(f"📝 Имя стратегии сохранено в: {name_strategy_path}", "#4fc3f7")

            # ПРОВЕРКА 5: Проверяем, что файлы были записаны корректно
            if not config_path.exists() or config_path.stat().st_size == 0:
                self.log_message(f"❌ Ошибка: config.txt не был записан", "#ff3b30")
                return False

            if not name_strategy_path.exists():
                self.log_message(f"❌ Ошибка: name_strategy.txt не был записан", "#ff3b30")
                return False

            return True

        except PermissionError:
            self.log_message(f"❌ Ошибка доступа к файлам", "#ff3b30")
            self.log_message("   Недостаточно прав для записи конфигурационных файлов", "#ff3b30")
            return False

        except Exception as e:
            self.log_message(f"❌ Ошибка применения стратегии: {str(e)}", "#ff3b30")
            return False

    def restart_service_with_strategy(self, strategy_name, password):
        """
        Перезапускает службу zapret с примененной стратегией
        """
        try:
            self.log_message("\n🔄 Перезапуск службы zapret...", "#4fc3f7")

            # Останавливаем службу
            success, output = self._run_command("systemctl stop zapret", use_sudo=True)
            if not success:
                self.log_message(f"⚠️  Предупреждение при остановке: {output}", "#ff9500")

            # Убиваем процессы nfqws
            self._run_command("pkill -9 nfqws", use_sudo=True)
            time.sleep(2)

            # Запускаем службу
            success, output = self._run_command("systemctl start zapret", use_sudo=True, timeout=10)
            if success:
                self.log_message(f"✅ Служба zapret перезапущена", "#30d158")

                # Ждем немного и проверяем статус
                time.sleep(3)
                status_success, status_output = self._run_command("systemctl is-active zapret", use_sudo=False)

                if status_success and "active" in status_output:
                    self.log_message(f"✅ Служба активна и работает со стратегией '{strategy_name}'", "#30d158")
                else:
                    self.log_message(f"⚠️  Служба не активна: {status_output}", "#ff9500")
            else:
                self.log_message(f"❌ Ошибка запуска службы: {output}", "#ff3b30")

        except Exception as e:
            self.log_message(f"❌ Ошибка перезапуска службы: {str(e)}", "#ff3b30")

    def _run_command(self, command, use_sudo=False, timeout=10):
        """
        Вспомогательный метод для выполнения команд (аналогичный из strategy_tester.py)
        """
        import subprocess

        try:
            if use_sudo and hasattr(self, 'current_password') and self.current_password:
                full_cmd = f"echo '{self.current_password}' | sudo -S {command}"
            elif use_sudo:
                full_cmd = f"sudo {command}"
            else:
                full_cmd = command

            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "Таймаут выполнения команды"
        except Exception as e:
            return False, str(e)

    def on_close(self):
        """Закрывает окно"""
        self.testing = False
        # Очищаем сохраненный пароль
        if hasattr(self, 'current_password'):
            del self.current_password

        # Обновляем стратегию в главном окне
        try:
            # Импортируем родительское окно
            if hasattr(self.parent, 'load_current_strategy'):
                self.parent.load_current_strategy()
        except Exception as e:
            print(f"Не удалось обновить стратегию в главном окне: {e}")

        if self.window:
            self.window.destroy()
