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
        self.root.geometry("580x410")
        self.version = "1.3"

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

    def show_status_window(self):
        self.status_window = tk.Toplevel(self.root)
        self.status_window.title("Статус Zapret DPI")
        self.status_window.geometry("680x350")
        self.status_window.resizable(False, False)

        tk.Label(self.status_window, text="В Loaded после zapret.service указывается автозапуск службы\ndisabled - автозапуск службы запущен\nenabled - автозапуск службы запущен\nВ строке Active указывается запущена служба или нет\nactive (exited) - процесс службы завершился (не работает в фоне), но сама служба\nсчитается 'активной',\ninactive (dead) - служба не запущена", font=('Helvetica', 12)).pack(pady=5)

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

    def create_main_menu(self):
        # Очищаем предыдущие виджеты
        for widget in self.root.winfo_children():
            widget.destroy()

        # Создаем Notebook (вкладки)
        self.notebook = ttk.Notebook(self.root)
        self.style.configure('TNotebook.Tab', font=('Helvetica', 15))
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка "Управление службами"
        service_frame = ttk.Frame(self.notebook)
        self.notebook.add(service_frame, text="Управление службой")

        note_text = """Примечание: По умолчанию автозапуск службы включен."""

        tk.Label(service_frame, text=note_text, justify=tk.LEFT, font=('Helvetica', 12)).pack(pady=10, padx=10, anchor=tk.W)

        tk.Button(service_frame, text="Проверка статуса службы",
                command=self.check_status, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)

        tk.Button(service_frame, text="Перезапустить службу",
                command=self.restart_service, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)

       # Создаем фреймы для кнопок
        service_buttons_frame = ttk.Frame(service_frame)
        service_buttons_frame.pack(pady=5, fill=tk.X, padx=10)

        autorun_buttons_frame = ttk.Frame(service_frame)
        autorun_buttons_frame.pack(pady=5, fill=tk.X, padx=10)

        # Динамические кнопки управления службой
        if self.is_service_active():
            self.stop_button = tk.Button(service_buttons_frame, text="Остановить службу", command=self.stop_service, font=('Helvetica', 13))
            self.stop_button.pack(pady=5, fill=tk.X)
        else:
            self.start_button = tk.Button(service_buttons_frame, text="Запустить службу", command=self.start_service, font=('Helvetica', 13))
            self.start_button.pack(pady=5, fill=tk.X)

        # Динамические кнопки автозапуска
        if self.is_service_enabled():
            self.disable_autorun_button = tk.Button(autorun_buttons_frame, text="Отсключить автозапуск службы", command=self.disable_autorun,  font=('Helvetica', 13))
            self.disable_autorun_button.pack(pady=5, fill=tk.X)
        else:
            self.enable_autorun_button = tk.Button(autorun_buttons_frame, text="Включить автозапуск службы",command=self.enable_autorun, font=('Helvetica', 13))
            self.enable_autorun_button.pack(pady=5, fill=tk.X)

        tk.Button(service_frame, text="Выход",
                command=self.root.destroy, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)

        # Вкладка "Списки доменов"
        domains_frame = ttk.Frame(self.notebook)
        self.notebook.add(domains_frame, text="Списки доменов")

        note_text = """Примечание:
Не работает какой-то заблокированный сайт?
Попробуйте добавить его домен в autohosts.txt.
Если не работает незаблокированный сайт?
Добавьте его домен в ignore.txt.
Для внесения изменения в config выбрать'Изменить config.txt
(для опытных пользователей) После измененеия требуется перезапуск службы)"""

        tk.Label(domains_frame, text=note_text, justify=tk.LEFT, font=('Helvetica', 10)).pack(pady=10, padx=10, anchor=tk.W)

        tk.Button(domains_frame, text="Добавить в autohosts.txt",
                 command=self.open_autohosts, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)
        tk.Button(domains_frame, text="Добавить в ignore.txt",
                 command=self.open_ignore, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)
        tk.Button(domains_frame, text="Изменить config.txt",
                 command=self.open_config, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)


        # Вкладка "Дополнительно"
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="Дополнительно")

        note_text = """"""

        tk.Label(main_frame, text=note_text, justify=tk.LEFT).pack(pady=10, padx=10, anchor=tk.W)

        tk.Button(main_frame, text="Обновить Zapret DPI Manager и службы",
                 command=self.update_zapret, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)
        tk.Button(main_frame, text="Удалить Zapret DPI",
                 command=self.uninstall_zapret, font=('Helvetica', 13)).pack(pady=10, fill=tk.X, padx=10)

        # Добавляем версию в нижнюю часть окна
        version_frame = ttk.Frame(self.root)
        version_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
    
        # Укажите вашу текущую версию здесь
        version_label = ttk.Label(version_frame, text=f"Zapret DPI Manager v.{self.version}", font=('Helvetica', 10))
        version_label.pack(side=tk.RIGHT, padx=10)
        
        self.root.deiconify()

    def check_status(self):
        self.show_status_window()

    def update_zapret(self):
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Переустановка Zapret DPI")
        progress_window.geometry("350x100")
        progress_window.resizable(False, False)

        tk.Label(progress_window, text="Идет переустановка Zapret DPI...", font=('Helvetica', 13)).pack(pady=10)

        progress = ttk.Progressbar(progress_window, mode='indeterminate')
        progress.pack(pady=5)
        progress.start()

        def run_update():

            try:
                # Проверяем и устанавливаем зависимости
                if not self.install_dependencies():
                    raise RuntimeError("Не удалось установить зависимости")

                # Удаляем старую версию Zapret

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
                if not self.install_zapret_dpi_manager():
                    raise RuntimeError("Не удалось скачать Zapret DPI Manager")

                # Устанавливаем Zapret
                if not self.install_zapret_dpi():
                    raise RuntimeError("Не удалось скачать службу Zapret DPI")                   

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


if __name__ == "__main__":
    root = tk.Tk()
    app = ZapretGUI(root)
    root.mainloop()
