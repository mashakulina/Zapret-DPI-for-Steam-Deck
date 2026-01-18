import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from core.manager_updater import ManagerUpdater
from core.zapret_updater import ZapretUpdater
from ui.components.button_styler import create_hover_button
from ui.components.custom_messagebox import ask_yesno

class UpdateWindow:
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window()

        # Инициализируем обновлялки
        self.manager_updater = ManagerUpdater()
        self.zapret_updater = ZapretUpdater()

        # Флаги наличия обновлений
        self.manager_update_available = False
        self.zapret_update_available = False
        self.manager_update_data = None
        self.zapret_update_data = None
        self.manager_version = None
        self.zapret_version = None

        self.setup_ui()

    def setup_window(self):
        self.root.title("Обновление")
        self.root.geometry("400x400")
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg='#182030', padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        tk.Label(main_frame, text="Обновление компонентов",
                font=("Arial", 14, "bold"), fg='white', bg='#182030').pack(anchor=tk.CENTER, pady=(0, 15))

        # Фрейм для информации о версиях
        info_frame = tk.Frame(main_frame, bg='#182030')
        info_frame.pack(fill=tk.X, pady=(0, 15))

        # Текущие версии
        versions_text = f"Текущие версии:\n"
        versions_text += f"• Менеджер: {self.manager_updater.current_version}\n"
        versions_text += f"• Служба Zapret: {self.zapret_updater.current_version}"

        self.version_label = tk.Label(info_frame, text=versions_text,
                                     font=("Arial", 11), fg='#5BA06A', bg='#182030',
                                     justify=tk.LEFT)
        self.version_label.pack(anchor=tk.W)

        # Кнопка проверки/обновления
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

        # Лог
        log_frame = tk.Frame(main_frame, bg='#182030')
        log_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(log_frame, text="Лог обновлений:",
                font=("Arial", 10), fg='white', bg='#182030').pack(anchor=tk.W, pady=(0, 5))

        self.log_text = tk.Text(
            log_frame,
            height=5,
            bg='#15354D',
            fg='white',
            wrap=tk.WORD,
            font=("Courier", 9),
            highlightthickness=0,
            borderwidth=0
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Кнопка закрытия
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
        if not self.manager_update_available and not self.zapret_update_available:
            # Нет обновлений - проверяем
            self.check_updates()
        else:
            # Есть обновления - показываем диалог
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

            # Проверяем обновления для менеджера
            manager_version, manager_data = self.manager_updater.check_for_updates()

            # Проверяем обновления для zapret
            zapret_version, zapret_data = self.zapret_updater.check_for_updates()

            has_updates = False

            # Обрабатываем результаты для менеджера
            if manager_version:
                self.manager_update_available = True
                self.manager_version = manager_version
                self.manager_update_data = manager_data
                self.log_message(f"📢 Доступно обновление менеджера: v{manager_version}")
                has_updates = True
            else:
                self.manager_update_available = False
                self.log_message("✅ Менеджер: установлена последняя версия")

            # Обрабатываем результаты для zapret
            if zapret_version:
                self.zapret_update_available = True
                self.zapret_version = zapret_version
                self.zapret_update_data = zapret_data
                self.log_message(f"📢 Доступно обновление zapret службы: v{zapret_version}")
                has_updates = True
            else:
                self.zapret_update_available = False
                self.log_message("✅ Служба Zapret: установлена последняя версия")

            if not has_updates:
                self.log_message("\n🎉 Все компоненты обновлены до последних версий!")
            else:
                # Обновляем кнопку
                self.root.after(0, self.update_action_button)

        except Exception as e:
            self.log_message(f"❌ Ошибка при проверке обновлений: {str(e)}")
        finally:
            self.root.after(0, lambda: self.action_btn.config(state=tk.NORMAL))

    def update_action_button(self):
        """Обновляет текст и действие кнопки"""
        if self.manager_update_available or self.zapret_update_available:
            # Определяем, что будем обновлять
            if self.manager_update_available and self.zapret_update_available:
                text = "Обновить все компоненты"
                color = '#15354D'
            elif self.manager_update_available:
                text = f"Обновить менеджер до v{self.manager_version}"
                color = '#15354D'
            else:  # только zapret
                text = f"Обновить zapret до v{self.zapret_version}"
                color = '#15354D'

            self.action_btn.config(
                text=text,
                bg=color,
                command=self.show_update_dialog
            )
        else:
            self.action_btn.config(
                text="Проверить обновления",
                bg='#15354D',
                command=self.check_or_update
            )

    def show_update_dialog(self):
        """Показывает диалог выбора обновления"""
        # Определяем, какие обновления доступны
        updates = []
        if self.manager_update_available:
            updates.append(f"• Менеджер: v{self.manager_version}")
        if self.zapret_update_available:
            updates.append(f"• Служба Zapret: v{self.zapret_version}")

        if not updates:
            return

        updates_text = "\n".join(updates)

        # Блокируем кнопку
        self.action_btn.config(state=tk.DISABLED, text="Обновление...")

        # Запускаем обновление
        thread = threading.Thread(target=self._update_all_thread)
        thread.daemon = True
        thread.start()

    def _update_all_thread(self):
        """Поток для обновления всех компонентов"""
        try:
            self.log_message("\n🔄 Начинаю обновление компонентов...")

            success_count = 0

            # Обновляем менеджер, если есть обновление
            if self.manager_update_available and self.manager_update_data:
                self.log_message(f"\n📦 Обновление менеджера до v{self.manager_version}...")

                download_url = self.manager_update_data.get('download_url')
                if download_url:
                    def progress_callback(message, percent):
                        if percent is not None:
                            self.log_message(f"   [{percent}%] {message}")
                        else:
                            self.log_message(f"   {message}")

                    success = self.manager_updater.update_manager(download_url, progress_callback)

                    if success:
                        self.log_message(f"✅ Менеджер успешно обновлен до v{self.manager_version}!")
                        success_count += 1
                        self.manager_update_available = False
                    else:
                        self.log_message("❌ Не удалось обновить менеджер")
                else:
                    self.log_message("❌ URL для скачивания менеджера не найден")

            # Обновляем zapret, если есть обновление
            if self.zapret_update_available and self.zapret_update_data:
                self.log_message(f"\n📦 Обновление zapret службы до v{self.zapret_version}...")

                download_url = self.zapret_update_data.get('download_url')
                if download_url:
                    def progress_callback(message, percent):
                        if percent is not None:
                            self.log_message(f"   [{percent}%] {message}")
                        else:
                            self.log_message(f"   {message}")

                    success = self.zapret_updater.update_zapret(
                        download_url,
                        self.root,
                        progress_callback
                    )

                    if success:
                        self.log_message(f"✅ Служба Zapret успешно обновлена до v{self.zapret_version}!")
                        success_count += 1
                        self.zapret_update_available = False
                    else:
                        self.log_message("❌ Не удалось обновить zapret службу")
                else:
                    self.log_message("❌ URL для скачивания zapret не найден")

            # Подводим итоги
            self.log_message(f"\n📊 Обновление завершено. Успешно: {success_count}/2")

            # Если обновлялся менеджер, предлагаем перезапуск
            if self.manager_update_available == False and success_count > 0:
                self.root.after(0, self.restart_manager)
            else:
                # Обновляем кнопку
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
        self.manager_updater.restart_manager()
        self.root.destroy()
        self.parent.destroy()

    def close_window(self):
        self.root.destroy()

    def run(self):
        self.root.wait_window()


# Функция для создания окна обновлений
def show_update_window(parent):
    window = UpdateWindow(parent)
    window.run()

class UpdateProgressWindow:
    def __init__(self, parent, update_tasks):
        """
        Окно прогресса обновления

        Args:
            parent: родительское окно
            update_tasks: список задач обновления в формате:
                [{
                    'name': 'Zapret DPI Manager',
                    'updater_class': 'ManagerUpdater',
                    'download_url': 'url'
                }, ...]
        """
        self.parent = parent
        self.update_tasks = update_tasks
        self.current_task_index = 0
        self.window = None
        self.is_updating = False
        self.manager_updated = False  # Флаг, что менеджер был обновлен

    def run(self):
        """Запускает окно прогресса"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Обновление")
        self.window.geometry("400x200")
        self.window.configure(bg='#182030')
        self.window.transient(self.parent)
        self.window.grab_set()

        self.setup_ui()
        self.start_update_process()

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.wait_window()

    def setup_ui(self):
        """Настраивает UI окна прогресса"""
        main_frame = tk.Frame(self.window, bg='#182030', padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(
            main_frame,
            text="Обновление компонентов",
            font=("Arial", 16, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(pady=(0, 20))

        # Текущая задача
        self.task_label = tk.Label(
            main_frame,
            text="Подготовка к обновлению...",
            font=("Arial", 12),
            fg='#0a84ff',
            bg='#182030',
            justify=tk.LEFT
        )
        self.task_label.pack(anchor=tk.W, pady=(0, 10))

        # Статус обновления
        self.status_label = tk.Label(
            main_frame,
            text="",
            font=("Arial", 11),
            fg='#AAAAAA',
            bg='#182030',
            justify=tk.LEFT
        )
        self.status_label.pack(anchor=tk.W, pady=(0, 5))

        # Прогресс-бар
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

            # Общий прогресс от 0 до 100
            overall_progress = 0

            for i, task in enumerate(self.update_tasks):
                if not self.is_updating:
                    break

                self.current_task_index = i
                task_name = task['name']
                updater_class = task['updater_class']
                download_url = task['download_url']

                # Обновляем информацию о текущей задаче
                self._update_task_info(f"Обновление {task_name} ({i+1}/{total_tasks})")
                self._update_status(f"Начинаю обновление {task_name}...")
                print(f"\n🔄 Начинаю обновление {task_name}...")

                # Выполняем обновление в зависимости от типа
                if updater_class == 'ManagerUpdater':
                    success = self._update_manager(download_url, task_name, overall_progress, total_tasks, i)
                    if success:
                        self.manager_updated = True
                elif updater_class == 'ZapretUpdater':
                    success = self._update_zapret(download_url, task_name, overall_progress, total_tasks, i)
                else:
                    success = False
                    print(f"❌ Неизвестный класс обновления: {updater_class}")

                # Обновляем общий прогресс после завершения задачи
                overall_progress = int((i + 1) / total_tasks * 100)
                self._update_progress_bar(overall_progress)

                if success:
                    print(f"✅ {task_name} успешно обновлен!")
                    self._update_status(f"{task_name} обновлен успешно")
                else:
                    print(f"❌ Не удалось обновить {task_name}")
                    self._update_status(f"{task_name}: ошибка обновления")

            # Завершаем обновление
            if self.is_updating:
                print(f"\n🎉 Обновление завершено!")
                self._update_task_info("Обновление завершено")
                self._update_status("Все компоненты успешно обновлены")

                # Устанавливаем прогресс на 100%
                self._update_progress_bar(100)

                # Если обновлялся менеджер, показываем сообщение о перезапуске
                if self.manager_updated:
                    self._show_restart_message()
                else:
                    # Закрываем окно через 2 секунды
                    self.window.after(2000, self.window.destroy)

        except Exception as e:
            print(f"\n❌ Ошибка при обновлении: {str(e)}")
            import traceback
            traceback.print_exc()
            self._update_status(f"Ошибка: {str(e)}")

    def _update_manager(self, download_url, task_name, base_progress, total_tasks, task_index):
        """Обновляет менеджер"""
        try:
            from core.manager_updater import ManagerUpdater
            manager_updater = ManagerUpdater()

            # Словарь для маппинга сообщений в проценты
            progress_map = {
                "Сохранение конфигураций": 10,
                "Очистка директории": 20,
                "Скачивание обновления": 30,
                "Распаковка": 50,
                "Копирование файлов": 70,
                "Восстановление конфигураций": 85,
                "Настройка прав": 95,
                "Обновление завершено": 100
            }

            def progress_callback(message, percent):
                # Определяем процент для этого шага
                step_progress = percent if percent is not None else 0

                # Ищем ключевые слова в сообщении
                for key, value in progress_map.items():
                    if key in message:
                        step_progress = value
                        break

                # Рассчитываем общий прогресс
                # Прогресс внутри текущей задачи (0-100)
                task_internal_progress = step_progress

                # Общий прогресс = прогресс предыдущих задач + часть текущей задачи
                # Каждая задача занимает 100/total_tasks процентов
                task_weight = 100 / total_tasks
                previous_tasks_progress = task_index * task_weight
                current_task_progress = task_internal_progress * (task_weight / 100)

                overall_progress = int(previous_tasks_progress + current_task_progress)

                # Обновляем прогресс-бар
                self.window.after(0, lambda p=overall_progress: self._update_progress_bar(p))

                # Обновляем статус
                self.window.after(0, lambda: self._update_progress_message(message, step_progress))

            print(f"  📦 Скачивание обновления менеджера...")
            success = manager_updater.update_manager(download_url, progress_callback)

            if success:
                print(f"  ✅ Менеджер успешно обновлен!")
            else:
                print(f"  ❌ Не удалось обновить менеджер")

            return success

        except Exception as e:
            print(f"  ❌ Ошибка обновления менеджера: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _update_zapret(self, download_url, task_name, base_progress, total_tasks, task_index):
        """Обновляет службу Zapret"""
        try:
            from core.zapret_updater import ZapretUpdater
            zapret_updater = ZapretUpdater()

            # Словарь для маппинга сообщений в проценты
            progress_map = {
                "Скачивание архива": 20,
                "Извлечение архива": 40,
                "Создание директории": 50,
                "Копирование файлов": 60,
                "Копирование бинарных файлов": 70,
                "Настройка параметров": 75,
                "Создание службы": 80,
                "Обновление systemd": 85,
                "Включение автозапуска": 90,
                "Запуск службы": 95,
                "Служба успешно запущена": 100
            }

            def progress_callback(message, percent):
                # Определяем процент для этого шага
                step_progress = percent if percent is not None else 0

                # Ищем ключевые слова в сообщении
                for key, value in progress_map.items():
                    if key in message:
                        step_progress = value
                        break

                # Рассчитываем общий прогресс
                # Прогресс внутри текущей задачи (0-100)
                task_internal_progress = step_progress

                # Общий прогресс = прогресс предыдущих задач + часть текущей задачи
                # Каждая задача занимает 100/total_tasks процентов
                task_weight = 100 / total_tasks
                previous_tasks_progress = task_index * task_weight
                current_task_progress = task_internal_progress * (task_weight / 100)

                overall_progress = int(previous_tasks_progress + current_task_progress)

                # Обновляем прогресс-бар
                self.window.after(0, lambda p=overall_progress: self._update_progress_bar(p))

                # Обновляем статус
                self.window.after(0, lambda: self._update_progress_message(message, step_progress))

            print(f"  📦 Скачивание обновления службы Zapret...")
            success = zapret_updater.update_zapret(download_url, self.window, progress_callback)

            if success:
                print(f"  ✅ Служба Zapret успешно обновлена!")
            else:
                print(f"  ❌ Не удалось обновить службу Zapret")

            return success

        except Exception as e:
            print(f"  ❌ Ошибка обновления службы Zapret: {str(e)}")
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
        # Принудительно обновляем окно для получения актуальных размеров
        self.window.update_idletasks()

        width = self.progress_bar.winfo_width()
        if width <= 1:  # Если размер еще не определен
            width = 350  # Используем примерную ширину

        # Ограничиваем процент от 0 до 100
        percent = max(0, min(100, percent))
        fill_width = int(width * percent / 100)

        self.progress_fill.config(width=fill_width)
        self.progress_bar.update_idletasks()

    def _show_restart_message(self):
        """Показывает сообщение о необходимости перезапуска"""
        self._update_task_info("Обновление завершено")
        self._update_status("Перезапуск программы...")

        # Показываем сообщение на 2 секунды, затем перезапускаем
        self.window.after(2000, self._restart_manager)

    def _restart_manager(self):
        """Перезапускает менеджер"""
        try:
            from core.manager_updater import ManagerUpdater
            manager_updater = ManagerUpdater()
            print("🔄 Перезапускаю менеджер...")
            manager_updater.restart_manager()

            # Закрываем текущее окно и родительское
            self.window.destroy()
            if self.parent:
                self.parent.destroy()

        except Exception as e:
            print(f"❌ Ошибка при перезапуске менеджера: {e}")
            # В любом случае закрываем окно
            self.window.destroy()

    def cancel_update(self):
        """Отменяет обновление"""
        self.is_updating = False
        print("\n⏹️ Обновление отменено пользователем")
        self._update_task_info("Обновление отменено")
        self._update_status("Операция прервана пользователем")

        # Активируем кнопку "Закрыть"
        self.window.after(0, lambda: self.close_button.config(state=tk.NORMAL))
        # Скрываем кнопку "Отмена"
        self.window.after(0, lambda: self.cancel_button.pack_forget())

    def on_close(self):
        """Обработчик закрытия окна"""
        if self.is_updating:
            # Если идет обновление, спрашиваем подтверждение
            from ui.components.custom_messagebox import ask_yesno
            if ask_yesno(self.window, "Отмена обновления",
                         "Обновление еще не завершено. Вы уверены, что хотите отменить?"):
                self.cancel_update()
        else:
            self.window.destroy()

    def close_window(self):
        """Закрывает окно"""
        self.window.destroy()


# Функция для создания окна прогресса обновления
def show_update_progress_window(parent, update_tasks):
    """Показывает окно прогресса обновления"""
    window = UpdateProgressWindow(parent, update_tasks)
    window.run()
