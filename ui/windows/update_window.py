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
