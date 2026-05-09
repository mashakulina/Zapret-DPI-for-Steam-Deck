import tkinter as tk
import threading

from core.manager_config import VERSION_CONFIG
from core.zapret_updater import ZapretBundleUpdater
from ui.components.button_styler import create_hover_button
from core.dpi_utils import (
    center_toplevel_on_parent,
    place_toplevel_centered_on_parent,
    set_window_size_to_fit_content,
)


class UpdateWindow:
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window()

        self.bundle_updater = ZapretBundleUpdater()

        self.bundle_update_available = False
        self.bundle_update_data = None
        self.bundle_version = None

        self.setup_ui()
        self.root.update_idletasks()
        try:
            self.root.minsize(1, 1)
        except tk.TclError:
            pass
        set_window_size_to_fit_content(
            self.root,
            min_width=360,
            min_height=320,
            margin_width=8,
            margin_height=12,
        )
        center_toplevel_on_parent(self.root, self.parent)

    def setup_window(self):
        self.root.title("Обновление")
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg='#182030', padx=20, pady=15)
        main_frame.pack(fill=tk.X)

        tk.Label(main_frame, text="Обновление компонентов",
                font=("Arial", 14, "bold"), fg='white', bg='#182030').pack(anchor=tk.CENTER, pady=(0, 15))

        info_frame = tk.Frame(main_frame, bg='#182030')
        info_frame.pack(fill=tk.X, pady=(0, 15))

        versions_text = f"Версия программы: {VERSION_CONFIG['current_version']}"

        self.version_label = tk.Label(info_frame, text=versions_text,
                                     font=("Arial", 11), fg='#5BA06A', bg='#182030',
                                     justify=tk.LEFT)
        self.version_label.pack(anchor=tk.W)

        btn_frame = tk.Frame(main_frame, bg='#182030')
        btn_frame.pack(fill=tk.X, pady=(0, 15))

        self.action_btn = create_hover_button(
            btn_frame,
            text="Проверить обновления",
            command=self.check_or_update,
            bg='#15354D', fg='white', font=('Arial', 10),
            width=25, bd=0, highlightthickness=0, padx=15, pady=8
        )
        self.action_btn.pack(anchor=tk.CENTER)

        log_frame = tk.Frame(main_frame, bg='#182030')
        log_frame.pack(fill=tk.X)

        tk.Label(log_frame, text="Лог обновлений:",
                font=("Arial", 10), fg='white', bg='#182030').pack(anchor=tk.W, pady=(0, 5))

        self.log_text = tk.Text(
            log_frame,
            height=6,
            width=48,
            bg='#15354D',
            fg='white',
            wrap=tk.WORD,
            font=("Courier", 9),
            highlightthickness=0,
            borderwidth=0
        )
        self.log_text.pack(fill=tk.X)

        close_frame = tk.Frame(main_frame, bg='#182030')
        close_frame.pack(fill=tk.X, pady=(10, 0))

        self.close_btn = create_hover_button(
            close_frame,
            text="Назад",
            command=self.close_window,
            bg='#15354D', fg='white', font=('Arial', 10),
            width=15, bd=0, highlightthickness=0, padx=10, pady=5
        )
        self.close_btn.pack(anchor=tk.CENTER)

    def log_message(self, message):
        """Добавляет сообщение в лог"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """Очищает лог"""
        self.log_text.delete(1.0, tk.END)

    def check_or_update(self):
        """Проверяет обновления или выполняет обновление"""
        if not self.bundle_update_available:
            self.check_updates()
        else:
            self.show_update_dialog()

    def check_updates(self):
        """Проверяет обновления для всех компонентов"""
        self.action_btn.config(state=tk.DISABLED, text="Проверка...")
        self.clear_log()

        thread = threading.Thread(target=self._check_updates_thread)
        thread.daemon = True
        thread.start()

    def _check_updates_thread(self):
        """Поток для проверки обновлений"""
        try:
            self.log_message("🔍 Начинаю проверку обновлений...")

            bundle_version, bundle_data = self.bundle_updater.check_for_updates()
            if bundle_version:
                self.bundle_update_available = True
                self.bundle_version = bundle_version
                self.bundle_update_data = bundle_data
                self.log_message(f"📢 Доступно полное обновление: v{bundle_version}")
                self.root.after(0, self.update_action_button)
            else:
                self.bundle_update_available = False
                self.bundle_update_data = None
                self.bundle_version = None
                self.log_message("\n🎉 Установлена последняя версия")

        except Exception as e:
            self.log_message(f"❌ Ошибка при проверке обновлений: {str(e)}")
        finally:
            self.root.after(0, lambda: self.action_btn.config(state=tk.NORMAL))

    def update_action_button(self):
        """Обновляет текст и действие кнопки"""
        if self.bundle_update_available:
            self.action_btn.config(
                text=f"Обновить полный пакет до v{self.bundle_version}",
                bg='#15354D',
                command=self.show_update_dialog,
            )
        else:
            self.action_btn.config(
                text="Проверить обновления",
                bg='#15354D',
                command=self.check_or_update,
            )

    def show_update_dialog(self):
        """Запускает обновление полного пакета"""
        if not self.bundle_update_available:
            return

        self.action_btn.config(state=tk.DISABLED, text="Обновление...")

        thread = threading.Thread(target=self._update_all_thread)
        thread.daemon = True
        thread.start()

    def _update_all_thread(self):
        """Поток для обновления полного пакета"""
        try:
            self.log_message("\n🔄 Начинаю обновление компонентов...")

            success_count = 0

            if self.bundle_update_available and self.bundle_update_data:
                self.log_message(f"\n📦 Полное обновление до v{self.bundle_version}...")
                download_url = self.bundle_update_data.get("download_url")
                if download_url:

                    def progress_callback(message, percent):
                        if percent is not None:
                            self.log_message(f"   [{percent}%] {message}")
                        else:
                            self.log_message(f"   {message}")

                    success = self.bundle_updater.update_bundle(
                        download_url, self.root, progress_callback
                    )
                    if success:
                        self.log_message(f"✅ Полное обновление до v{self.bundle_version} завершено!")
                        success_count += 1
                        self.bundle_update_available = False
                    else:
                        self.log_message("❌ Не удалось выполнить полное обновление")
                else:
                    self.log_message("❌ URL полного пакета не найден")

            self.log_message(f"\n📊 Обновление завершено. Успешных шагов: {success_count}")

            if success_count > 0:
                self.root.after(0, self.restart_manager)
            else:
                self.root.after(0, self.update_action_button)

        except Exception as e:
            self.log_message(f"❌ Ошибка при обновлении: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.root.after(0, lambda: self.action_btn.config(state=tk.NORMAL))
            self.root.after(0, self.update_action_button)

    def restart_manager(self):
        """Перезапускает менеджер"""
        from core.manager_updater import ManagerUpdater
        ManagerUpdater().restart_manager()
        self.root.destroy()
        self.parent.destroy()

    def close_window(self):
        self.root.destroy()

    def run(self):
        self.root.wait_window()


def show_update_window(parent):
    window = UpdateWindow(parent)
    window.run()


class UpdateProgressWindow:
    def __init__(self, parent, update_tasks):
        """
        Окно прогресса обновления.

        Args:
            parent: родительское окно
            update_tasks: список задач обновления (используется только bundle):
                [{
                    'name': 'Zapret DPI Manager',
                    'updater_class': 'ZapretBundleUpdater',
                    'download_url': 'url'
                }, ...]
        """
        self.parent = parent
        self.update_tasks = update_tasks
        self.current_task_index = 0
        self.window = None
        self.is_updating = False
        self.manager_updated = False  # Флаг, что bundle применён (нужен перезапуск)
        self.bundle_updater = ZapretBundleUpdater()

    def run(self):
        """Запускает окно прогресса"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Обновление")
        self.window.configure(bg='#182030')
        self.window.transient(self.parent)
        self.window.grab_set()

        self.setup_ui()
        place_toplevel_centered_on_parent(
            self.window, self.parent, min_width=340, min_height=160, margin_width=8, margin_height=12
        )
        self.start_update_process()

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.wait_window()

    def setup_ui(self):
        """Настраивает UI окна прогресса"""
        main_frame = tk.Frame(self.window, bg='#182030', padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            main_frame,
            text="Обновление компонентов",
            font=("Arial", 16, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(pady=(0, 20))

        self.task_label = tk.Label(
            main_frame,
            text="Подготовка к обновлению...",
            font=("Arial", 12),
            fg='#0a84ff',
            bg='#182030',
            justify=tk.LEFT
        )
        self.task_label.pack(anchor=tk.W, pady=(0, 10))

        self.status_label = tk.Label(
            main_frame,
            text="",
            font=("Arial", 11),
            fg='#AAAAAA',
            bg='#182030',
            justify=tk.LEFT
        )
        self.status_label.pack(anchor=tk.W, pady=(0, 5))

        progress_container = tk.Frame(main_frame, bg='#182030')
        progress_container.pack(fill=tk.X, pady=(15, 20))

        self.progress_bar = tk.Frame(progress_container, bg='#2c2c2e', height=10)
        self.progress_bar.pack(fill=tk.X)
        self.progress_bar.pack_propagate(False)

        self.progress_fill = tk.Frame(self.progress_bar, bg='#0a84ff', width=0)
        self.progress_fill.pack(side=tk.LEFT, fill=tk.Y)

    def start_update_process(self):
        """Запускает процесс обновления"""
        self.is_updating = True
        thread = threading.Thread(target=self._update_thread, daemon=True)
        thread.start()

    def _update_thread(self):
        """Поток для выполнения обновлений"""
        try:
            total_tasks = len(self.update_tasks)

            overall_progress = 0

            for i, task in enumerate(self.update_tasks):
                if not self.is_updating:
                    break

                self.current_task_index = i
                task_name = task['name']
                updater_class = task['updater_class']
                download_url = task['download_url']

                self._update_task_info(f"Обновление {task_name} ({i+1}/{total_tasks})")
                self._update_status(f"Начинаю обновление {task_name}...")
                print(f"\n🔄 Начинаю обновление {task_name}...")

                if updater_class == 'ZapretBundleUpdater':
                    success = self._update_bundle(download_url, task_name, overall_progress, total_tasks, i)
                    if success:
                        self.manager_updated = True
                else:
                    success = False
                    print(f"❌ Неизвестный класс обновления: {updater_class}")

                overall_progress = int((i + 1) / total_tasks * 100)
                self._update_progress_bar(overall_progress)

                if success:
                    print(f"✅ {task_name} успешно обновлен!")
                    self._update_status(f"{task_name} обновлен успешно")
                else:
                    print(f"❌ Не удалось обновить {task_name}")
                    self._update_status(f"{task_name}: ошибка обновления")

            if self.is_updating:
                print("\n🎉 Обновление завершено!")
                self._update_task_info("Обновление завершено")
                self._update_status("Все компоненты успешно обновлены")

                self._update_progress_bar(100)

                if self.manager_updated:
                    self._show_restart_message()
                else:
                    self.window.after(2000, self.window.destroy)

        except Exception as e:
            print(f"\n❌ Ошибка при обновлении: {str(e)}")
            import traceback
            traceback.print_exc()
            self._update_status(f"Ошибка: {str(e)}")

    def _update_bundle(self, download_url, task_name, base_progress, total_tasks, task_index):
        """Полное обновление менеджера и службы одним архивом."""
        try:
            progress_map = {
                "Остановка": 10,
                "Скачивание": 25,
                "Распаковка": 40,
                "Применение обновления менеджера": 55,
                "Копирование файлов системы": 60,
                "Копирование бинарных": 70,
                "Создание службы systemd": 80,
                "Обновление systemd": 85,
                "Включение автозапуска": 90,
                "Запуск службы": 95,
                "Полное обновление завершено": 100,
            }

            def progress_callback(message, percent):
                step_progress = percent if percent is not None else 0
                for key, value in progress_map.items():
                    if key in message:
                        step_progress = value
                        break
                task_internal_progress = step_progress
                task_weight = 100 / total_tasks
                previous_tasks_progress = task_index * task_weight
                current_task_progress = task_internal_progress * (task_weight / 100)
                overall_progress = int(previous_tasks_progress + current_task_progress)
                self.window.after(0, lambda p=overall_progress: self._update_progress_bar(p))
                self.window.after(0, lambda: self._update_progress_message(message, step_progress))

            print("  📦 Полное обновление пакета...")
            return self.bundle_updater.update_bundle(download_url, self.window, progress_callback)

        except Exception as e:
            print(f"  ❌ Ошибка полного обновления: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _update_task_info(self, text):
        """Обновляет информацию о текущей задаче"""
        self.window.after(0, lambda: self.task_label.config(text=text))

    def _update_status(self, text):
        """Обновляет статус обновления"""
        self.window.after(0, lambda: self.status_label.config(text=text))

    def _update_progress_message(self, message, percent=None):
        """Обновляет сообщение о прогрессе"""
        if percent is not None:
            text = f"[{percent}%] {message}"
        else:
            text = message

        self.status_label.config(text=text)
        print(f"    {message}")

    def _update_progress_bar(self, percent):
        """Обновляет прогресс-бар"""
        self.window.update_idletasks()

        width = self.progress_bar.winfo_width()
        if width <= 1:
            width = 350

        percent = max(0, min(100, percent))
        fill_width = int(width * percent / 100)

        self.progress_fill.config(width=fill_width)
        self.progress_bar.update_idletasks()

    def _show_restart_message(self):
        """Показывает сообщение о необходимости перезапуска"""
        self._update_task_info("Обновление завершено")
        self._update_status("Перезапуск программы...")

        self.window.after(2000, self._restart_manager)

    def _restart_manager(self):
        """Перезапускает менеджер"""
        try:
            from core.manager_updater import ManagerUpdater
            manager_updater = ManagerUpdater()
            print("🔄 Перезапускаю менеджер...")
            manager_updater.restart_manager()

            self.window.destroy()
            if self.parent:
                self.parent.destroy()

        except Exception as e:
            print(f"❌ Ошибка при перезапуске менеджера: {e}")
            self.window.destroy()

    def cancel_update(self):
        """Отменяет обновление"""
        self.is_updating = False
        print("\n⏹️ Обновление отменено пользователем")
        self._update_task_info("Обновление отменено")
        self._update_status("Операция прервана пользователем")

    def on_close(self):
        """Обработчик закрытия окна"""
        if self.is_updating:
            from ui.components.custom_messagebox import ask_yesno
            if ask_yesno(self.window, "Отмена обновления",
                         "Обновление еще не завершено. Вы уверены, что хотите отменить?"):
                self.cancel_update()
        else:
            self.window.destroy()

    def close_window(self):
        """Закрывает окно"""
        self.window.destroy()


def show_update_progress_window(parent, update_tasks):
    """Показывает окно прогресса обновления"""
    window = UpdateProgressWindow(parent, update_tasks)
    window.run()
