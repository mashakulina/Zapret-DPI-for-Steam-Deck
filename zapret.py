#!/usr/bin/env python3
import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys, os


class ZapretGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Zapret DPI Manager")
        self.root.geometry("685x350")
        self.version = "1.7"

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
        """Разблокирует файловую систему для записи"""
        try:
            subprocess.run(['sudo', 'steamos-readonly', 'disable'], check=True)
            return True
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Ошибка", f"Не удалось разблокировать файловую систему: {e}")
            return False

    def lock_filesystem(self):
        """Блокирует файловую систему обратно"""
        try:
            subprocess.run(['sudo', 'steamos-readonly', 'enable'], check=True)
            return True
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Ошибка", f"Не удалось заблокировать файловую систему: {e}")
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

            return True
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Ошибка", f"Ошибка при установке зависимостей: {e}")
            return False
        finally:
            self.lock_filesystem()

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

    def update_zapret(self):
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
            try:
                # Создаем бэкап конфигурационных файлов
                status_label.config(text="Создание бэкапа конфигураций...")
                if not self.backup_config_files():
                    print("Предупреждение: не удалось создать бэкап конфигурационных файлов")

                # Проверяем и устанавливаем зависимости
                status_label.config(text="Проверка зависимостей...")
                if not self.install_dependencies():
                    raise RuntimeError("Не удалось установить зависимости")

                # Удаляем старую версию Zapret
                status_label.config(text="Удаление старой версии...")
                try:
                    if not self.unlock_filesystem():
                        return

                    if os.path.exists('/opt/zapret'):
                        subprocess.run(['sudo', 'systemctl', 'disable', 'zapret'], check=True)
                        subprocess.run(['sudo', 'systemctl', 'stop', 'zapret'], check=True)
                        subprocess.run(['sudo', 'rm', '-rf', '/usr/lib/systemd/system/zapret.service'], check=True)
                        subprocess.run(['sudo', 'rm', '-rf', '/opt/zapret'], check=True)

                finally:
                    self.lock_filesystem()

                # Удаляем папку zapret
                subprocess.run(['sudo', 'rm', '-rf', '/home/deck/zapret'], check=True)

                # Скачиваем обновление
                status_label.config(text="Скачивание обновления...")
                if not self.install_zapret_dpi_manager():
                    raise RuntimeError("Не удалось скачать Zapret DPI Manager")

                # Устанавливаем Zapret
                status_label.config(text="Установка Zapret DPI...")
                if not self.install_zapret_dpi():
                    raise RuntimeError("Не удалось скачать службу Zapret DPI")

                # Восстанавливаем конфигурационные файлы
                status_label.config(text="Восстановление конфигураций...")
                if not self.restore_config_files():
                    print("Предупреждение: не удалось восстановить конфигурационные файлы")

                progress_window.destroy()
                messagebox.showinfo("Успех", "Zapret DPI успешно переустановлен")
                self.create_main_menu()

                # Перезапуск приложения
                python = sys.executable
                os.execl(python, python, *sys.argv)

            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Ошибка", f"Ошибка при переустановке: {str(e)}")

        threading.Thread(target=run_update).start()

    def uninstall_zapret(self):
        if not os.path.exists('/opt/zapret'):
            messagebox.showinfo("Информация", "Zapret DPI не установлен")
            return

        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить Zapret DPI?"):
            try:
                if not self.unlock_filesystem():
                    return

                # Удаляем Zapret
                subprocess.run(['sudo', 'systemctl', 'disable', 'zapret'], check=True)
                subprocess.run(['sudo', 'systemctl', 'stop', 'zapret'], check=True)
                subprocess.run(['sudo', 'rm', '-rf', '/usr/lib/systemd/system/zapret.service'], check=True)
                subprocess.run(['sudo', 'rm', '-rf', '/opt/zapret'], check=True)

                # Удаляем зависимости (только ipset)
                subprocess.run(['sudo', 'pacman', '-Rns', '--noconfirm', 'ipset'], check=True)

                # Удаляем ярлык с рабочего стола
                subprocess.run(['sudo', 'rm', '/home/deck/Desktop/Zapret-DPI.desktop'], check=True)

                # Удаляем папку zapret
                subprocess.run(['sudo', 'rm', '-rf', '/home/deck/zapret'], check=True)

                # Возвращаем значение в pacman.conf
                if not self.fix_pacman_conf_for_uninstall():
                    return False

                messagebox.showinfo("Успех", "Zapret DPI и зависимости успешно удалены")
                self.root.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при удалении: {str(e)}")
            finally:
                self.lock_filesystem()

    def restart_service(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', 'zapret'], check=True)
            self.update_strategy_display()  # Обновляем отображение
            messagebox.showinfo("Успех", "Служба Zapret DPI перезапущена")
            self.update_service_tab()  # Обновляем интерфейс
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при перезапуске службы: {str(e)}")

    def stop_service(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'stop', 'zapret'], check=True)
            messagebox.showinfo("Успех", "Служба Zapret DPI остановлена")
            self.update_service_tab()  # Обновляем интерфейс
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при остановке службы: {str(e)}")

    def start_service(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'start', 'zapret'], check=True)
            messagebox.showinfo("Успех", "Служба Zapret DPI запущена")
            self.update_service_tab()  # Обновляем интерфейс
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при запуске службы: {str(e)}")

    def disable_autorun(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'disable', 'zapret'], check=True)
            messagebox.showinfo("Успех", "Автозапуск службы Zapret DPI отключен")
            self.update_service_tab()  # Обновляем интерфейс
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при отключении автозапуска: {str(e)}")

    def enable_autorun(self):
        try:
            subprocess.run(['sudo', 'systemctl', 'enable', 'zapret'], check=True)
            messagebox.showinfo("Успех", "Автозапуск службы Zapret DPI включен")
            self.update_service_tab() # Обновляем интерфейс
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

    def open_config(self):
        try:
            ignore_path = "/opt/zapret/config.txt"
            if os.path.exists(ignore_path):
                subprocess.run(['xdg-open', ignore_path])
            else:
                messagebox.showerror("Ошибка", "Файл config.txt не найден")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {str(e)}")

    def backup_config_files(self):
        """Создает бэкап конфигурационных файлов"""
        try:
            backup_dir = "/home/deck/zapret_backup"
            os.makedirs(backup_dir, exist_ok=True)

            files_to_backup = [
                ("/opt/zapret/autohosts.txt", "autohosts.txt"),
                ("/opt/zapret/ignore.txt", "ignore.txt"),
                ("/opt/zapret/config.txt", "config.txt")
            ]

            for source_path, filename in files_to_backup:
                if os.path.exists(source_path):
                    backup_path = os.path.join(backup_dir, filename)
                    subprocess.run(['sudo', 'cp', source_path, backup_path], check=True)
                    subprocess.run(['sudo', 'chown', 'deck:deck', backup_path], check=True)

            return True
        except Exception as e:
            print(f"Ошибка при создании бэкапа: {str(e)}")
            return False

    def restore_config_files(self):
        """Восстанавливает конфигурационные файлы из бэкапа"""
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

    def update_button_states(self):
        """Обновляет текст и состояние кнопок в зависимости от статуса службы"""
        if self.is_service_active():
            self.service_control_btn.config(text="Остановить службу")
        else:
            self.service_control_btn.config(text="Запустить службу")

        if self.is_service_enabled():
            self.autostart_btn.config(text="Отключить автозапуск")
        else:
            self.autostart_btn.config(text="Включить автозапуск")

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


    # Сообщение о том, какая стретегия выбрана
    def get_current_config(self):
        """Возвращает текущую конфигурацию с определением провайдера"""
        config_path = "/opt/zapret/config.txt"

        try:
            with open(config_path, 'r') as f:
                first_line = f.readline().strip()
                content = first_line + "\n" + f.read()  # Читаем остальное содержимое

            # Определяем провайдера по первой строке
            provider = "Пользовательская"
            if "Ростелеком" in first_line:
                provider = "Ростелеком/Теле2"
            elif "МТС" in first_line:
                provider = "МТС"
            elif "Общая стратегия" in first_line:
                provider = "Общая стратегия"

            return (f"Текущая стратегия: {provider}\n")

        except Exception as e:
            return f"Ошибка чтения конфигурации: {str(e)}"

    def update_strategy_display(self):
        """Обновляет отображение стратегии"""
        self.strategy_label.config(text=self.get_current_config())



