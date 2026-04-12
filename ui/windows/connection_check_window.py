#!/usr/bin/env python3

import tkinter as tk
from tkinter import scrolledtext
import threading
import subprocess
import time
import socket
import http.client
import urllib.parse
import ssl
from urllib.error import URLError
from ui.components.button_styler import create_hover_button
from core.dpi_utils import place_toplevel_centered_on_parent
import os

class ConnectionCheckWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.checking = False
        self.results = []
        self.zapret_status = None

    def run(self):
        """Запускает окно проверки соединения"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Проверка соединения")
        self.window.configure(bg='#182030')

        self.setup_ui()
        place_toplevel_centered_on_parent(
            self.window, self.parent, min_width=520, min_height=400, margin_width=8, margin_height=12
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
            text="Проверка сетевого соединения",
            font=("Arial", 16, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(pady=(0, 20))

        # Область вывода результатов
        results_frame = tk.Frame(main_frame, bg='#182030')
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

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
        self.results_text.pack(fill=tk.BOTH, expand=True)

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

        # Динамическая кнопка Запустить/Остановить
        self.toggle_button = create_hover_button(
            control_frame,
            text="Запустить проверку",
            command=self.toggle_check,
            **button_style
        )
        self.toggle_button.pack(side=tk.LEFT, padx=(0, 10))

        # Кнопка назад
        self.back_button = create_hover_button(
            control_frame,
            text="Назад",
            command=self.on_close,
            **button_style
        )
        self.back_button.pack(side=tk.RIGHT)

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
        self.results = []

        # Обновляем текст кнопки
        self.toggle_button.config(text="Остановить проверку", bg='#15354D')

        # Очищаем результаты перед началом проверки
        self.clear_results()

        # Все операции с GUI должны выполняться в главном потоке
        self.window.after(0, self._start_check_ui)

        # Запускаем проверку в отдельном потоке
        thread = threading.Thread(target=self.run_checks)
        thread.daemon = True
        thread.start()

    def _start_check_ui(self):
        """Обновляет UI в главном потоке"""
        self.log_message("=" * 60, "#0a84ff")
        self.log_message("НАЧАЛО ПРОВЕРКИ СОЕДИНЕНИЯ", "#0a84ff")
        self.log_message("=" * 60, "#0a84ff")
        self.log_message(f"Время начала: {time.strftime('%H:%M:%S')}")
        self.log_message("")

    def log_message(self, message, color='white'):
        """Добавляет сообщение в область вывода (безопасно для потоков)"""
        # Используем after для безопасного обновления GUI из другого потока
        self.window.after(0, self._log_message_thread_safe, message, color)

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
            self.checking = False
            self.log_message("\n[!] Проверка остановлена пользователем", "#ff9500")
            # Обновляем кнопку немедленно
            self.window.after(0, self._update_button_to_start)

    def _update_button_to_start(self):
        """Обновляет кнопку в состояние 'Запустить'"""
        self.toggle_button.config(text="Запустить проверку", bg='#15354D')

    def clear_results(self):
        """Очищает область результатов"""
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state='disabled')

    def run_checks(self):
        """Выполняет проверки соединения"""
        try:
            # Проверяем статус Zapret перед началом проверок
            self.zapret_status = self.check_zapret_status()

            # 1. Проверка локальной сети
            self.check_local_network()

            if not self.checking:
                return

            # 2. Проверка интернет-соединения
            self.check_internet()

            if not self.checking:
                return

            # 3. Проверка YouTube (специальные URL)
            self.check_youtube()

            if not self.checking:
                return

            # 4. Проверка Discord
            self.check_discord()

            if not self.checking:
                return

           # 5. Итоги
            self.show_summary()

        except Exception as e:
            self.log_message(f"\n[ОШИБКА] {str(e)}", "#ff3b30")
        finally:
            self.checking = False
            self.window.after(0, self.on_check_complete)

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
                text=True
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
                            text=True
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

    def check_internet(self):
        """Проверка интернет-соединения через curl"""
        self.log_message("🔍 ПРОВЕРКА ИНТЕРНЕТ-СОЕДИНЕНИЯ:", "#0a84ff")

        test_urls = [
            ("Google", "https://www.google.com"),
            ("Cloudflare", "https://1.1.1.1"),
            ("Yandex", "https://ya.ru"),
        ]

        for name, url in test_urls:
            if not self.checking:
                return

            try:
                start_time = time.time()

                # Используем curl для проверки
                result = subprocess.run(
                    ["curl", "-s", "-I", "--max-time", "5", url],
                    capture_output=True,
                    text=True,
                    timeout=7
                )

                response_time = (time.time() - start_time) * 1000

                if result.returncode == 0:
                    # Парсим статус код из вывода curl
                    for line in result.stdout.split('\n'):
                        if line.startswith('HTTP/'):
                            status_code = int(line.split()[1])
                            if status_code < 400:
                                self.log_message(f"  ✅ {name}: {status_code} ({response_time:.0f} мс)", "#30d158")
                                self.results.append(("Интернет", name, True))
                            else:
                                self.log_message(f"  ⚠️ {name}: код {status_code}", "#ff9500")
                                self.results.append(("Интернет", name, False))
                            break
                else:
                    self.log_message(f"  ❌ {name}: ошибка curl", "#ff3b30")
                    self.results.append(("Интернет", name, False))

            except subprocess.TimeoutExpired:
                self.log_message(f"  ⏱️ {name}: таймаут", "#ff9500")
                self.results.append(("Интернет", name, False))
            except Exception as e:
                self.log_message(f"  ❌ {name}: {str(e)}", "#ff3b30")
                self.results.append(("Интернет", name, False))

        self.log_message("")

    def check_discord(self):
        """Проверка доступности Discord"""
        self.log_message("🔍 ПРОВЕРКА ДОСТУПА К DISCORD:", "#0a84ff")

        discord_tests = [
            {
                "name": "Discord Website",
                "url": "discord.com",
                "path": "/",
                "method": "HEAD",
                "expected": [200, 301, 302]
            },
            {
                "name": "Discord API",
                "url": "discord.com",
                "path": "/api/v9/gateway",
                "method": "GET",
                "expected": [200, 400, 401]
            },
        ]

        discord_results = []  # Временный список для результатов Discord

        for test in discord_tests:
            if not self.checking:
                return

            try:
                start_time = time.time()

                # Создаем SSL контекст для HTTPS
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

                # Устанавливаем соединение
                conn = http.client.HTTPSConnection(test["url"], timeout=5, context=context)

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': '*/*'
                }

                conn.request(test["method"], test["path"], headers=headers)

                response = conn.getresponse()
                response_time = (time.time() - start_time) * 1000
                status_code = response.status

                # Проверяем статус
                if status_code in test["expected"] or (200 <= status_code < 300):
                    self.log_message(f"  ✅ {test['name']}: {status_code} ({response_time:.0f} мс)", "#30d158")
                    self.results.append(("Discord", test['name'], True))
                    discord_results.append(True)  # Добавляем в временный список

                else:
                    self.log_message(f"  ⚠️ {test['name']}: код {status_code}", "#ff9500")
                    self.results.append(("Discord", test['name'], False))
                    discord_results.append(False)  # Добавляем в временный список

                conn.close()

            except socket.timeout:
                self.log_message(f"  ⏱️ {test['name']}: таймаут", "#ff9500")
                self.results.append(("Discord", test['name'], False))
                discord_results.append(False)  # Добавляем в временный список
            except Exception as e:
                self.log_message(f"  ❌ {test['name']}: {str(e)}", "#ff3b30")
                self.results.append(("Discord", test['name'], False))
                discord_results.append(False)  # Добавляем в временный список

        self.log_message("")
        # Проверяем результаты Discord тестов
        if discord_results:  # Если есть результаты
            successful_tests = sum(1 for result in discord_results if result)
            total_tests = len(discord_results)

            self.log_message("=" * 40, "#0a84ff")
            self.log_message("🔍 АНАЛИЗ РЕЗУЛЬТАТОВ YOUTUBE:", "#0a84ff")
            self.log_message("=" * 40, "#0a84ff")

            if successful_tests == total_tests:  # Все тесты успешны
                self.log_message(f"✅ Discord разблокирован и должен работать!", "#30d158")
            elif successful_tests > 0:  # Частично успешно
                self.log_message(f"  ⚠️ Discord частично доступен ({successful_tests}/{total_tests} тестов)", "#ff9500")
            else:  # Все тесты провалены
                self.log_message(f"❌ Discord не работает! Попробуйте другую стратегию", "#ff3b30")
        else:
            self.log_message(f"ℹ️  Нет результатов проверки Discord", "#8e8e93")

        self.log_message("")

    def check_youtube(self):
        """Проверка YouTube через curl с реальными endpoint'ами"""
        self.log_message("🔍 ПРОВЕРКА ДОСТУПА К YOUTUBE И ВИДЕО:", "#0a84ff")

        youtube_tests = [
            {
                "name": "youtube.com",
                "url": "https://www.youtube.com/",
                "method": "HEAD"
            },
            {
                "name": "generate_204",
                "url": "https://rr2---sn-axq7sn7z.googlevideo.com/generate_204",
                "method": "HEAD"
            },
            {
                "name": "YouTube API",
                "url": "https://www.googleapis.com/youtube/v3/videos?id=dQw4w9WgXcQ&key=test",
                "method": "GET"
            },
            {
                "name": "YouTube Images",
                "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
                "method": "HEAD"
            }
        ]

        for test in youtube_tests:
            if not self.checking:
                return

            self.log_message(f"  Тест: {test['name']}", "#8e8e93")

            try:
                # Строим команду curl
                command = [
                    "curl",
                    "-I",  # Только заголовки
                    "--connect-timeout", "5",
                    "--max-time", "10",
                    "--silent",
                    "--show-error",
                    "--location"  # Следовать редиректам
                ]

                # Добавляем метод запроса
                if test["method"] == "HEAD":
                    command.extend(["-X", "HEAD"])
                # Для GET метод по умолчанию, ничего не добавляем

                # Добавляем User-Agent как у браузера
                command.extend(["-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"])

                # Добавляем URL
                command.append(test["url"])

                start_time = time.time()

                # Выполняем curl команду
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=12  # Немного больше чем --max-time
                )

                response_time = (time.time() - start_time) * 1000

                if result.returncode == 0:
                    # Успешный запрос, анализируем вывод
                    lines = result.stdout.strip().split('\n')
                    status_line = lines[0] if lines else ""

                    if "HTTP/" in status_line:
                        try:
                            status_code = int(status_line.split()[1])
                            status_str = str(status_code)

                            # Логика проверки для разных тестов
                            if test["name"] == "YouTube API":
                                if status_str in ['400', '403', '404']:
                                    self.log_message(f"    ✅ HTTP {status_code} ({response_time:.0f} мс) - ожидаемая ошибка ключа", "#30d158")
                                    self.results.append(("YouTube", test['name'], True))
                                elif status_str == '429':
                                    self.log_message(f"    🚫 HTTP {status_code} - лимит запросов", "#ff3b30")
                                    self.results.append(("YouTube", test['name'], False))
                                elif status_str == '200':
                                    self.log_message(f"    ⚠️ HTTP {status_code} - неожиданно для тестового ключа", "#ff9500")
                                    self.results.append(("YouTube", test['name'], True))
                                else:
                                    self.log_message(f"    ❓ HTTP {status_code} - неожиданный ответ", "#ff9500")
                                    self.results.append(("YouTube", test['name'], False))

                            else:  # youtube.com, YouTube Images и generate_204
                                if status_str in ['200', '204']:
                                    self.log_message(f"    ✅ HTTP {status_code} ({response_time:.0f} мс)", "#30d158")
                                    self.results.append(("YouTube", test['name'], True))
                                elif status_str == '404':
                                    self.log_message(f"    ⚠️ HTTP {status_code} - endpoint не найден", "#ff9500")
                                    self.results.append(("YouTube", test['name'], False))
                                elif status_str in ['403', '429']:
                                    self.log_message(f"    🚫 HTTP {status_code} - блокировка", "#ff3b30")
                                    self.results.append(("YouTube", test['name'], False))
                                elif status_str in ['301', '302', '307', '308']:
                                    self.log_message(f"    🔀 HTTP {status_code} - редирект", "#ff9500")
                                    self.results.append(("YouTube", test['name'], True))
                                else:
                                    self.log_message(f"    ❓ HTTP {status_code} - неожиданный ответ", "#ff9500")
                                    self.results.append(("YouTube", test['name'], False))

                        except (IndexError, ValueError) as e:
                            self.log_message(f"    ❌ Ошибка парсинга ответа: {str(e)}", "#ff3b30")
                            self.results.append(("YouTube", test['name'], False))
                    else:
                        self.log_message(f"    ❌ Нет HTTP заголовка в ответе", "#ff3b30")
                        self.results.append(("YouTube", test['name'], False))

                else:
                    # Ошибка curl, анализируем stderr
                    error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
                    error_lower = error_output.lower()

                    if "could not resolve host" in error_lower:
                        self.log_message(f"    ❌ DNS блокировка - не удалось разрешить хост", "#ff3b30")
                    elif "connection timed out" in error_lower:
                        self.log_message(f"    ❌ Таймаут соединения - возможная DPI блокировка", "#ff3b30")
                    elif "connection refused" in error_lower:
                        self.log_message(f"    ❌ Соединение отклонено - блокировка", "#ff3b30")
                    elif "ssl handshake" in error_lower or "tls" in error_lower:
                        self.log_message(f"    🔐 SSL handshake ошибка - вероятная DPI блокировка", "#ff3b30")
                    elif "operation timed out" in error_lower:
                        self.log_message(f"    ⏱️ Общий таймаут запроса", "#ff9500")
                    else:
                        # Берем первую строку ошибки
                        error_first_line = error_output.split('\n')[0] if error_output else "Неизвестная ошибка"
                        self.log_message(f"    ❌ Ошибка curl: {error_first_line[:80]}", "#ff3b30")

                    self.results.append(("YouTube", test['name'], False))

            except subprocess.TimeoutExpired:
                self.log_message(f"    ⏱️ Таймаут выполнения команды (>12 сек)", "#ff9500")
                self.results.append(("YouTube", test['name'], False))
            except Exception as e:
                self.log_message(f"    ❌ Системная ошибка: {str(e)[:80]}", "#ff3b30")
                self.results.append(("YouTube", test['name'], False))

        self.log_message("")

        # Интерпретируем результаты
        self.interpret_youtube_results()

    def _check_ssl_handshake_issues(self):
        """Проверяет наличие SSL handshake проблем в результатах"""
        ssl_errors = []

        # Собираем все сообщения об ошибках из results_text
        text_content = self.results_text.get("1.0", tk.END)

        # Ищем SSL ошибки
        ssl_keywords = [
            "SSL ошибка",
            "SSLError",
            "handshake",
            "SSL handshake",
            "TLS",
            "certificate",
            "CERT",
            "ssl.CERT"
        ]

        youtube_keywords = [
            "googlevideo",
            "youtube",
            "ytimg"
        ]

        lines = text_content.split('\n')
        for line in lines:
            line_lower = line.lower()
            # Проверяем, есть ли в строке SSL ошибка И связана ли она с YouTube
            if any(keyword.lower() in line_lower for keyword in ssl_keywords):
                if any(keyword in line for keyword in youtube_keywords):
                    ssl_errors.append(line.strip())

        return len(ssl_errors) > 0

    def interpret_youtube_results(self):
        """Интерпретирует результаты YouTube тестов"""
        self.log_message("=" * 40, "#0a84ff")
        self.log_message("🔍 АНАЛИЗ РЕЗУЛЬТАТОВ YOUTUBE:", "#0a84ff")
        self.log_message("=" * 40, "#0a84ff")

        # Проверяем наличие SSL handshake проблем
        ssl_problems = self._check_ssl_handshake_issues()

        # Считаем результаты YouTube тестов
        youtube_results = [r for r in self.results if r[0] == "YouTube"]
        total_youtube = len(youtube_results)
        successful_youtube = sum(1 for r in youtube_results if r[2])

        # Проверяем конкретные тесты
        has_generate_204 = any(r[1] == "generate_204" and r[2] for r in youtube_results)
        has_youtube_main = any(r[1] == "youtube.com" and r[2] for r in youtube_results)
        has_images = any(r[1] == "YouTube Images" and r[2] for r in youtube_results)

        if ssl_problems:
            self.log_message("🚨 ОБНАРУЖЕНА ВОЗМОЖНАЯ DPI БЛОКИРОВКА!", "#ff3b30")
            self.log_message("")
            self.log_message("❌ Признаки блокировки:", "#ff3b30")
            self.log_message("   • SSL handshake ошибки на YouTube доменах", "#ff3b30")
            self.log_message("   • TCP соединение может работать, но HTTPS блокируется", "#ff3b30")
            self.log_message("   • DPI система может быть активна", "#ff3b30")
            self.log_message("")
            self.log_message("🛠️ РЕКОМЕНДАЦИИ:", "#ff9500")
            self.log_message("   1. Проверьте запущена ли служба Zapret", "#ff3b30")
            self.log_message("   2. Выберите другую стратегию обхода", "#ff3b30")
            self.log_message("   3. Убедитесь в наличии интернет-соединения", "#ff3b30")
            self.log_message("   4. Попробуйте включить DNS", "#ff3b30")
            self.log_message("")

        elif successful_youtube == total_youtube and total_youtube > 0:
            self.log_message("✅ YouTube разблокирован и должен работать!", "#30d158")
            self.log_message("")
            # self.log_message("🔑 Ключевые индикаторы успеха:", "#30d158")
            # if has_generate_204:
            #     self.log_message("   • HTTP 204 на /generate_204 - идеальный ответ", "#30d158")
            # if has_images:
            #     self.log_message("   • HTTP 200 на thumbnail сервер - изображения загружаются", "#30d158")
            # if has_youtube_main:
            #     self.log_message("   • Доступность youtube.com - основной сайт работает", "#30d158")
            # self.log_message("   • SSL handshake успешен - нет DPI блокировки", "#30d158")
            # self.log_message("   • DNS разрешается - нет DNS блокировки", "#30d158")

        elif successful_youtube == total_youtube:
            self.log_message("⚠️ ЧАСТИЧНАЯ ДОСТУПНОСТЬ YOUTUBE", "#ff9500")
            self.log_message("")
            self.log_message("🔍 Возможные проблемы:", "#ff9500")
            if not has_generate_204:
                self.log_message(
                    "   • Проблемы с видео-серверами Google. Скорее всего сам сайт youtube грузится, но могут наблюдаться тормоза",
                    "#ff9500",
                )
            if not has_youtube_main:
                self.log_message(
                    "   • Основной сайт YouTube недоступен. Попробуйте включить DNS Google",
                    "#ff9500",
                )
            if not has_images:
                self.log_message("   • Проблемы с загрузкой изображений", "#ff9500")

        else:
            self.log_message("❌ YOUTUBE НЕ ДОСТУПЕН", "#ff3b30")
            self.log_message("")
            self.log_message("🛠️ НЕОБХОДИМЫ ДЕЙСТВИЯ:", "#ff3b30")
            self.log_message("   1. Проверьте запущена ли служба Zapret", "#ff3b30")
            self.log_message("   2. Выберите другую стратегию обхода", "#ff3b30")
            self.log_message("   3. Убедитесь в наличии интернет-соединения", "#ff3b30")
            self.log_message("   4. Попробуйте включить DNS", "#ff3b30")

        self.log_message("")
        # self.log_message("📋 Справочная информация:", "#8e8e93")
        # self.log_message("   • HTTP 404 на API - нормально (без ключа)", "#8e8e93")
        # self.log_message("   • Ping успешный = сетевая связность OK", "#8e8e93")
        # self.log_message("   • Порт 443 открыт = TCP соединение OK", "#8e8e93")
        # self.log_message("   • SSL handshake = критичен для HTTPS", "#8e8e93")
        # self.log_message("=" * 40, "#0a84ff")

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

        total_success = sum(1 for _, _, success in self.results if success)
        total_tests = len(self.results)

    def on_close(self):
        """Закрывает окно"""
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
