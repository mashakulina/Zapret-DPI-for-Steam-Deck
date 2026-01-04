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
    def __init__(self, parent, project_root="/home/deck/Zapret_DPI_Manager", strategies_to_test=None):
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
        self.window.geometry("650x500")
        self.window.configure(bg='#182030')

        self.setup_ui()


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
                # Анализируем результаты
                successful_tests = sum(r.get('successful', 0) for r in results)
                total_tests = sum(r.get('total_targets', 0) for r in results)

                # Находим лучшую стратегию
                best_result = max(results, key=lambda x: x.get('success_rate', 0))
                best_strategy = best_result.get('strategy', 'Неизвестная')
                best_rate = best_result.get('success_rate', 0)
                best_successful = best_result.get('successful', 0)
                best_total = best_result.get('total_targets', 0)

                self.log_message("\n" + "=" * 60, "#4fc3f7")
                self.log_message("📊 ИТОГИ ТЕСТИРОВАНИЯ ВСЕХ СТРАТЕГИЙ", "#4fc3f7")
                self.log_message("=" * 60, "#4fc3f7")

                self.log_message(f"✅ Протестировано стратегий: {len(results)}", "#30d158")
                self.log_message(f"📈 Всего проверок: {total_tests}", "#4fc3f7")
                self.log_message(f"🎯 Успешных проверок: {successful_tests}", "#30d158")

                self.log_message("\n🏆 ЛУЧШАЯ СТРАТЕГИЯ:", "#4fc3f7")
                self.log_message(f"   {best_strategy}", "#FFD700")  # Золотой цвет

                if best_rate >= 80:
                    self.log_message(f"   ✅ ОТЛИЧНО: {best_successful}/{best_total} ({best_rate:.1f}%)", "#30d158")
                elif best_rate >= 60:
                    self.log_message(f"   ⚠️  НОРМАЛЬНО: {best_successful}/{best_total} ({best_rate:.1f}%)", "#ff9500")
                else:
                    self.log_message(f"   ❌ ПЛОХО: {best_successful}/{best_total} ({best_rate:.1f}%)", "#ff3b30")

                # Выводим топ-3 стратегии
                self.log_message("\n🏅 ТОП-3 СТРАТЕГИИ:", "#4fc3f7")
                sorted_results = sorted(results, key=lambda x: x.get('success_rate', 0), reverse=True)

                for i, result in enumerate(sorted_results[:3], 1):
                    strategy = result.get('strategy', 'Неизвестная')
                    rate = result.get('success_rate', 0)
                    successful = result.get('successful', 0)
                    total = result.get('total_targets', 0)

                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    self.log_message(f"   {medal} {strategy}: {successful}/{total} ({rate:.1f}%)", "#4fc3f7")

                # АВТОМАТИЧЕСКОЕ ПРИМЕНЕНИЕ ЛУЧШЕЙ СТРАТЕГИИ
                if best_rate > 0:  # Если есть успешные тесты
                    self.log_message("\n" + "=" * 60, "#4fc3f7")
                    self.log_message("🤖 АВТОМАТИЧЕСКОЕ ПРИМЕНЕНИЕ СТРАТЕГИИ", "#4fc3f7")
                    self.log_message("=" * 60, "#4fc3f7")

                    # Применяем лучшую стратегию
                    if self.apply_best_strategy(best_strategy):
                        # Перезапускаем службу
                        self.restart_service_with_strategy(best_strategy, sudo_password)
                    else:
                        self.log_message("⚠️  Не удалось применить стратегию автоматически", "#ff9500")

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

            # Восстанавливаем состояние кнопок и останавливаем таймер
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
        """
        try:
            strategy_path = self.project_root / "files" / "strategy" / strategy_name

            # Проверяем, существует ли файл стратегии
            if not strategy_path.exists():
                # Ищем файл с любым расширением
                matching_files = list(strategy_path.parent.glob(strategy_name + ".*"))
                if not matching_files:
                    self.log_message(f"❌ Файл стратегии не найден: {strategy_name}", "#ff3b30")
                    return False
                strategy_path = matching_files[0]

            # Читаем содержимое стратегии
            with open(strategy_path, 'r', encoding='utf-8') as f:
                strategy_content = f.read()

            # Записываем в config.txt
            config_path = self.project_root / "config.txt"
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(strategy_content)

            # Записываем имя стратегии в name_strategy.txt
            name_strategy_path = self.project_root / "utils" / "name_strategy.txt"
            with open(name_strategy_path, 'w', encoding='utf-8') as f:
                f.write(strategy_name)

            self.log_message(f"✅ Стратегия '{strategy_name}' применена автоматически", "#30d158")
            self.log_message(f"📝 Записана в: {config_path}", "#4fc3f7")
            self.log_message(f"📝 Имя стратегии сохранено в: {name_strategy_path}", "#4fc3f7")

            return True

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