# ===========================================================
# ======================== СТРАТЕГИИ ========================
# ===========================================================

    # Стратегия для Ростелеокма/Теле2
    def config_rostelecom(self):
        config_path = "/opt/zapret/config.txt"
        config_content = """# Ростелеком/Теле2
--wf-tcp=80,443 --wf-udp=443,50000-59000
--filter-udp=443 --hostlist=/opt/zapret/autohosts.txt --hostlist-exclude=/opt/zapret/ignore.txt --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=/opt/zapret/system/quic_initial_www_google_com.bin --new
--filter-tcp=443 --hostlist=/opt/zapret/autohosts.txt --hostlist-exclude=/opt/zapret/ignore.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-cutoff=d2 --dpi-desync-ttl=4 --new
--filter-tcp=443 --hostlist=/opt/zapret/autohosts.txt --hostlist-exclude=/opt/zapret/ignore.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=/opt/zapret/system/tls_clienthello_www_google_com.bin --dpi-desync-ttl=3 --new
--filter-udp=50000-59000 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new
--filter-tcp=443 --hostlist=/opt/zapret/autohosts.txt --hostlist-exclude=/opt/zapret/ignore.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=/opt/zapret/system/tls_clienthello_www_google_com.bin --dpi-desync-ttl=2 --new"""

        # Записываем новую конфигурацию с sudo правами
        try:
            # Создаем временный файл
            temp_path = "/tmp/config.tmp"
            with open(temp_path, 'w') as f:
                f.write(config_content)

            # Копируем с sudo правами
            subprocess.run(['sudo', 'cp', temp_path, config_path], check=True)
            subprocess.run(['sudo', 'chmod', '644', config_path], check=True)

            messagebox.showinfo("Успех", f"Стратегия успешно применена. Перезапустите службу для применения изменений.")
            self.restart_service()
            self.update_strategy_display()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось применить конфигурацию: {str(e)}")
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # Стратегия для МТС
    def config_mts(self):
        """Применяет конфигурацию для выбранного провайдера"""
        config_path = "/opt/zapret/config.txt"
        config_content = """# МТС
--wf-tcp=80,443 --wf-udp=443,50000-59000
--filter-udp=443 --hostlist=/opt/zapret/autohosts.txt --hostlist-exclude=/opt/zapret/ignore.txt --dpi-desync=fake --dpi-desync-repeats=2 --dpi-desync-cutoff=n2 --dpi-desync-fake-quic=/opt/zapret/system/quic_initial_www_google_com.bin --new
--filter-tcp=443 --hostlist=/opt/zapret/autohosts.txt --hostlist-exclude=/opt/zapret/ignore.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=2 --dpi-desync-split-pos=3 --dpi-desync-fake-tls=/opt/zapret/system/tls_clienthello_www_google_com.bin --dpi-desync-ttl=3 --new
--filter-udp=443 --hostlist=/opt/zapret/autohosts.txt --hostlist-exclude=/opt/zapret/ignore.txt --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=7 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=/opt/zapret/system/quic_initial_www_google_com.bin --dpi-desync-cutoff=n2 --new
--filter-udp=50000-59000 --dpi-desync=fake,split2 --dpi-desync-any-protocol --dpi-desync-cutoff=d2 --dpi-desync-fake-quic=/opt/zapret/system/quic_initial_www_google_com.bin --new
--filter-tcp=443 --hostlist=/opt/zapret/autohosts.txt --hostlist-exclude=/opt/zapret/ignore.txt --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-ttl=4 --new
--filter-tcp=443 --hostlist=/opt/zapret/autohosts.txt --hostlist-exclude=/opt/zapret/ignore.txt --dpi-desync=fake,split2 --dpi-desync-split-seqovl=1 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=/opt/zapret/system/tls_clienthello_www_google_com.bin --dpi-desync-ttl=2 --new"""

        # Записываем новую конфигурацию с sudo правами
        try:
            # Создаем временный файл
            temp_path = "/tmp/config.tmp"
            with open(temp_path, 'w') as f:
                f.write(config_content)

            # Копируем с sudo правами
            subprocess.run(['sudo', 'cp', temp_path, config_path], check=True)
            subprocess.run(['sudo', 'chmod', '644', config_path], check=True)

            messagebox.showinfo("Успех", f"Стратегия успешно применена. Перезапустите службу для применения изменений.")
            self.restart_service()
            self.update_strategy_display()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось применить конфигурацию: {str(e)}")
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.remove(temp_path)


    # Стратегия Общая стратегия
    def config_all(self):
        """Применяет конфигурацию для выбранного провайдера"""
        config_path = "/opt/zapret/config.txt"
        config_content = """# Общая стратегия
--wf-l3=ipv4,ipv6 --wf-tcp=80,443,6695-6705 --wf-udp=443,50000-50100,1024-65535
--filter-tcp=443 --ipset=/opt/zapret/lists/russia-youtube-rtmps.txt --dpi-desync=syndata --dpi-desync-fake-syndata=/opt/zapret/bin/tls_clienthello_4.bin --dpi-desync-autottl --new
--filter-tcp=443 --hostlist=/opt/zapret/lists/youtube_v2.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld+1 --new
--filter-tcp=443 --hostlist=/opt/zapret/lists/youtubeGV.txt --dpi-desync=multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=midsld-1 --new
--filter-udp=443 --hostlist=/opt/zapret/lists/youtubeQ.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=4 --dpi-desync-fake-quic=/opt/zapret/bin/quic_3.bin --dpi-desync-cutoff=n3 --dpi-desync-repeats=2 --new
--filter-tcp=443 --ipset=/opt/zapret/lists/ipset-discord.txt --dpi-desync=syndata --dpi-desync-fake-syndata=/opt/zapret/bin/tls_clienthello_3.bin --dpi-desync-autottl --new
--filter-udp=443 --hostlist=/opt/zapret/lists/discord.txt --dpi-desync=fake,udplen --dpi-desync-udplen-increment=5 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=/opt/zapret/bin/quic_2.bin --dpi-desync-repeats=7 --dpi-desync-cutoff=n2 --new
--filter-udp=50000-50090 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=n3 --new
--filter-tcp=443 --hostlist-domains=googlevideo.com --dpi-desync=multidisorder --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1,host+2,sld+2,sld+5,sniext+1,sniext+2,endhost-2 --new
--filter-tcp=6695-6705 --dpi-desync=fake,split2 --dpi-desync-repeats=8 --dpi-desync-fooling=md5sig --dpi-desync-autottl=2 --dpi-desync-fake-tls=/opt/zapret/bin/tls_clienthello_www_google_com.bin --new
--filter-tcp=443 --hostlist-exclude=/opt/zapret/lists/netrogat.txt --dpi-desync=fakedsplit --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-autottl --new"""

        # Записываем новую конфигурацию с sudo правами
        try:
            # Создаем временный файл
            temp_path = "/tmp/config.tmp"
            with open(temp_path, 'w') as f:
                f.write(config_content)

            # Копируем с sudo правами
            subprocess.run(['sudo', 'cp', temp_path, config_path], check=True)
            subprocess.run(['sudo', 'chmod', '644', config_path], check=True)

            messagebox.showinfo("Успех", f"Стратегия успешно применена. Перезапустите службу для применения изменений.")
            self.restart_service()
            self.update_strategy_display()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось применить конфигурацию: {str(e)}")
        finally:
            # Удаляем временный файл
            if os.path.exists(temp_path):
                os.remove(temp_path)


