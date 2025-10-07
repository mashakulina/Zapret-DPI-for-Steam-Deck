#!/usr/bin/env python3
import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys, os
import re


class ZapretGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Zapret DPI Manager")
        self.root.geometry("950x350")
        self.version = "1.9"

        # Константы для путей
        self.ETC_HOSTS_PATH = "/etc/hosts"
        self.ZAPRET_HOSTS_PATH = "/opt/zapret/hosts.txt"
        self.zapret_config_path = os.path.join("/", "opt", "zapret", "config.txt") # Путь до стратегий запрета
        self.zapret_manager_working_dir_path = os.path.join("/", "home", "deck", "zapret") # Путь до корневой папки скрипта
        self.zapret_manager_strategy_dir = "strategy" # Папка с стратегиями

        # Список сайтов для новой вкладки
        self.AI_SITES = {
            "Gemini": "Gemini",
            "Chatgpt": "Chatgpt",
            "Другие AI": "OtherAI",
            "Instagram": "Instagram",
            "Facebook": "Facebook",
            "Spotify": "Spotify",
            "Twitch": "Twitch",
            "Tiktok": "Tiktok",
            "Rutracker": "Rutracker"
        }

        # # Устанавливаем стиль и шрифты
        self.style = ttk.Style()
        self.style.configure('.', font=('Helvetica', 14))  # Базовый шрифт

        # Настройка шрифтов для конкретных виджетов
        self.style.configure('TButton', font=('Helvetica', 13, 'bold'))
        self.style.configure('TLabel', font=('Helvetica', 13))
        self.style.configure('TNotebook.Tab', font=('Helvetica', 13))

        # Проверка прав root
        if os.geteuid() != 0:
            self.show_password_dialog()
        else:
            self.check_zapret_installed()

    def is_package_installed(self, package_name):
        """Проверяет, установлен ли пакет через проверку версии"""
        try:
            if package_name == 'curl':
                subprocess.run(['sudo', 'curl', '--version'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             check=True)
                return True
            elif package_name == 'ipset':
                subprocess.run(['sudo', 'ipset', '--version'],
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             check=True)
                return True
            elif package_name == 'iptables':
                subprocess.run(['sudo', 'iptables', '--version'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True)
                return True
            return False
        except subprocess.CalledProcessError:
            return False

    def unlock_filesystem(self):
        """Разблокирует файловую систему для записи."""
        try:
            subprocess.run(['sudo', 'steamos-readonly', 'disable'], check=True)
            return True
        except subprocess.CalledProcessError as e:
            # Игнорируем предупреждение о том, что система уже разблокирована
            if "already read-write" in str(e):
                return True
            # Для других ошибок показываем сообщение
            messagebox.showerror("Ошибка", f"Не удалось разблокировать ФС: {e}")
            return False

    def lock_filesystem(self, max_attempts=3):
        """
        Блокирует файловую систему с несколькими попытками
        Возвращает True если удалось заблокировать, False если все попытки провалились
        """
        for attempt in range(1, max_attempts + 1):
            try:
                subprocess.run(['sudo', 'steamos-readonly', 'enable'], check=True)
                print(f"✓ Файловая система успешно заблокирована (попытка {attempt})")
                return True

            except subprocess.CalledProcessError as e:
                error_msg = f"Попытка {attempt}/{max_attempts} не удалась: {e}"
                print(error_msg)

                if attempt < max_attempts:
                    # Спросить пользователя о повторной попытке
                    retry = messagebox.askretrycancel(
                        "Ошибка блокировки файловой системы",
                        f"{error_msg}\n\nХотите повторить попытку блокировки?"
                    )
                    if retry:
                        continue  # Повторить попытку
                    else:
                        break    # Пользователь отказался от повторной поптыки
                else:
                    # Все попытки исчерпаны
                    messagebox.showerror(
                        "Ошибка блокировки файловой системы",
                        f"Не удалось заблокировать файловую систему после {max_attempts} попыток.\n\n"
                        "Рекомендуется выполнить вручную:\n"
                        "sudo steamos-readonly enable"
                    )
                    return False

        return False

    def fix_pacman_conf(self):
        """Модифицирует pacman.conf и инициализирует ключи"""
        try:
            # Модифицируем pacman.conf
            subprocess.run([
                'sudo', 'sed', '-i',
                's/Required DatabaseOptional/TrustAll/g',
                '/etc/pacman.conf'
            ], check=True)

            # Инициализируем ключи
            subprocess.run(['sudo', 'pacman-key', '--init'], check=True)
            subprocess.run(['sudo', 'pacman-key', '--populate'], check=True)

            # Обновляем базу пакетов
            subprocess.run(['sudo', 'pacman', '-Sy'], check=True)

            return True
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка конфигурации pacman: {str(e)}")
            return False

    def fix_pacman_conf_for_uninstall(self):
        """Модифицирует pacman.conf и инициализирует ключи"""
        try:
            # Модифицируем pacman.conf
            subprocess.run([
                'sudo', 'sed', '-i',
                's/TrustAll/Required DatabaseOptional/g',
                '/etc/pacman.conf'
            ], check=True)

            # Инициализируем ключи
            subprocess.run(['sudo', 'pacman-key', '--init'], check=True)
            subprocess.run(['sudo', 'pacman-key', '--populate'], check=True)

            # Обновляем базу пакетов
            subprocess.run(['sudo', 'pacman', '-Sy'], check=True)

            return True
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка конфигурации pacman: {str(e)}")
            return False

    def install_dependencies(self):
        """Устанавливает необходимые зависимости (ipset и iptables)"""
        try:
            if not self.unlock_filesystem():
                return False

            # Проверяем и устанавливаем зависимости
            dependencies_needed = False

            if not self.is_package_installed('curl'):
                if not self.fix_pacman_conf():
                    return False
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'curl'], check=True)
                dependencies_needed = True

            if not self.is_package_installed('ipset'):
                if not self.fix_pacman_conf():
                    return False
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'ipset'], check=True)
                dependencies_needed = True

            if not self.is_package_installed('iptables'):
                if not self.fix_pacman_conf():
                    return False
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'iptables'], check=True)
                dependencies_needed = True

            self.lock_filesystem()

            return True
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Ошибка", f"Ошибка при установке зависимостей: {e}")
            return False

    def install_zapret_dpi(self):
        """Устанавливаем службу Zapret DPI"""
        try:
            if not self.unlock_filesystem():
                return False

            subprocess.run(['unzip', 'zapret.zip'], cwd='/home/deck/zapret', check=True)
            subprocess.run(['sudo', './install.sh'], cwd='/home/deck/zapret/zapret', check=True)
            subprocess.run(['rm', '-rf', '/home/deck/zapret/zapret'], check=True)
            subprocess.run(['rm', '-rf', '/home/deck/zapret/zapret.zip'], check=True)

            return True
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка скачивания службы {str(e)}")
            return False

    def install_zapret_dpi_manager(self):
        """Устанавливаем Zapret DPI Manager"""
        try:
            os.makedirs('/home/deck/zapret', exist_ok=True)
            subprocess.run([
                'wget', 'https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/releases/latest/download/zapret_dpi_manager.zip'
            ], cwd='/home/deck/zapret', check=True)
            subprocess.run(['unzip', 'zapret_dpi_manager.zip'], cwd='/home/deck/zapret', check=True)
            subprocess.run(['rm', 'zapret_dpi_manager.zip'], cwd='/home/deck/zapret', check=True)
            subprocess.run(['sudo', 'chmod', '+x', 'zapret.py'], cwd='/home/deck/zapret', check=True)
            subprocess.run(['sudo', 'chmod', '+x', 'reinstall_zapret.sh'], cwd='/home/deck/zapret', check=True)

            return True
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка скачивания Zapret DPI Manager {str(e)}")
            return False

    def is_service_active(self):
        """Проверяет, активна ли служба"""
        try:
            result = subprocess.run(['systemctl', 'is-active', 'zapret'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0
        except:
            return False

    def is_service_enabled(self):
        """Проверяет, включен ли автозапуск службы"""
        try:
            result = subprocess.run(['systemctl', 'is-enabled', 'zapret'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0
        except:
            return False

    # Экран ввода пароля
    def show_password_dialog(self):
        self.password_window = tk.Toplevel(self.root)
        self.password_window.title("Аутентификация")
        self.password_window.geometry("300x125")
        self.password_window.resizable(False, False)

        tk.Label(self.password_window, text="Введите sudo пароль:", font=('Helvetica', 13)).pack(pady=5)

        self.password_entry = tk.Entry(self.password_window, show="*", font=('Helvetica', 13))
        self.password_entry.pack(pady=5)

        button_frame = tk.Frame(self.password_window)
        button_frame.pack(pady=5)

        tk.Button(button_frame, text="OK", command=self.verify_password, font=('Helvetica', 13), padx=30, pady=30).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="Отмена", command=self.cancel_operation, font=('Helvetica', 13), padx=10, pady=10).pack(side=tk.RIGHT, padx=5)

        self.password_entry.bind('<Return>', lambda event: self.verify_password())
        self.password_window.grab_set()
        self.root.withdraw()

    # Проверка введеного пароля
    def verify_password(self):
        password = self.password_entry.get()
        try:
            result = subprocess.run(
                ['sudo', '-S', 'true'],
                input=password.encode(),
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                check=True
            )
            self.password_window.destroy()
            self.root.deiconify()
            self.check_zapret_installed()
        except subprocess.CalledProcessError:
            messagebox.showerror("Ошибка", "Неверный пароль!")
            self.password_entry.delete(0, tk.END)

    def cancel_operation(self):
        self.root.destroy()

    def check_zapret_installed(self):
        try:
            result = subprocess.run(['systemctl', 'is-active', 'zapret'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if result.returncode == 0 or os.path.exists('/opt/zapret'):
                self.create_main_menu()
            else:
                self.show_install_dialog()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при проверке статуса Zapret DPI: {str(e)}")

    def check_status(self):
        self.show_status_window()

    def show_update_options(self):
        win = tk.Toplevel(self.root)
        win.title("Выбор обновления")
        win.geometry("400x200")

        tk.Label(win, text="Выберите, что обновить:", font=('Helvetica', 13)).pack(pady=10)

        tk.Button(win, text="Обновить всё (службы + Manager)",
                command=lambda: [win.destroy(), self.update_zapret()],
                font=('Helvetica', 12)).pack(pady=5, fill=tk.X, padx=20)

        tk.Button(win, text="Обновить только Manager",
                command=lambda: [win.destroy(), self.update_manager_only()],
                font=('Helvetica', 12)).pack(pady=5, fill=tk.X, padx=20)

        tk.Button(win, text="Обновить только службы",
                command=lambda: [win.destroy(), self.update_services_only()],
                font=('Helvetica', 12)).pack(pady=5, fill=tk.X, padx=20)

    def update_zapret(self):
        # Спрашиваем о бэкапе
        backup_choice = messagebox.askyesno(
            "Бэкап списков доменов",
            "Хотите создать бэкап всех списков доменов перед обновлением?\n\n"
            "Рекомендуется сделать бэкап, чтобы сохранить ваши настройки."
        )

        progress_window = tk.Toplevel(self.root)
        progress_window.title("Переустановка Zapret DPI")
        progress_window.geometry("350x120")
        progress_window.resizable(False, False)

        tk.Label(progress_window, text="Идет переустановка Zapret DPI...", font=('Helvetica', 13)).pack(pady=10)

        progress = ttk.Progressbar(progress_window, mode='indeterminate')
        progress.pack(pady=5)
        progress.start()

        status_label = tk.Label(progress_window, text="Создание бэкапа...", font=('Helvetica', 11))
        status_label.pack(pady=5)

        def run_update():
            must_lock = True
            try:
                # Создаем бэкап конфигурационных файлов если пользователь согласился
                if backup_choice:
                    status_label.config(text="Создание бэкапа конфигураций...")
                    if not self.backup_config_files():
                        pass
                else:
                    status_label.config(text="Пропуск бэкапа...")

                # Проверяем и устанавливаем зависимости
                status_label.config(text="Проверка зависимостей...")
                if not self.install_dependencies():
                    raise RuntimeError("Не удалось установить зависимости")

                # Удаляем старую версию Zapret (с пропуском ошибок)
                status_label.config(text="Удаление старой версии...")
                try:
                    if not self.unlock_filesystem():
                        return

                    # Пытаемся остановить и отключить службу (игнорируем ошибки)
                    subprocess.run(['sudo', 'systemctl', 'disable', 'zapret'], check=False)
                    subprocess.run(['sudo', 'systemctl', 'stop', 'zapret'], check=False)

                    # Удаляем файлы службы (игнорируем ошибки если файлов нет)
                    subprocess.run(['sudo', 'rm', '-rf', '/usr/lib/systemd/system/zapret.service'], check=False)
                    subprocess.run(['sudo', 'rm', '-rf', '/opt/zapret'], check=False)

                finally:
                    pass  # Блокировка будет в основном finally

                # Удаляем папку zapret (игнорируем ошибки)
                subprocess.run(['sudo', 'rm', '-rf', '/home/deck/zapret'], check=False)

                # Скачиваем обновление
                status_label.config(text="Скачивание обновления...")
                if not self.install_zapret_dpi_manager():
                    raise RuntimeError("Не удалось скачать Zapret DPI Manager")

                # Устанавливаем Zapret
                status_label.config(text="Установка Zapret DPI...")
                if not self.install_zapret_dpi():
                    raise RuntimeError("Не удалось скачать службу Zapret DPI")

                # Восстанавливаем конфигурационные файлы если был сделан бэкап
                if backup_choice:
                    status_label.config(text="Восстановление конфигураций...")
                    if not self.restore_config_files():
                        pass
                else:
                    status_label.config(text="Завершение обновления...")

                self.lock_filesystem()

                progress_window.destroy()

                if backup_choice:
                    messagebox.showinfo("Успех", "Zapret DPI успешно переустановлен\nБэкап конфигураций восстановлен")
                else:
                    messagebox.showinfo("Успех", "Zapret DPI успешно переустановлен")

                self.create_main_menu()

                # Перезапуск приложения
                python = sys.executable
                os.execl(python, python, *sys.argv)

            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Ошибка", f"Ошибка при переустановке: {str(e)}")

        threading.Thread(target=run_update).start()

    def update_manager_only(self):
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Обновление Manager")
        progress_window.geometry("350x140")
        progress_window.resizable(False, False)

        tk.Label(progress_window, text="Обновление Zapret DPI Manager...", font=('Helvetica', 13)).pack(pady=10)
        progress = ttk.Progressbar(progress_window, mode='indeterminate')
        progress.pack(pady=5)
        progress.start()

        status_label = tk.Label(progress_window, text="Подготовка...", font=('Helvetica', 11))
        status_label.pack(pady=5)

        def run_update_manager():
            try:
                temp_dir = "/tmp/zapret_manager_update"
                os.makedirs(temp_dir, exist_ok=True)

                status_label.config(text="Удаление старого zapret.py...")
                subprocess.run(['sudo', 'rm', '-f', '/home/deck/zapret/zapret.py'], check=False)

                status_label.config(text="Скачивание архива...")
                subprocess.run([
                    'wget', '-O', os.path.join(temp_dir, 'zapret_dpi_manager.zip'),
                    'https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/releases/latest/download/zapret_dpi_manager.zip'
                ], check=True)

                status_label.config(text="Извлечение zapret.py...")
                subprocess.run(['unzip', '-o', 'zapret_dpi_manager.zip', 'zapret.py'], cwd=temp_dir, check=True)

                status_label.config(text="Установка нового zapret.py...")
                subprocess.run(['cp', os.path.join(temp_dir, 'zapret.py'), '/home/deck/zapret/zapret.py'], check=True)
                subprocess.run(['sudo', 'chmod', '+x', '/home/deck/zapret/zapret.py'], check=True)

                status_label.config(text="Очистка временных файлов...")
                subprocess.run(['rm', '-rf', temp_dir], check=True)

                progress_window.destroy()
                messagebox.showinfo("Успех", "Zapret DPI Manager успешно обновлён.\nПриложение будет перезапущено.")

                # Перезапуск приложения
                python = sys.executable
                os.execl(python, python, *sys.argv)

            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Ошибка", f"Ошибка при обновлении Manager: {str(e)}")

        threading.Thread(target=run_update_manager).start()


    def update_services_only(self):
        backup_choice = messagebox.askyesno(
            "Бэкап конфигурации",
            "Хотите создать бэкап списков доменов перед обновлением?\n\n"
            "Рекомендуется сделать бэкап."
        )

        progress_window = tk.Toplevel(self.root)
        progress_window.title("Обновление службы Zapret DPI")
        progress_window.geometry("350x140")
        progress_window.resizable(False, False)

        tk.Label(progress_window, text="Обновление службы Zapret DPI...", font=('Helvetica', 13)).pack(pady=10)
        progress = ttk.Progressbar(progress_window, mode='indeterminate')
        progress.pack(pady=5)
        progress.start()

        status_label = tk.Label(progress_window, text="Подготовка...", font=('Helvetica', 11))
        status_label.pack(pady=5)

        def run_update_service():
            try:
                temp_dir = "/tmp/zapret_service_update"
                os.makedirs(temp_dir, exist_ok=True)

                if backup_choice:
                    status_label.config(text="Создание бэкапа конфигураций...")
                    self.backup_config_files()

                if not self.unlock_filesystem():
                    raise RuntimeError("Не удалось разблокировать файловую систему")

                status_label.config(text="Остановка службы...")
                subprocess.run(['sudo', 'systemctl', 'disable', 'zapret'], check=False)
                subprocess.run(['sudo', 'systemctl', 'stop', 'zapret'], check=False)

                status_label.config(text="Удаление старых файлов...")
                subprocess.run(['sudo', 'rm', '-rf', '/usr/lib/systemd/system/zapret.service'], check=False)
                subprocess.run(['sudo', 'rm', '-rf', '/opt/zapret'], check=False)

                status_label.config(text="Скачивание архива...")
                subprocess.run([
                    'wget', '-O', os.path.join(temp_dir, 'zapret_dpi_manager.zip'),
                    'https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/releases/latest/download/zapret_dpi_manager.zip'
                ], check=True)

                status_label.config(text="Извлечение zapret.zip...")
                subprocess.run(['unzip', '-o', 'zapret_dpi_manager.zip'], cwd=temp_dir, check=True)
                zapret_zip_path = os.path.join(temp_dir, "zapret.zip")
                if not os.path.exists(zapret_zip_path):
                    raise RuntimeError("Файл zapret.zip не найден внутри zapret_dpi_manager.zip")

                status_label.config(text="Копирование zapret.zip...")
                os.makedirs("/home/deck/zapret", exist_ok=True)
                subprocess.run(['cp', zapret_zip_path, '/home/deck/zapret/zapret.zip'], check=True)

                status_label.config(text="Установка службы...")
                if not self.install_zapret_dpi():
                    raise RuntimeError("Ошибка установки службы Zapret DPI")

                if backup_choice:
                    status_label.config(text="Восстановление конфигураций...")
                    self.restore_config_files()

                status_label.config(text="Финализация...")
                self.lock_filesystem()

                subprocess.run(['rm', '-rf', temp_dir], check=True)

                progress_window.destroy()
                messagebox.showinfo("Успех", "Службы Zapret DPI успешно обновлены")
                self.create_main_menu()

            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Ошибка", f"Ошибка при обновлении службы: {str(e)}")

        threading.Thread(target=run_update_service).start()


    def uninstall_zapret(self):
        if not os.path.exists('/opt/zapret'):
            messagebox.showinfo("Информация", "Zapret DPI не установлен")
            return

        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить Zapret DPI?"):
            # Создаем окно прогресса
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Удаление Zapret DPI")
            progress_window.geometry("350x120")
            progress_window.resizable(False, False)
            progress_window.grab_set()

            tk.Label(progress_window, text="Идет удаление Zapret DPI...", font=('Helvetica', 13)).pack(pady=10)

            progress = ttk.Progressbar(progress_window, mode='indeterminate')
            progress.pack(pady=5, padx=20, fill=tk.X)
            progress.start()

            status_label = tk.Label(progress_window, text="Подготовка...", font=('Helvetica', 11))
            status_label.pack(pady=5)

            def run_uninstall():
                must_lock = True
                try:
                    if not self.unlock_filesystem():
                        raise RuntimeError("Не удалось разблокировать файловую систему")

                    # Удаляем Zapret (с пропуском ошибок)
                    status_label.config(text="Остановка службы...")
                    subprocess.run(['sudo', 'systemctl', 'disable', 'zapret'], check=False)

                    status_label.config(text="Отключение автозапуска...")
                    subprocess.run(['sudo', 'systemctl', 'stop', 'zapret'], check=False)

                    status_label.config(text="Удаление файлов службы...")
                    subprocess.run(['sudo', 'rm', '-rf', '/usr/lib/systemd/system/zapret.service'], check=False)

                    status_label.config(text="Удаление основных файлов...")
                    subprocess.run(['sudo', 'rm', '-rf', '/opt/zapret'], check=False)

                    status_label.config(text="Удаление зависимостей...")
                    # Удаляем зависимости (только ipset, игнорируем ошибки)
                    subprocess.run(['sudo', 'pacman', '-Rns', '--noconfirm', 'ipset'], check=False)

                    status_label.config(text="Удаление ярлыков...")
                    # Удаляем ярлык с рабочего стола (игнорируем ошибки)
                    subprocess.run(['sudo', 'rm', '/home/deck/Desktop/Zapret-DPI.desktop'], check=False)

                    status_label.config(text="Удаление папки zapret...")
                    # Удаляем папку zapret (игнорируем ошибки)
                    subprocess.run(['sudo', 'rm', '-rf', '/home/deck/zapret'], check=False)

                    status_label.config(text="Восстановление системы...")
                    # Возвращаем значение в pacman.conf
                    if not self.fix_pacman_conf_for_uninstall():
                        pass

                    self.lock_filesystem()

                    progress_window.destroy()
                    messagebox.showinfo("Успех", "Zapret DPI и зависимости успешно удалены")
                    self.root.destroy()

                except Exception as e:
                    progress_window.destroy()
                    messagebox.showerror("Ошибка", f"Ошибка при удалении: {str(e)}")


            # Запускаем в отдельном потоке
            threading.Thread(target=run_uninstall, daemon=True).start()

    def handle_systemctl_error(self, operation, error_msg):
        """Обработка ошибок systemctl с предложением восстановления службы"""
        if messagebox.askyesno("Ошибка службы",
                            f"Служба zapret.service повреждена.\nХотите восстановить службу?"):
            self.restore_zapret_service()

    def restore_zapret_service(self):
        """Восстанавливает службу zapret.service"""
        try:
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Восстановление службы")
            progress_window.geometry("350x120")
            progress_window.resizable(False, False)

            tk.Label(progress_window, text="Восстановление zapret.service...", font=('Helvetica', 13)).pack(pady=10)

            progress = ttk.Progressbar(progress_window, mode='indeterminate')
            progress.pack(pady=5)
            progress.start()

            status_label = tk.Label(progress_window, text="Создание службы...", font=('Helvetica', 11))
            status_label.pack(pady=5)

            def run_restore():
                try:
                    if not self.unlock_filesystem():
                        raise RuntimeError("Не удалось разблокировать файловую систему")

                    # Создаем службу
                    status_label.config(text="Создание файла службы...")
                    service_content = """[Unit]
    Description=zapret
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=oneshot
    RemainAfterExit=yes
    WorkingDirectory=/opt/zapret
    ExecStart=/bin/bash /opt/zapret/system/starter.sh
    ExecStop=/bin/bash /opt/zapret/system/stopper.sh

    [Install]
    WantedBy=multi-user.target"""

                    # Создаем временный файл
                    temp_service = "/tmp/zapret.service"
                    with open(temp_service, 'w') as f:
                        f.write(service_content)

                    # Копируем с правами sudo
                    subprocess.run(['sudo', 'cp', temp_service, '/usr/lib/systemd/system/zapret.service'], check=True)
                    subprocess.run(['sudo', 'chmod', '644', '/usr/lib/systemd/system/zapret.service'], check=True)

                    # Обновляем демон systemd
                    status_label.config(text="Обновление systemd...")
                    subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)

                    # Запускаем и включаем службу
                    status_label.config(text="Запуск службы...")
                    subprocess.run(['sudo', 'systemctl', 'start', 'zapret'], check=True)
                    subprocess.run(['sudo', 'systemctl', 'enable', 'zapret'], check=True)

                    progress_window.destroy()
                    messagebox.showinfo("Успех", "Служба zapret.service успешно восстановлена")
                    self.update_service_tab()

                except Exception as e:
                    progress_window.destroy()
                    messagebox.showerror("Ошибка", f"Не удалось восстановить службу: {str(e)}")
                finally:
                    self.lock_filesystem()

            threading.Thread(target=run_restore).start()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при восстановлении службы: {str(e)}")


    def restart_service(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', 'zapret'], check=True)
            self.update_strategy_display()
            messagebox.showinfo("Успех", "Служба Zapret DPI перезапущена")
            self.update_service_tab()
        except subprocess.CalledProcessError as e:
            self.handle_systemctl_error("перезапуске службы", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при перезапуске службы: {str(e)}")

    def stop_service(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'stop', 'zapret'], check=True)
            messagebox.showinfo("Успех", "Служба Zapret DPI остановлена")
            self.update_service_tab()
        except subprocess.CalledProcessError as e:
            self.handle_systemctl_error("остановке службы", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при остановке службы: {str(e)}")

    def start_service(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'start', 'zapret'], check=True)
            messagebox.showinfo("Успех", "Служба Zapret DPI запущена")
            self.update_service_tab()
        except subprocess.CalledProcessError as e:
            self.handle_systemctl_error("запуске службы", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при запуске службы: {str(e)}")

    def disable_autorun(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'disable', 'zapret'], check=True)
            messagebox.showinfo("Успех", "Автозапуск службы Zapret DPI отключен")
            self.update_service_tab()
        except subprocess.CalledProcessError as e:
            self.handle_systemctl_error("отключении автозапуска", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при отключении автозапуска: {str(e)}")

    def enable_autorun(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'enable', 'zapret'], check=True)
            messagebox.showinfo("Успех", "Автозапуск службы Zapret DPI включен")
            self.update_service_tab()
        except subprocess.CalledProcessError as e:
            self.handle_systemctl_error("включении автозапуска", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при включении автозапуска: {str(e)}")

    def update_service_tab(self):
        """Обновляет только вкладку управления службами, сохраняя текущее положение"""
        # Запоминаем текущую вкладку
        current_tab = self.notebook.index(self.notebook.select())

        # Обновляем весь интерфейс
        self.create_main_menu()

        # Возвращаемся на вкладку управления службами
        self.notebook.select(current_tab)

    def open_autohosts(self):
        try:
            autohosts_path = "/opt/zapret/autohosts.txt"
            if os.path.exists(autohosts_path):
                subprocess.run(['xdg-open', autohosts_path])
            else:
                messagebox.showerror("Ошибка", "Файл autohosts.txt не найден")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {str(e)}")

    def open_ignore(self):
        try:
            ignore_path = "/opt/zapret/ignore.txt"
            if os.path.exists(ignore_path):
                subprocess.run(['xdg-open', ignore_path])
            else:
                messagebox.showerror("Ошибка", "Файл ignore.txt не найден")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {str(e)}")

    def open_lists_folder(self):
        try:
            lists_path = "/opt/zapret/lists"
            if os.path.exists(lists_path):
                subprocess.run(['xdg-open', lists_path])
            else:
                messagebox.showerror("Ошибка", "Папка lists не найдена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {str(e)}")

    def open_config(self):
        try:
            ignore_path = "/opt/zapret/config.txt"
            if os.path.exists(ignore_path):
                subprocess.run(['xdg-open', ignore_path])
            else:
                messagebox.showerror("Ошибка", "Файл config.txt не найден")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {str(e)}")
            
    def open_strategy(self):
        try:
            strategy_path = os.path.join(self.zapret_manager_working_dir_path, self.zapret_manager_strategy_dir)
            if os.path.exists(strategy_path):
                subprocess.run(['xdg-open', strategy_path])
            else:
                messagebox.showerror("Ошибка", "Папка strategy не найдена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {str(e)}")

    def backup_config_files(self):
        """Создает бэкап конфигурационных файлов и папки lists"""
        try:
            backup_dir = "/home/deck/zapret_backup"
            os.makedirs(backup_dir, exist_ok=True)

            files_to_backup = [
                ("/opt/zapret/autohosts.txt", "autohosts.txt"),
                ("/opt/zapret/ignore.txt", "ignore.txt"),
                ("/opt/zapret/config.txt", "config.txt")
            ]

            backed_up_files = []

            # Бэкап файлов
            for source_path, filename in files_to_backup:
                if os.path.exists(source_path):
                    backup_path = os.path.join(backup_dir, filename)
                    subprocess.run(['sudo', 'cp', source_path, backup_path], check=True)
                    subprocess.run(['sudo', 'chown', 'deck:deck', backup_path], check=True)
                    backed_up_files.append(filename)

            # Бэкап папки lists
            lists_source = "/opt/zapret/lists"
            lists_backup = os.path.join(backup_dir, "lists")
            if os.path.exists(lists_source):
                subprocess.run(['sudo', 'cp', '-r', lists_source, lists_backup], check=True)
                subprocess.run(['sudo', 'chown', '-R', 'deck:deck', lists_backup], check=True)
                backed_up_files.append("lists")

            print(f"Создан бэкап файлов: {', '.join(backed_up_files)}")
            return True
        except Exception as e:
            print(f"Ошибка при создании бэкапа: {str(e)}")
            return False

    def restore_config_files(self):
        """Восстанавливает конфигурационные файлы и папку lists из бэкапа"""
        try:
            backup_dir = "/home/deck/zapret_backup"

            files_to_restore = [
                ("autohosts.txt", "/opt/zapret/autohosts.txt"),
                ("ignore.txt", "/opt/zapret/ignore.txt"),
                ("config.txt", "/opt/zapret/config.txt")
            ]

            # Восстанавливаем файлы
            for backup_filename, target_path in files_to_restore:
                backup_path = os.path.join(backup_dir, backup_filename)
                if os.path.exists(backup_path):
                    subprocess.run(['sudo', 'cp', backup_path, target_path], check=True)
                    subprocess.run(['sudo', 'chmod', '644', target_path], check=True)

            # Восстанавливаем папку lists
            lists_backup = os.path.join(backup_dir, "lists")
            lists_target = "/opt/zapret/lists"
            if os.path.exists(lists_backup):
                # Удаляем старую папку lists если существует
                if os.path.exists(lists_target):
                    subprocess.run(['sudo', 'rm', '-rf', lists_target], check=True)
                # Копируем бэкап
                subprocess.run(['sudo', 'cp', '-r', lists_backup, lists_target], check=True)
                subprocess.run(['sudo', 'chmod', '-R', '644', lists_target], check=True)

            # Удаляем папку бэкапа после успешного восстановления
            if os.path.exists(backup_dir):
                subprocess.run(['sudo', 'rm', '-rf', backup_dir], check=True)
                print("Папка бэкапа удалена после восстановления")

            return True
        except Exception as e:
            print(f"Ошибка при восстановлении бэкапа: {str(e)}")
            return False


    def fix_protondb_dns(self):
        """Добавляет DNS для работы с Protondb и перезапускает службу"""
        try:
            # Создаем резервную копию
            subprocess.run(["sudo", "cp", "/etc/systemd/resolved.conf", "/etc/systemd/resolved.conf.backup"], check=True)

            # Читаем и модифицируем файл
            with open("/etc/systemd/resolved.conf", "r") as f:
                lines = f.readlines()

            # Удаляем старые DNS настройки если есть
            lines = [line for line in lines if not line.startswith("DNS=")]

            # Добавляем новую DNS настройку в конец
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.append("DNS=1.1.1.1\n")

            # Записываем обратно
            with open("/tmp/resolved.conf.new", "w") as f:
                f.writelines(lines)

            # Копируем с правами sudo
            subprocess.run(["sudo", "cp", "/tmp/resolved.conf.new", "/etc/systemd/resolved.conf"], check=True)
            subprocess.run(["sudo", "rm", "/tmp/resolved.conf.new"], check=True)

            # Перезапускаем службу
            subprocess.run(["sudo", "systemctl", "restart", "systemd-resolved"], check=True)
            subprocess.run(["sudo", "systemctl", "enable", "systemd-resolved"], check=True)

            messagebox.showinfo("Успех", "DNS для ProtonDB успешно добавлен!\nСлужба перезапущена.")

        except subprocess.CalledProcessError as e:
            messagebox.showerror("Ошибка", f"Ошибка выполнения команды: {str(e)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось настроить DNS: {str(e)}")

    def fix_update_applications(self):
        """Модифицирует pacman.conf и инициализирует ключи"""
        # Создаем окно ожидания
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Обновление программ")
        progress_window.geometry("400x120")
        progress_window.resizable(False, False)
        progress_window.grab_set()

        tk.Label(progress_window, text="Идет обновление программ...",
                font=('Helvetica', 13)).pack(pady=10)

        progress = ttk.Progressbar(progress_window, mode='indeterminate')
        progress.pack(pady=5, padx=20, fill=tk.X)
        progress.start()

        status_label = tk.Label(progress_window, text="Подготовка...",
                            font=('Helvetica', 11))
        status_label.pack(pady=5)

        def run_update():
            try:
                if not self.unlock_filesystem():
                    raise RuntimeError("Не удалось разблокировать файловую систему")

                # Обновляем статус
                status_label.config(text="Обновление openh264...")
                progress_window.update()

                # Обновляем базу пакетов и устанавливаем openh264
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', 'openh264'], check=True)

                # Обновляем статус
                status_label.config(text="Обновление flatpak приложений...")
                progress_window.update()

                # Обновляем flatpak приложения
                subprocess.run(['flatpak', 'update', '-y'], check=True)

                progress_window.destroy()
                messagebox.showinfo("Успех", "Программы успешно обновлены!")

            except subprocess.CalledProcessError as e:
                progress_window.destroy()
                messagebox.showerror("Ошибка", f"Ошибка выполнения команды: {str(e)}")
            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Ошибка", f"Ошибка обновления: {str(e)}")
            finally:
                self.lock_filesystem()

        # Запускаем в отдельном потоке
        threading.Thread(target=run_update, daemon=True).start()


    # Экран установки
    def show_install_dialog(self):
        self.install_window = tk.Toplevel(self.root)
        self.install_window.title("Установка Zapret DPI")
        self.install_window.geometry("400x100")
        self.install_window.resizable(False, False)

        tk.Label(self.install_window, text="Zapret DPI не установлен. Установить?", font=('Helvetica', 13)).pack(pady=10)

        button_frame = tk.Frame(self.install_window)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Установить Zapret DPI",
                 command=self.install_zapret, font=('Helvetica', 13)).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Отмена",
                 command=self.cancel_operation, font=('Helvetica', 13)).pack(side=tk.RIGHT, padx=10)

        self.install_window.grab_set()
        self.root.withdraw()

    # Управление Hosts для разблокировки сайтов
    def get_hosts_block(self, keyword):
        """
        Ищет и возвращает блок строк для заданного ключевого слова из /opt/zapret/hosts.
        Блок: ключевое слово и все строки ниже до первой пустой строки или конца файла.
        """
        try:
            if not os.path.exists(self.ZAPRET_HOSTS_PATH):
                return None, f"Файл {self.ZAPRET_HOSTS_PATH} не найден. Проверьте путь и наличие файла."

            with open(self.ZAPRET_HOSTS_PATH, 'r', encoding='utf-8') as f:
                content = f.read()

            pattern = re.compile(
                rf"^{re.escape(keyword)}\s*\n(.*?)(?:\n\s*\n|\Z)",
                re.MULTILINE | re.DOTALL
            )

            match = pattern.search(content)

            if match:
                # Возвращаем ключевое слово и все захваченные строки.
                # Важно: ключевое слово и первая строка после него должны быть в блоке.
                block_lines = [keyword] + match.group(1).strip().split('\n')
                # Удаляем пустые строки, если они есть
                block = '\n'.join([line.strip() for line in block_lines if line.strip()])
                return block, None
            else:
                return None, f"Ключевое слово '{keyword}' не найдено в {self.ZAPRET_HOSTS_PATH}. Проверьте формат файла."

        except Exception as e:
            return None, f"Ошибка при чтении hosts-файла: {str(e)}"

    def is_site_unblocked(self, keyword):
        """Проверяет, присутствует ли блок для ключевого слова в /etc/hosts."""
        try:
            with open(self.ETC_HOSTS_PATH, 'r', encoding='utf-8') as f:
                content = f.read()

            # Ищем ключевое слово, за которым следует перевод строки и любая непустая строка
            # (чтобы избежать ложных срабатываний, если ключевое слово упоминается в комментарии)
            pattern = re.compile(rf"^{re.escape(keyword)}\s*\n\s*\S+", re.MULTILINE)
            return bool(pattern.search(content))
        except Exception as e:
            print(f"Ошибка при проверке /etc/hosts: {str(e)}")
            return False

    def unblock_site(self, keyword):
        """
        Разблокирует сайт: добавляет блок из /opt/zapret/hosts в /etc/hosts.
        """
        block, error = self.get_hosts_block(keyword)
        if error:
            messagebox.showerror("Ошибка разблокировки", error)
            return

        # Добавляем пустую строку в конце для разделения
        # block уже содержит ключевое слово и содержимое
        content_to_add = "\n" + block.strip() + "\n\n"

        try:
            # Создаем временный файл с содержимым для добавления
            temp_path = f"/tmp/hosts_add_{keyword}"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content_to_add)

            # Используем tee и sudo для безопасной записи в конец /etc/hosts
            subprocess.run([
                'sudo', 'sh', '-c', f'cat {temp_path} >> {self.ETC_HOSTS_PATH}'
            ], check=True)

            os.remove(temp_path)

            messagebox.showinfo("Успех", f"Доступ к сайту {keyword} включен!")
            self.update_site_access_tab()

        except subprocess.CalledProcessError as e:
            messagebox.showerror("Ошибка добавления в файл", f"Не удалось записать в /etc/hosts: {e}")
        except Exception as e:
            messagebox.showerror("Ошибка добавления в файл", f"Общая ошибка: {str(e)}")

    def block_site(self, keyword):
        """Блокирует сайт: удаляет блок для ключевого слова из /etc/hosts."""
        try:
            # 1. Читаем содержимое /etc/hosts
            with open(self.ETC_HOSTS_PATH, 'r', encoding='utf-8') as f:
                original_content = f.read()

            import re
            # 2. ИСПРАВЛЕННЫЙ ШАБЛОН ДЛЯ УДАЛЕНИЯ:
            # Ищем: (0 или более пустых строк/пробелов) + КЛЮЧЕВОЕ СЛОВО + (любые символы, кроме
            # КЛЮЧЕВОГО СЛОВА, нежадным способом) до конца блока.
            # (?:\n\s*?)? - нежадно захватывает предыдущие пустые строки/пробелы.
            # (?:.*?)(?=(?:^\s*[^#\s]|\Z)) - ищет конец блока перед следующей некомментированной строкой или концом файла.

            # Мы используем более простое решение, гарантирующее, что захват заканчивается
            # на следующей пустой строке или конце файла:
            pattern = re.compile(
                rf"(?:^\s*)?^({re.escape(keyword)}\s*\n.*?)(?:^\s*\n|\Z)",
                re.MULTILINE | re.DOTALL
            )

            # Удаляем совпадение. Замена на пустую строку, затем нормализуем пустые строки.
            new_content = pattern.sub('', original_content).strip() + '\n'

            # 3. Записываем новое содержимое обратно с sudo
            temp_path = f"/tmp/hosts_new_{keyword}"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            subprocess.run(['sudo', 'cp', temp_path, self.ETC_HOSTS_PATH], check=True)
            subprocess.run(['sudo', 'chmod', '644', self.ETC_HOSTS_PATH], check=True)

            os.remove(temp_path)

            # Принудительная перерисовка GUI
            if self.root.winfo_exists():
                self.update_button_states()
                self.root.update_idletasks()

            messagebox.showinfo("Успех", f"Доступ к сайту {keyword} отключен!")

        except subprocess.CalledProcessError as e:
            messagebox.showerror("Ошибка удаления из файла", f"Не удалось удалить из /etc/hosts: {e}")
        except Exception as e:
            messagebox.showerror("Ошибка удаления из файла", f"Общая ошибка: {str(e)}")

    def toggle_site_access(self, keyword):
        """Переключает состояние включения/отключения доступа к сайту."""
        if self.is_site_unblocked(keyword):
            self.block_site(keyword)
        else:
            self.unblock_site(keyword)

    def update_site_access_tab(self):
        self.update_button_states()


    def open_zapret_hosts(self):
        """Открывает файл /opt/zapret/hosts для редактирования"""
        try:
            if os.path.exists(self.ZAPRET_HOSTS_PATH):
                subprocess.run(['xdg-open', self.ZAPRET_HOSTS_PATH])
            else:
                messagebox.showerror("Ошибка", f"Файл {self.ZAPRET_HOSTS_PATH} не найден")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {str(e)}")

    def open_etc_hosts(self):
        """Открывает файл /etc/hosts для просмотра"""
        try:
            if os.path.exists(self.ETC_HOSTS_PATH):
                # Используем xdg-open для открытия в текстовом редакторе по умолчанию
                subprocess.run(['xdg-open', self.ETC_HOSTS_PATH])
            else:
                messagebox.showerror("Ошибка", f"Файл {self.ETC_HOSTS_PATH} не найден")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {str(e)}")



    def update_button_states(self):
        """Обновляет текст и состояние кнопок в зависимости от статуса службы"""
        if hasattr(self, 'service_control_btn'):
            if self.is_service_active():
                self.service_control_btn.config(text="Остановить службу")
            else:
                self.service_control_btn.config(text="Запустить службу")

            if self.is_service_enabled():
                self.autostart_btn.config(text="Отключить автозапуск")
            else:
                self.autostart_btn.config(text="Включить автозапуск")

        """Обновляет текст и состояние кнопок в зависимости от статуса доступа к сайту"""
        if hasattr(self, 'site_buttons'):
            for name, keyword in self.AI_SITES.items():
                if keyword in self.site_buttons:
                    button = self.site_buttons[keyword]

                    if not button.winfo_exists():
                        continue

                    if self.is_site_unblocked(keyword):
                        button.config(text=f"Отключить доступ к {name}", style='TButton')
                    else:
                        button.config(text=f"Включить доступ к {name}", style='TButton')


    def toggle_service(self):
        """Переключает состояние службы"""
        if self.is_service_active():
            self.stop_service()
        else:
            self.start_service()
        self.update_button_states()

    def toggle_autostart(self):
        """Переключает автозапуск"""
        if self.is_service_enabled():
            self.disable_autorun()
        else:
            self.enable_autorun()
        self.update_button_states()
        
    # Ищем файлы в переданном пути и 
    # возвращаем массив названий файлов
    def get_file_list(self, target_dir_path: str) -> list[str]:
        files_name = []
        for item in os.listdir(target_dir_path):
            full_path = os.path.join(target_dir_path, item)
            if os.path.isfile(full_path):
                files_name.append(item)
        return files_name

    # Сообщение о том, какая стретегия выбрана
    def get_current_config(self) -> str:
        filename_with_ext = "Missing info"
        if os.path.exists(self.zapret_config_path):
            if os.path.islink(self.zapret_config_path):
                target_path = os.readlink(self.zapret_config_path)
                filename_with_ext = os.path.basename(target_path)
            else:
                subprocess.run(['sudo', 'rm', '-rf', self.zapret_config_path], check=False)
        
        return (f"Текущая стратегия: {filename_with_ext}\n")

    def update_strategy_display(self):
        """Обновляет отображение стратегии"""
        self.strategy_label.config(text=self.get_current_config())
        
    # Принимает путь до файла и путь, где необходимо создать symlink
    def create_symlink_to_file(self, source_path: str, target_path: str):
        try:
            subprocess.run(['sudo', 'ln', '-s', source_path, target_path], check=False)
            # os.symlink(source_path, target_path, target_is_directory=False)
        except Exception as e:
            print(f"Error creating symbolic link: {e}")
    
    # Принимает путь до symlink и удаляет его, если 
    # путь действительно ведёт на symlink
    def remove_symlink_to_file(self, symlink_path: str):
        if os.path.islink(symlink_path):
            try:
                subprocess.run(['sudo', 'unlink', symlink_path], check=False)
                os.unlink(symlink_path)
            except OSError as e:
                print(f"Error removing symbolic link '{symlink_path}': {e}")
                
    # Функция изменения стратегии
    def change_strategy(self, strategy_name: str):
        try:
            selected_strategy_path = os.path.join(self.zapret_manager_working_dir_path, self.zapret_manager_strategy_dir, strategy_name)
            self.remove_symlink_to_file(self.zapret_config_path)
            self.create_symlink_to_file(selected_strategy_path, self.zapret_config_path)
            
            messagebox.showinfo("Успех", f"Стратегия успешно применена. Перезапуск службы для применения изменений.")
            
            self.restart_service()
            self.update_strategy_display()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось применить конфигурацию: {str(e)}")

    # Установка Запрета
    def install_zapret(self):
        self.install_window.destroy()

        progress_window = tk.Toplevel(self.root)
        progress_window.title("Установка Zapret DPI")
        progress_window.geometry("300x100")
        progress_window.resizable(False, False)

        tk.Label(progress_window, text="Идет установка Zapret DPI...", font=('Helvetica', 13)).pack(pady=10)

        progress = ttk.Progressbar(progress_window, mode='indeterminate')
        progress.pack(pady=5)
        progress.start()

        def run_installation():
            try:
                # Проверяем и устанавливаем зависимости
                if not self.install_dependencies():
                    raise RuntimeError("Не удалось установить зависимости")

                # Устанавливаем Zapret
                if not self.install_zapret_dpi():
                     raise RuntimeError("Не удалось скачать службу")

                progress_window.destroy()
                messagebox.showinfo("Успех", "Zapret DPI успешно установлен")
                self.show_status_window()
            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Ошибка", f"Ошибка при установке: {str(e)}")
                self.root.deiconify()
            finally:
                self.lock_filesystem()

        threading.Thread(target=run_installation).start()

    # Окно с выводом статуса службы
    def show_status_window(self):
        self.status_window = tk.Toplevel(self.root)
        self.status_window.title("Статус Zapret DPI")
        self.status_window.geometry("680x350")
        self.status_window.resizable(False, False)

        tk.Label(self.status_window, text="В Loaded после zapret.service указывается автозапуск службы\nenabled - автозапуск службы запущен\ndisabled - автозапуск службы не запущен\nВ строке Active указывается запущена служба или нет\nactive (exited) - процесс службы завершился (не работает в фоне), но сама служба\nсчитается 'активной',\ninactive (dead) - служба не запущена", font=('Helvetica', 12)).pack(pady=5)

        status_text = scrolledtext.ScrolledText(self.status_window, height=5, font=('Helvetica', 12))
        status_text.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)

        try:
            result = subprocess.run(['systemctl', 'status', 'zapret'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            for line in result.stdout.split('\n'):
                if 'Loaded:' in line:
                    status_text.insert(tk.END, line + '\n')
                    break
            for line in result.stdout.split('\n'):
                if 'Active:' in line:
                    status_text.insert(tk.END, line + '\n')
                    break
        except Exception as e:
            status_text.insert(tk.END, f"Ошибка при получении статуса: {str(e)}")

        status_text.config(state=tk.DISABLED)

        tk.Button(self.status_window, text="Далее", font=('Helvetica', 13),
                  command=lambda: [self.status_window.destroy(),
                                self.create_main_menu()]).pack(pady=5)

        self.status_window.grab_set()
        self.root.withdraw()

    # Основной экран
    def create_main_menu(self):
        # Очищаем предыдущие виджеты
        for widget in self.root.winfo_children():
            widget.destroy()

        # Создаем Notebook (вкладки)
        self.notebook = ttk.Notebook(self.root)
        self.style.configure('TNotebook.Tab', font=('Helvetica', 15))
        self.notebook.pack(fill=tk.BOTH, expand=True)


        # Вкладка "Управление службой"
        service_frame = ttk.Frame(self.notebook)
        self.notebook.add(service_frame, text="Управление службой")

        # Строка статуса (компактная)
        status_frame = ttk.Frame(service_frame)
        status_frame.pack(fill=tk.X, pady=(10, 10), padx=5)

        self.strategy_label = ttk.Label(
            status_frame,
            text=self.get_current_config(),
            font=('Helvetica', 12, 'bold'),
            foreground='blue'
        )
        self.strategy_label.pack(side=tk.LEFT)

        # Сетка кнопок (2 колонки)
        buttons_frame = ttk.Frame(service_frame)
        buttons_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        buttons_frame.columnconfigure(0, weight=1, uniform='cols')
        buttons_frame.columnconfigure(1, weight=1, uniform='cols')

        # Динамические кнопки управления службой
        self.service_control_btn = ttk.Button(
            buttons_frame,
            command=self.toggle_service,
            style='TButton'
        )
        self.service_control_btn.grid(row=0, column=0, padx=3, pady=3, sticky='nsew')

        # Динамические кнопки автозапуска
        self.autostart_btn = ttk.Button(
            buttons_frame,
            command=self.toggle_autostart,
            style='TButton'
        )
        self.autostart_btn.grid(row=0, column=1, padx=3, pady=3, sticky='nsew')

        # Динамические кнопки (сохраняем как атрибуты)
        ttk.Button(
            buttons_frame,
            text="Проверка статуса",
            command=self.check_status,
            style='TButton'
        ).grid(row=1, column=0, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="Выход",
            command=self.root.destroy,
            style='TButton'
        ).grid(row=1, column=1, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="Исправление ProtonDB.com",
            command=self.fix_protondb_dns,
            style='TButton'
        ).grid(row=2, column=0, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="Обновление программ",
            command=self.fix_update_applications,
            style='TButton'
        ).grid(row=2, column=1, padx=3, pady=3, sticky='nsew')


        # Настройка строк
        for i in range(3):
            buttons_frame.rowconfigure(i, weight=0, minsize=30)

        # Обновляем состояние кнопок
        self.update_button_states()


        # =========== Вкладка "Стратегия" ===========
        config_frame = ttk.Frame(self.notebook)
        self.notebook.add(config_frame, text="Стратегия")

        # Строка статуса (компактная)
        status_frame = ttk.Frame(config_frame)
        status_frame.pack(fill=tk.X, pady=(10, 1), padx=5)

        self.strategy_label = ttk.Label(
            status_frame,
            text=self.get_current_config(),
            font=('Helvetica', 12, 'bold'),
            foreground='blue'
        )
        self.strategy_label.pack(side=tk.LEFT)

        note_text = "Для выбора стратегии, выберите конфиг в выпадающем меню"
        tk.Label(config_frame, text=note_text, justify=tk.LEFT, font=('Helvetica', 12)).pack(pady=(0, 5), padx=5, anchor=tk.W)
        
        def get_strategy_list():
            strategy_list = self.get_file_list(os.path.join(self.zapret_manager_working_dir_path, self.zapret_manager_strategy_dir))
            return strategy_list
        
        def onSelect_strategy_combobox(event):
            self.change_strategy(strategy_combobox.get())
            
        strategy_combobox = ttk.Combobox(config_frame, values=get_strategy_list())
        strategy_combobox.pack()
        strategy_combobox.bind("<<ComboboxSelected>>", onSelect_strategy_combobox)
        
        def onClick_update_strategy_button():
            strategy_combobox['values'] = get_strategy_list()
            
        # Сетка кнопок (2 колонки)
        buttons_frame = ttk.Frame(config_frame)
        buttons_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        buttons_frame.columnconfigure(0, weight=1, uniform='cols')
        buttons_frame.columnconfigure(1, weight=1, uniform='cols')
        
        ttk.Button(
            buttons_frame,
            text="Обновить список стратегий",
            command=onClick_update_strategy_button,
            style='TButton'
        ).grid(row=0, column=0, padx=3, pady=3, sticky='nsew')
        ttk.Button(
            buttons_frame,
            text="Открыть папку с стратегиями",
            command=self.open_strategy,
            style='TButton'
        ).grid(row=0, column=1, padx=3, pady=3, sticky='nsew')
        
        buttons_frame.rowconfigure(0, weight=0, minsize=30)
        # Обновляем состояние кнопок
        self.update_button_states()
        
        # =========== Вкладка "Стратегия" ===========

        # Вкладка "Списки доменов"
        domains_frame = ttk.Frame(self.notebook)
        self.notebook.add(domains_frame, text="Списки доменов")

        note_text = """Примечание:
Для Рослетелком/Теле2 и МТС:
- Не работает какой-то заблокированный сайт? Добавить его домен в autohosts.txt.
- Не работает незаблокированный сайт? Добавьте его домен в ignore.txt.
Для Общей стратегии: Можно редактировать списки доменов в папке lists."""

        tk.Label(domains_frame, text=note_text, justify=tk.LEFT, font=('Helvetica', 12)).pack(pady=10, padx=10, anchor=tk.W)

        # Сетка кнопок (2 колонки)
        buttons_frame = ttk.Frame(domains_frame)
        buttons_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        buttons_frame.columnconfigure(0, weight=1, uniform='cols')
        buttons_frame.columnconfigure(1, weight=1, uniform='cols')

        # Динамические кнопки (сохраняем как атрибуты)
        ttk.Button(
            buttons_frame,
            text="Добавить в autohosts.txt",
            command=self.open_autohosts,
            style='TButton'
        ).grid(row=0, column=0, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="Добавить в ignore.txt",
            command=self.open_ignore,
            style='TButton'
        ).grid(row=0, column=1, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="Открыть папку lists (Общая стратегия)",
            command=self.open_lists_folder,
            style='TButton'
        ).grid(row=1, column=0, columnspan=2, padx=3, pady=3, sticky='nsew')


        # Настройка строк
        for i in range(3):
            buttons_frame.rowconfigure(i, weight=0, minsize=30)

        # Обновляем состояние кнопок
        self.update_button_states()

        # Вкладка "Включить доступ к сайтам"
        sites_frame = ttk.Frame(self.notebook)
        self.notebook.add(sites_frame, text="Включить доступ к сайтам")

        note_text = "Выберите сайт для разблокировки/блокировки. Изменения вносятся в /etc/hosts.\nМожете добавить в файл hosts свой домен"
        tk.Label(sites_frame, text=note_text, justify=tk.LEFT, font=('Helvetica', 12)).pack(pady=(10, 5), padx=5, anchor=tk.W)

        # Сетка кнопок (3 колонки)
        sites_buttons_frame = ttk.Frame(sites_frame)
        sites_buttons_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        sites_buttons_frame.columnconfigure(0, weight=1, uniform='cols')
        sites_buttons_frame.columnconfigure(1, weight=1, uniform='cols')
        sites_buttons_frame.columnconfigure(2, weight=1, uniform='cols')

        self.site_buttons = {} # Словарь для хранения динамических кнопок

        # Создание кнопок в сетке (3 колонки)
        buttons_data = list(self.AI_SITES.items())

        for i, (name, keyword) in enumerate(buttons_data):
            row = i // 3
            col = i % 3

            button = ttk.Button(
                sites_buttons_frame,
                text=f"Включить доступ к {name}", # Начальный текст
                command=lambda k=keyword: self.toggle_site_access(k),
                style='TButton'
            )
            button.grid(row=row, column=col, padx=3, pady=3, sticky='nsew')
            self.site_buttons[keyword] = button # Сохраняем кнопку для динамического обновления

            sites_buttons_frame.rowconfigure(3, weight=0, minsize=30)

        # # Дополнительные кнопки для hosts-файлов
        # ttk.Button(
        #     sites_buttons_frame,
        #     text="Редактировать hosts-лист (/opt/zapret/hosts)",
        #     command=self.open_zapret_hosts,
        #     style='TButton'
        # ).grid(row=(len(buttons_data) // 3) + 1, column=0, columnspan=3, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            sites_buttons_frame,
            text="Просмотреть /etc/hosts",
            command=self.open_etc_hosts,
            style='TButton'
        ).grid(row=(len(buttons_data) // 3) + 2, column=0, columnspan=3, padx=3, pady=3, sticky='nsew')

        # Обновляем состояние кнопок (для этой вкладки)
        self.update_button_states()


        # Вкладка "Дополнительно"
        extra_frame = ttk.Frame(self.notebook)
        self.notebook.add(extra_frame, text="Дополнительно")

        note_text = """"""

        tk.Label(extra_frame, text=note_text, justify=tk.LEFT).pack(pady=10, padx=10, anchor=tk.W)

        buttons_frame.columnconfigure(0, weight=1, uniform='cols')
        buttons_frame.columnconfigure(1, weight=1, uniform='cols')

        # Сетка кнопок (2 колонки)
        buttons_frame = ttk.Frame(extra_frame)
        buttons_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        buttons_frame.columnconfigure(0, weight=1, uniform='cols')
        buttons_frame.columnconfigure(1, weight=1, uniform='cols')

        ttk.Button(
            buttons_frame,
            text="Обновить службу Zapret DPI и Manager",
            command=self.show_update_options,
            style='TButton'
        ).grid(row=2, column=0, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="Удалить службу Zapret DPI и Manager",
            command=self.uninstall_zapret,
            style='TButton'
        ).grid(row=2, column=1, padx=3, pady=3, sticky='nsew')





        # Добавляем версию в нижнюю часть окна
        version_frame = ttk.Frame(self.root)
        version_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        # Укажите вашу текущую версию здесь
        version_label = ttk.Label(version_frame, text=f"Zapret DPI Manager v.{self.version}", font=('Helvetica', 10))
        version_label.pack(side=tk.RIGHT, padx=10)

        self.root.deiconify()




if __name__ == "__main__":
    root = tk.Tk()
    app = ZapretGUI(root)
    root.mainloop()