# ===========================================================
# ===========================================================
# ===========================================================


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


        # Вкладка "Стратегия"
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

        note_text = """Стратегия для Ростел./Т2 работает с Мегафон, но без голосового в дисе.
Если нужно добавить свою стратегию, то выбрать 'Изменить config.txt'.
Обязательно после изменений перезапустите службу"""
        tk.Label(config_frame, text=note_text, justify=tk.LEFT, font=('Helvetica', 12)).pack(pady=(0, 5), padx=5, anchor=tk.W)

        # Сетка кнопок (2 колонки)
        buttons_frame = ttk.Frame(config_frame)
        buttons_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        buttons_frame.columnconfigure(0, weight=1, uniform='cols')
        buttons_frame.columnconfigure(1, weight=1, uniform='cols')

        # Динамические кнопки (сохраняем как атрибуты)
        ttk.Button(
            buttons_frame,
            text="Ростелеком/Теле2",
            command=self.config_rostelecom,
            style='TButton'
        ).grid(row=0, column=0, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="МТС",
            command=self.config_mts,
            style='TButton'
        ).grid(row=0, column=1, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="Общая стратегия",
            command=self.config_all,
            style='TButton'
        ).grid(row=1, column=1, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="Изменить config.txt",
            command=self.open_config,
            style='TButton'
        ).grid(row=1, column=0, padx=3, pady=3, sticky='nsew')

        ttk.Button(
            buttons_frame,
            text="Перезапустить службу",
            command=self.restart_service,
            style='TButton'
        ).grid(row=2, column=1, padx=3, pady=3, sticky='nsew')


        # Настройка строк
        for i in range(3):
            buttons_frame.rowconfigure(i, weight=0, minsize=30)

        # Обновляем состояние кнопок
        self.update_button_states()


        # Вкладка "Списки доменов"
        domains_frame = ttk.Frame(self.notebook)
        self.notebook.add(domains_frame, text="Списки доменов")

        note_text = """Примечание:
Не работает какой-то заблокированный сайт?
Попробуйте добавить его домен в autohosts.txt.
Если не работает незаблокированный сайт?
Добавьте его домен в ignore.txt."""

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


        # Настройка строк
        for i in range(3):
            buttons_frame.rowconfigure(i, weight=0, minsize=30)

        # Обновляем состояние кнопок
        self.update_button_states()


        # Вкладка "Дополнительно"
        extra_frame = ttk.Frame(self.notebook)
        self.notebook.add(extra_frame, text="Дополнительно")

        note_text = """"""

        tk.Label(extra_frame, text=note_text, justify=tk.LEFT).pack(pady=10, padx=10, anchor=tk.W)

        tk.Button(extra_frame, text="Обновить службу Zapret DPI и Manager",
                 command=self.update_zapret, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)
        tk.Button(extra_frame, text="Удалить службу Zapret DPI и Manager",
                 command=self.uninstall_zapret, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)

        # Сетка кнопок (2 колонки)
        buttons_frame = ttk.Frame(extra_frame)
        buttons_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        buttons_frame.columnconfigure(0, weight=1, uniform='cols')
        buttons_frame.columnconfigure(1, weight=1, uniform='cols')

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
