#!/usr/bin/env python3
import asyncio
import subprocess
import json
import time
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import re

class StrategyTester:
    """
    Класс для автоматического тестирования различных стратегий обхода блокировок
    """

    def __init__(self, project_root: str, sudo_password: Optional[str] = None):
        """
        Инициализация тестировщика

        :param project_root: Путь к корню проекта (/home/deck/Zapret_DPI_Manager)
        :param sudo_password: Пароль sudo
        """
        self.project_root = Path(project_root)
        self.sudo_password = sudo_password
        self.config_path = self.project_root / "config.txt"
        self.stop_requested = False

        # Пути к файлам
        self.files_dir = self.project_root / "files"
        self.lists_dir = self.files_dir / "lists"
        self.strategies_dir = self.files_dir / "strategy"
        self.utils_dir = self.project_root / "utils"
        self.reports_dir = self.utils_dir / "reports"

        # Создаем необходимые директории
        self.reports_dir.mkdir(exist_ok=True)

        # Результаты тестирования
        self.results = []

    def stop_testing(self):
        """
        Устанавливает флаг остановки тестирования
        """
        self.stop_requested = True
        print("⚠️  Получен запрос на остановку тестирования...")

    def _run_command(self, command: str, use_sudo: bool = False, timeout: int = 10) -> Tuple[bool, str]:
        """
        Выполняет команду с опциональным sudo
        """
        try:
            if use_sudo and self.sudo_password:
                full_cmd = f"echo '{self.sudo_password}' | sudo -S {command}"
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

    def _load_targets(self, mode: str = "standard") -> List[Dict]:
        """
        Загружает цели для тестирования
        """
        targets = []

        if mode == "dpi":
            # DPI-цели
            dpi_targets = [
                {"name": "US.Cloudflare.1", "url": "https://cdn.cookielaw.org/scripttemplates/202501.2.0/otBannerSdk.js", "ping_only": False},
                {"name": "US.Cloudflare.2", "url": "https://genshin.jmp.blue/characters/all#", "ping_only": False},
                {"name": "US.Cloudflare.3", "url": "https://api.frankfurter.dev/v1/2000-01-01..2002-12-31", "ping_only": False},
                {"name": "US.DigitalOcean", "url": "https://genderize.io/", "ping_only": False},
                {"name": "DE.Hetzner.1", "url": "https://j.dejure.org/jcg/doctrine/doctrine_banner.webp", "ping_only": False},
                {"name": "FI.Hetzner.2", "url": "https://tcp1620-01.dubybot.live/1MB.bin", "ping_only": False},
                {"name": "FI.Hetzner.3", "url": "https://tcp1620-02.dubybot.live/1MB.bin", "ping_only": False},
                {"name": "FI.Hetzner.4", "url": "https://tcp1620-05.dubybot.live/1MB.bin", "ping_only": False},
                {"name": "FI.Hetzner.5", "url": "https://tcp1620-06.dubybot.live/1MB.bin", "ping_only": False},
                {"name": "FR.OVH.1", "url": "https://eu.api.ovh.com/console/rapidoc-min.js", "ping_only": False},
                {"name": "FR.OVH.2", "url": "https://ovh.sfx.ovh/10M.bin", "ping_only": False},
                {"name": "SE.Oracle", "url": "https://oracle.sfx.ovh/10M.bin", "ping_only": False},
                {"name": "DE.AWS.1", "url": "https://tms.delta.com/delta/dl_anderson/Bootstrap.js", "ping_only": False},
                {"name": "US.AWS.2", "url": "https://corp.kaltura.com/wp-content/cache/min/1/wp-content/themes/airfleet/dist/styles/theme.css", "ping_only": False},
                {"name": "US.GoogleCloud", "url": "https://api.usercentrics.eu/gvl/v3/en.json", "ping_only": False},
                {"name": "US.Fastly.1", "url": "https://openoffice.apache.org/images/blog/rejected.png", "ping_only": False},
                {"name": "US.Fastly.2", "url": "https://www.juniper.net/etc.clientlibs/juniper/clientlibs/clientlib-site/resources/fonts/lato/Lato-Regular.woff2", "ping_only": False},
                {"name": "PL.Akamai.1", "url": "https://www.lg.com/lg5-common-gp/library/jquery.min.js", "ping_only": False},
                {"name": "PL.Akamai.2", "url": "https://media-assets.stryker.com/is/image/stryker/gateway_1?$max_width_1410$", "ping_only": False},
                {"name": "US.CDN77", "url": "https://cdn.eso.org/images/banner1920/eso2520a.jpg", "ping_only": False},
                {"name": "DE.Contabo", "url": "https://cloudlets.io/wp-content/themes/Avada/includes/lib/assets/fonts/fontawesome/webfonts/fa-solid-900.woff2", "ping_only": False},
                {"name": "FR.Scaleway", "url": "https://renklisigorta.com.tr/teklif-al", "ping_only": False},
                {"name": "US.Constant", "url": "https://cdn.xuansiwei.com/common/lib/font-awesome/4.7.0/fontawesome-webfont.woff2?v=4.7.0", "ping_only": False},
            ]
            return dpi_targets

        elif mode == "YouTube/Discord":
            # Режим только YouTube/Discord
            return self._load_youtube_discord_targets()

        else:
            # Стандартные цели из test_targets.txt
            return self._load_standard_targets()

    def _load_youtube_discord_targets(self) -> List[Dict]:
        """Загружает только цели связанные с YouTube и Discord"""
        targets = []
        targets_file = self.utils_dir / "test_targets.txt"

        if not targets_file.exists():
            return [
                {"name": "YouTubeWeb", "url": "https://www.youtube.com", "ping_target": "www.youtube.com", "ping_only": False},
                {"name": "DiscordMain", "url": "https://discord.com", "ping_target": "discord.com", "ping_only": False}
            ]

        with open(targets_file, 'r', encoding='utf-8') as f:
            current_section = None

            for line in f:
                line = line.strip()

                # Определяем секцию
                if line.startswith('###'):
                    current_section = line.replace('###', '').strip().lower()
                    continue

                # Пропускаем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue

                # Парсим строки вида: Name = "value"
                match = re.match(r'^\s*([A-Za-z0-9_]+)\s*=\s*"(.+)"\s*$', line)
                if match:
                    name = match.group(1)
                    value = match.group(2)

                    # Проверяем, относится ли цель к секциям YouTube или Discord
                    should_include = False

                    # Проверка по секции
                    if current_section and ('youtube' in current_section or 'discord' in current_section):
                        should_include = True

                    # Проверка по имени (дополнительная безопасность)
                    name_lower = name.lower()
                    if 'youtube' in name_lower or 'discord' in name_lower:
                        should_include = True

                    # Проверка по URL значению
                    value_lower = value.lower()
                    if 'youtube' in value_lower or 'youtu.be' in value_lower or 'youtube.com' in value_lower:
                        should_include = True
                    elif 'discord' in value_lower or 'discordapp.com' in value_lower:
                        should_include = True

                    # Также включаем generate_204 (хотя он не содержит youtube в названии, но связан с YouTube)
                    if name.lower() == 'generate_204':
                        should_include = True

                    if should_include:
                        if value.upper().startswith('PING:'):
                            ping_target = value[5:].strip()
                            targets.append({
                                "name": name,
                                "ping_target": ping_target,
                                "ping_only": True
                            })
                        else:
                            try:
                                from urllib.parse import urlparse
                                parsed = urlparse(value)
                                ping_target = parsed.hostname or value
                            except:
                                ping_target = value

                            targets.append({
                                "name": name,
                                "url": value,
                                "ping_target": ping_target,
                                "ping_only": False
                            })

        # Сортируем: сначала YouTube цели, потом Discord
        youtube_targets = []
        discord_targets = []

        for target in targets:
            name_lower = target['name'].lower()
            if 'youtube' in name_lower:
                youtube_targets.append(target)
            elif 'discord' in name_lower:
                discord_targets.append(target)
            else:
                # Для целей без явного указания в имени (например, generate_204)
                # смотрим по URL или добавляем в начало
                if 'youtube' in target.get('url', '').lower():
                    youtube_targets.append(target)
                elif 'discord' in target.get('url', '').lower():
                    discord_targets.append(target)
                else:
                    # generate_204 добавляем к YouTube целям
                    youtube_targets.append(target)

        sorted_targets = youtube_targets + discord_targets

        if not sorted_targets:
            sorted_targets = [
                {"name": "YouTubeWeb", "url": "https://www.youtube.com", "ping_target": "www.youtube.com", "ping_only": False},
                {"name": "DiscordMain", "url": "https://discord.com", "ping_target": "discord.com", "ping_only": False}
            ]

        print(f"  Загружено YouTube целей: {len(youtube_targets)}, Discord целей: {len(discord_targets)}")

        return sorted_targets

    async def _rutracker_test(self, target: Dict, result: Dict) -> Dict:
        """Специальный тест для Rutracker с проверкой заголовка Connection и 3 попытками"""
        url = target["url"]

        # Для Rutracker используем форумный URL для проверки
        if "rutracker.org" in url and "/forum/index.php" not in url:
            test_url = "http://rutracker.org/forum/index.php"
        else:
            test_url = url

        result.update({
            "protocol": "HTTP",
            "success": False,
            "blocked": False,
            "details": "",
            "attempts": []
        })

        # Параметры curl для получения заголовков
        curl_cmd = [
            'curl', '-k', '-I', '-s', '-m', '1',
            '-L',  # Следуем редиректам
            '-o', '/dev/null',
            '-w', '%{http_code}::%{time_total}'
        ]

        # Выполняем 3 попытки
        attempts_results = []

        for attempt in range(1, 4):
            try:
                # Создаем команду для этой попытки
                attempt_cmd = curl_cmd.copy()
                attempt_cmd.append(test_url)

                # Запускаем процесс curl для получения заголовков
                proc = await asyncio.create_subprocess_exec(
                    *attempt_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await proc.communicate()
                output = stdout.decode('utf-8', errors='ignore')

                # Также получаем полные заголовки для анализа Connection
                headers_cmd = ['curl', '-k', '-I', '-s', '-m', '1', '-L', test_url]
                proc_headers = await asyncio.create_subprocess_exec(
                    *headers_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout_headers, _ = await proc_headers.communicate()
                headers_text = stdout_headers.decode('utf-8', errors='ignore')

                # Анализируем результат попытки
                attempt_result = {
                    "attempt": attempt,
                    "success": False,
                    "http_code": None,
                    "time_taken": None,
                    "connection": "не определен",
                    "raw_headers": headers_text[:200]
                }

                if proc.returncode == 0 and '::' in output:
                    http_code, time_taken = output.split('::')
                    attempt_result["http_code"] = http_code
                    attempt_result["time_taken"] = time_taken

                    # Ищем заголовок Connection
                    connection_found = False
                    for line in headers_text.split('\n'):
                        if line.lower().startswith('connection:'):
                            connection_value = line.split(':', 1)[1].strip().lower()
                            attempt_result["connection"] = connection_value
                            connection_found = True

                            if connection_value == 'keep-alive':
                                attempt_result["success"] = True
                            else:
                                # Любое другое значение Connection (close или что-то еще)
                                attempt_result["success"] = False
                            break

                    # Если заголовок Connection не найден, ищем keep-alive в других заголовках
                    if not connection_found:
                        # Ищем keep-alive в любом месте заголовков
                        if "keep-alive" in headers_text.lower() or "keepalive" in headers_text.lower():
                            attempt_result["success"] = True
                            attempt_result["connection"] = "keep-alive (обнаружено в заголовках)"
                        else:
                            # Нет keep-alive нигде
                            attempt_result["connection"] = "нет keep-alive"
                            attempt_result["success"] = False

                attempts_results.append(attempt_result)

                # Если удачная попытка (keep-alive найден), прерываем дальнейшие проверки
                if attempt_result["success"]:
                    break

                # Добавляем минимальную задержку между попытками (0.3 секунды)
                if attempt < 3:
                    await asyncio.sleep(0.3)

            except Exception as e:
                attempts_results.append({
                    "attempt": attempt,
                    "success": False,
                    "error": str(e)[:80]
                })

                # Задержка после ошибки (0.2 секунды)
                if attempt < 3:
                    await asyncio.sleep(0.2)

        # Сохраняем все попытки в результат
        result["attempts"] = attempts_results

        # ПРОСТАЯ ЛОГИКА: есть keep-alive = успех, нет keep-alive = блокировка
        successful_attempts = sum(1 for a in attempts_results if a.get("success", False))

        if successful_attempts > 0:
            # ХОТЯ БЫ ОДНА УСПЕШНАЯ ПОПЫТКА С KEEP-ALIVE
            result["success"] = True
            result["blocked"] = False

            # Используем данные из первой успешной попытки
            successful_attempt = next((a for a in attempts_results if a.get("success", False)), None)
            if successful_attempt:
                time_display = successful_attempt['time_taken'] if successful_attempt['time_taken'] else 'N/A'
                result["details"] = f"HTTP: код {successful_attempt['http_code']}, " \
                                f"Connection: {successful_attempt['connection']}, " \
                                f"время {time_display}с"
        else:
            # НИ ОДНОЙ УСПЕШНОЙ ПОПЫТКИ С KEEP-ALIVE = БЛОКИРОВКА
            result["success"] = False
            result["blocked"] = True

            # Используем данные из первой попытки для деталей
            if attempts_results and attempts_results[0]:
                first_attempt = attempts_results[0]
                http_code = first_attempt.get('http_code', 'N/A')
                connection = first_attempt.get('connection', 'нет данных')

                result["details"] = f"HTTP: код {http_code}, " \
                                f"Connection: {connection} (блокировка РКН)"
            else:
                result["details"] = "HTTP: все попытки завершились ошибкой (блокировка РКН)"

        return result

    def _load_standard_targets(self) -> List[Dict]:
        """Загружает все стандартные цели"""
        targets = []
        targets_file = self.utils_dir / "test_targets.txt"

        if not targets_file.exists():
            return [
                {"name": "YouTube", "url": "https://www.youtube.com", "ping_target": "www.youtube.com", "ping_only": False},
                {"name": "Discord", "url": "https://discord.com", "ping_target": "discord.com", "ping_only": False}
            ]

        # Парсим все цели
        with open(targets_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                match = re.match(r'^\s*([A-Za-z0-9_]+)\s*=\s*"(.+)"\s*$', line)
                if match:
                    name = match.group(1)
                    value = match.group(2)

                    if value.upper().startswith('PING:'):
                        ping_target = value[5:].strip()
                        targets.append({
                            "name": name,
                            "ping_target": ping_target,
                            "ping_only": True
                        })
                    else:
                        try:
                            from urllib.parse import urlparse
                            parsed = urlparse(value)
                            ping_target = parsed.hostname or value
                        except:
                            ping_target = value

                        targets.append({
                            "name": name,
                            "url": value,
                            "ping_target": ping_target,
                            "ping_only": False
                        })

        return targets

    def _prepare_strategy_config(self, strategy_name: str) -> Optional[Path]:
        """
        Подготавливает конфигурационный файл для конкретной стратегии

        :param strategy_name: Имя стратегии (без расширения)
        :return: Путь к временному конфигу или None при ошибке
        """
        try:
            # Ищем файл стратегии без расширения
            strategy_file = self.strategies_dir / strategy_name

            if not strategy_file.exists():
                # Попробуем найти с любым расширением
                matching_files = list(self.strategies_dir.glob(strategy_name + ".*"))
                if not matching_files:
                    print(f"  Файл стратегии не найден: {strategy_file}")
                    return None
                strategy_file = matching_files[0]

            # Читаем настройки стратегии
            with open(strategy_file, 'r', encoding='utf-8') as f:
                strategy_content = f.read()

            # Создаем временный конфиг
            temp_dir = Path(tempfile.gettempdir())
            temp_config = temp_dir / f"zapret_test_{strategy_name}_{int(time.time())}.txt"

            with open(temp_config, 'w', encoding='utf-8') as f:
                f.write(strategy_content)

            return temp_config

        except Exception as e:
            print(f"  Ошибка подготовки конфига: {e}")
            return None

    def _cleanup_ipset_for_dpi(self) -> bool:
        """
        Очищает ipset файлы для DPI-тестирования
        """
        try:
            ipset_file = self.lists_dir / "ipset-all.txt"
            if not ipset_file.exists():
                print(f"  Файл ipset-all.txt не найден: {ipset_file}")
                return False

            # Создаем бэкап
            backup_file = ipset_file.with_suffix('.test-backup.txt')
            shutil.copy2(ipset_file, backup_file)

            # Очищаем файл (оставляем комментарий)
            with open(ipset_file, 'w', encoding='utf-8') as f:
                f.write("# Очищено для DPI-теста\n# Все IP временно удалены\n")

            print(f"  Очищен ipset-all.txt, создан бэкап: {backup_file}")
            return True

        except Exception as e:
            print(f"  Ошибка очистки ipset: {e}")
            return False

    def _restore_ipset(self) -> bool:
        """
        Восстанавливает оригинальные ipset файлы
        """
        try:
            ipset_file = self.lists_dir / "ipset-all.txt"
            backup_file = ipset_file.with_suffix('.test-backup.txt')

            if backup_file.exists():
                shutil.copy2(backup_file, ipset_file)
                backup_file.unlink()
                print(f"  Восстановлен ipset-all.txt из бэкапа")
                return True
            else:
                print(f"  Бэкап не найден: {backup_file}")
                return False

        except Exception as e:
            print(f"  Ошибка восстановления ipset: {e}")
            return False

    async def _test_single_target(self, target: Dict) -> Dict:
        """
        Тестирует одну цель
        """
        result = {
            "target_name": target["name"],
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "blocked": False,
            "details": "",
            "protocol": "N/A"
        }

        if target.get("ping_only", False):
            # Ping-тест
            return await self._ping_test(target, result)
        else:
            # Проверяем специальные цели
            target_name_lower = target["name"].lower()

            if "rutracker" in target_name_lower:
                # Специальный тест для Rutracker
                return await self._rutracker_test(target, result)
            elif "decky" in target_name_lower:
                # JSON-тест для Decky loader
                return await self._json_test(target, result)
            else:
                # HTTP/HTTPS тест для остальных
                return await self._curl_test(target, result)


    async def _ping_test(self, target: Dict, result: Dict) -> Dict:
        """Выполняет ping тест"""
        host = target["ping_target"]

        try:
            # Запускаем ping с таймаутом 3 секунды
            proc = await asyncio.create_subprocess_exec(
                'ping', '-c', '2', '-W', '3', host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()
            output = stdout.decode('utf-8', errors='ignore')

            if proc.returncode == 0:
                # Извлекаем время
                time_match = re.search(r'time=([\d.]+)\s*ms', output)
                if time_match:
                    ping_time = time_match.group(1)
                    result["details"] = f"Ping: {ping_time} ms"
                else:
                    result["details"] = "Ping: успешно"
                result["success"] = True
            else:
                result["details"] = "Ping: неудачно"
                result["success"] = False

        except Exception as e:
            result["details"] = f"Ping ошибка: {str(e)}"
            result["success"] = False

        return result

    async def _json_test(self, target: Dict, result: Dict) -> Dict:
        """Выполняет проверку JSON API"""
        url = target["url"]

        # Тестируем разные протоколы
        protocols = [
            ("HTTP", ["--http1.1"]),
            ("TLS1.2", ["--tlsv1.2", "--tls-max", "1.2"]),
            ("TLS1.3", ["--tlsv1.3", "--tls-max", "1.3"])
        ]

        for proto_name, proto_args in protocols:
            test_result = await self._json_request(url, proto_name, proto_args)

            if test_result["success"]:
                result.update(test_result)
                return result
            elif test_result["blocked"]:
                result.update(test_result)
                return result

        # Если все протоколы не сработали
        result["details"] = "Все протоколы не сработали"
        return result

    async def _curl_test(self, target: Dict, result: Dict) -> Dict:
        """Выполняет HTTP тест через curl"""
        url = target["url"]

        # Тестируем разные протоколы
        protocols = [
            ("HTTP", ["--http1.1"]),
            ("TLS1.2", ["--tlsv1.2", "--tls-max", "1.2"]),
            ("TLS1.3", ["--tlsv1.3", "--tls-max", "1.3"])
        ]

        for proto_name, proto_args in protocols:
            test_result = await self._curl_request(url, proto_name, proto_args)

            if test_result["success"]:
                result.update(test_result)
                return result
            elif test_result["blocked"]:
                result.update(test_result)
                return result

        # Если все протоколы не сработали
        result["details"] = "Все протоколы не сработали"
        return result

    def _is_special_target(self, target_name: str, http_code: str) -> Tuple[bool, str]:
        """
        Проверяет, является ли цель специальной с ожидаемым HTTP кодом

        Возвращает: (является_ли_специальной, пояснение)
        """
        special_targets = {
            'generate_204': ('204', 'ожидаемый код 204 для generate_204'),
            'YouTube_API': ('404', 'ожидаемый код 404 для API (только HEAD запрос)'),
            'YouTubeVideoRedirect': ('302', 'ожидаемая переадресация'),
            'DiscordUpdates': ('404', 'ожидаемый код 404 для updates endpoint'),
        }

        if target_name in special_targets:
            expected_code, explanation = special_targets[target_name]
            if http_code == expected_code:
                return True, explanation
            else:
                return True, f"получен код {http_code} вместо ожидаемого {expected_code}"

        return False, ""

    async def _curl_request(self, url: str, protocol: str, args: List[str]) -> Dict:
        """Выполняет один запрос через curl"""

        # Пропускаем для Rutracker, так как у него свой тест
        if "rutracker.org" in url:
            return {
                "protocol": protocol,
                "success": False,
                "blocked": False,
                "details": "Rutracker тестируется отдельным методом"
            }

        curl_cmd = ['curl', '-I', '-s', '-L', '-m', '1',
                '-o', '/dev/null', '-w', '%{http_code}::%{time_total}::%{size_download}']
        curl_cmd.extend(args)
        curl_cmd.append(url)

        result = {
            "protocol": protocol,
            "success": False,
            "blocked": False,
            "details": ""
        }

        try:
            proc = await asyncio.create_subprocess_exec(
                *curl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()
            output = stdout.decode('utf-8', errors='ignore').strip()
            error_output = stderr.decode('utf-8', errors='ignore').lower()

            if proc.returncode == 0 and '::' in output:
                parts = output.split('::')
                if len(parts) >= 2:
                    http_code, time_taken = parts[0], parts[1]

                    # Расширенный список успешных HTTP статусов
                    success_codes = {
                        '200',  # OK
                        '301',  # Moved Permanently
                        '302',  # Found (переадресация)
                        '303',  # See Other
                        '304',  # Not Modified
                        '307',  # Temporary Redirect
                        '308',  # Permanent Redirect
                        '204',  # No Content (специально для generate_204)
                        '404',  # Not Found (ожидаемое поведение для некоторых API)
                        '405',  # Method Not Allowed (ожидаемое для API методов)
                        '403',  # Forbidden (но доступ был)
                    }

                    # Дополнительно проверяем для специфичных URL
                    url_lower = url.lower()

                    if http_code in success_codes:
                        result["success"] = True
                        result["details"] = f"{protocol}: код {http_code}, время {time_taken}с"

                        # Добавляем пояснение для специфичных кодов
                        if http_code == '204':
                            result["details"] = f"{protocol}: код 204 (No Content) ✓, время {time_taken}с"
                        elif http_code == '404':
                            result["details"] = f"{protocol}: код 404 (ожидаемо для API) ✓, время {time_taken}с"
                        elif http_code == '405':
                            result["details"] = f"{protocol}: код 405 (ожидаемо для API) ✓, время {time_taken}с"

                    else:
                        result["details"] = f"{protocol}: код {http_code}"

            elif 'ssl' in error_output or 'certificate' in error_output:
                result["blocked"] = True
                result["details"] = f"{protocol}: SSL блокировка"
            elif 'reset' in error_output or 'rst' in error_output:
                result["blocked"] = True
                result["details"] = f"{protocol}: сброс соединения"
            elif 'timed out' in error_output or 'timeout' in error_output:
                result["details"] = f"{protocol}: таймаут"
            elif 'could not resolve' in error_output:
                result["details"] = f"{protocol}: DNS ошибка"
            else:
                result["details"] = f"{protocol}: ошибка {proc.returncode}"

        except Exception as e:
            result["details"] = f"{protocol}: исключение {str(e)}"

        return result

    async def _json_request(self, url: str, protocol: str, args: List[str]) -> Dict:
        """Выполняет запрос и проверяет корректность JSON"""
        # Команда для получения статуса и времени
        status_cmd = ['curl', '-s', '-L', '-m', '1',
                    '-H', 'Accept: application/json',
                    '-H', 'User-Agent: Zapret-Tester/1.0',
                    '-o', '/dev/null',
                    '-w', '%{http_code}::%{time_total}']
        status_cmd.extend(args)
        status_cmd.append(url)

        # Команда для получения контента
        content_cmd = ['curl', '-s', '-L', '-m', '1',
                    '-H', 'Accept: application/json',
                    '-H', 'User-Agent: Zapret-Tester/1.0']
        content_cmd.extend(args)
        content_cmd.append(url)

        result = {
            "protocol": protocol,
            "success": False,
            "blocked": False,
            "details": ""
        }

        try:
            # Получаем статус и время
            proc_status = await asyncio.create_subprocess_exec(
                *status_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout_status, stderr_status = await proc_status.communicate()
            status_output = stdout_status.decode('utf-8', errors='ignore').strip()
            error_output = stderr_status.decode('utf-8', errors='ignore').lower()

            if proc_status.returncode == 0 and '::' in status_output:
                http_code, time_taken = status_output.split('::')

                # Проверяем успешный статус
                if http_code == '200':  # Только 200, так как нам нужен валидный JSON
                    # Теперь получаем контент
                    proc_content = await asyncio.create_subprocess_exec(
                        *content_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )

                    stdout_content, stderr_content = await proc_content.communicate()
                    json_content = stdout_content.decode('utf-8', errors='ignore').strip()

                    if json_content:
                        try:
                            # Пробуем распарсить JSON
                            json_data = json.loads(json_content)

                            # Проверяем структуру JSON (ожидаем список или словарь)
                            if isinstance(json_data, list):
                                # Для первого URL: проверяем, что это список объектов
                                if len(json_data) > 0 and isinstance(json_data[0], dict):
                                    # Проверяем наличие ожидаемых полей для Decky plugins
                                    first_item = json_data[0]
                                    expected_fields = ['id', 'name', 'versions']
                                    found_fields = [field for field in expected_fields if field in first_item]

                                    if len(found_fields) >= 2:  # Хотя бы 2 из 3 полей
                                        result["success"] = True
                                        result["details"] = f"{protocol}: JSON валиден (список плагинов), {len(json_data)} элементов, время {time_taken}с"
                                    else:
                                        # Проверяем другие возможные структуры
                                        if 'name' in first_item or 'author' in first_item or 'description' in first_item:
                                            result["success"] = True
                                            result["details"] = f"{protocol}: JSON валиден (альтернативный формат), {len(json_data)} элементов, время {time_taken}с"
                                        else:
                                            result["details"] = f"{protocol}: Неожиданная структура списка"
                                else:
                                    result["details"] = f"{protocol}: Пустой список или элементы не являются объектами"

                            elif isinstance(json_data, dict):
                                # Для второго URL: проверяем структуру словаря
                                expected_fields = ['id', 'name', 'author', 'description', 'tags', 'versions']
                                found_fields = [field for field in expected_fields if field in json_data]

                                if len(found_fields) >= 3:  # Хотя бы 3 из ожидаемых полей
                                    result["success"] = True
                                    result["details"] = f"{protocol}: JSON валиден (объект плагина), {len(found_fields)} полей, время {time_taken}с"
                                else:
                                    # Проверяем, может быть это просто объект с данными
                                    if len(json_data) > 0:
                                        result["success"] = True
                                        result["details"] = f"{protocol}: JSON валиден (объект), {len(json_data)} полей, время {time_taken}с"
                                    else:
                                        result["details"] = f"{protocol}: Пустой объект"
                            else:
                                result["details"] = f"{protocol}: Ответ не является JSON объектом/массивом"

                        except json.JSONDecodeError as e:
                            result["details"] = f"{protocol}: Невалидный JSON ({str(e)})"
                        except Exception as e:
                            result["details"] = f"{protocol}: Ошибка обработки JSON ({str(e)})"
                    else:
                        result["details"] = f"{protocol}: Пустой ответ"
                else:
                    result["details"] = f"{protocol}: код {http_code} (ожидался 200)"
            elif 'ssl' in error_output or 'certificate' in error_output:
                result["blocked"] = True
                result["details"] = f"{protocol}: SSL блокировка"
            elif 'reset' in error_output or 'rst' in error_output:
                result["blocked"] = True
                result["details"] = f"{protocol}: сброс соединения"
            elif 'timed out' in error_output or 'timeout' in error_output:
                result["details"] = f"{protocol}: таймаут"
            elif 'could not resolve' in error_output:
                result["details"] = f"{protocol}: DNS ошибка"
            else:
                result["details"] = f"{protocol}: ошибка {proc_status.returncode}"

        except Exception as e:
            result["details"] = f"{protocol}: исключение {str(e)}"

        return result

    async def test_strategy(self, strategy_name: str, mode: str = "standard") -> Dict:
        """
        Тестирует одну стратегию
        """
        # Проверяем флаг остановки в начале
        if self.stop_requested:
            print(f"⏹️  Остановка тестирования стратегии {strategy_name}")
            return {
                "strategy": strategy_name,
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "Test stopped by user",
                "total_targets": 0,
                "successful": 0,
                "failed": 0,
                "blocked": 0,
                "success_rate": 0,
                "critical_fail": False,
                "critical_fail_reason": ""
            }

        print(f"\n{'='*60}")
        print(f"Тестируем стратегию: {strategy_name}")
        print(f"Режим: {mode}")
        print(f"{'='*60}")

        # Проверяем статус службы перед тестом
        self.check_service_status()

        # Загружаем цели
        targets = self._load_targets(mode)

        # Определяем обязательные цели
        critical_targets = []
        youtube_target = None
        discord_target = None

        for target in targets:
            if "youtube" in target["name"].lower():
                youtube_target = target
                critical_targets.append(target)
            elif "discord" in target["name"].lower():
                discord_target = target
                critical_targets.append(target)

        # Проверяем флаг остановки
        if self.stop_requested:
            print(f"⏹️  Остановка тестирования перед началом")
            return {
                "strategy": strategy_name,
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "Test stopped by user",
                "total_targets": 0,
                "successful": 0,
                "failed": 0,
                "blocked": 0,
                "success_rate": 0,
                "critical_fail": False,
                "critical_fail_reason": ""
            }

        # Подготавливаем конфиг стратегии
        temp_config = self._prepare_strategy_config(strategy_name)
        if not temp_config:
            return {
                "strategy": strategy_name,
                "mode": mode,
                "success": False,
                "error": "Не удалось подготовить конфигурацию стратегии",
                "critical_fail": False,
                "critical_fail_reason": ""
            }

        # Для DPI режима очищаем ipset
        if mode == "dpi":
            print("  [DPI] Очищаем ipset-all.txt...")
            self._cleanup_ipset_for_dpi()

        # Останавливаем текущий сервис
        print("  Останавливаем службу zapret...")
        success, output = self._run_command("systemctl stop zapret", use_sudo=True)
        if not success:
            print(f"  Предупреждение: {output}")

        # Убиваем оставшиеся процессы nfqws
        self._run_command("pkill -9 nfqws", use_sudo=True)
        time.sleep(2)

        try:
            # Подготавливаем временный конфиг
            temp_config = self._prepare_strategy_config(strategy_name)

            # ВРЕМЕННО ЗАМЕНЯЕМ КОНФИГ И ЗАПУСКАЕМ СЛУЖБУ

            # 1. Создаем бэкап оригинального config.txt
            config_file = self.project_root / "config.txt"
            if config_file.exists():
                backup_config = config_file.with_suffix('.test_backup.txt')
                shutil.copy2(config_file, backup_config)

                # 2. Копируем конфиг стратегии в основной config.txt
                with open(temp_config, 'r', encoding='utf-8') as src:
                    strategy_content = src.read()

                with open(config_file, 'w', encoding='utf-8') as dst:
                    dst.write(strategy_content)

                print(f"  Конфиг стратегии записан в {config_file}")

                # 3. ПЕРЕЗАПУСКАЕМ СЛУЖБУ ZAPRET С НОВЫМ КОНФИГОМ
                print("  Перезапускаем службу zapret...")

                # Останавливаем службу
                self._run_command("systemctl stop zapret", use_sudo=True)
                time.sleep(2)

                # Запускаем службу (она использует обновленный config.txt)
                success, output = self._run_command("systemctl start zapret", use_sudo=True, timeout=10)

                if not success:
                    print(f"  Ошибка запуска службы: {output}")
                    # Запускаем вручную через systemd-run
                    print("  Пробуем запустить вручную...")
                    manual_cmd = f"systemd-run --unit=zapret-test-{strategy_name} systemctl start zapret"
                    success, output = self._run_command(manual_cmd, use_sudo=True, timeout=10)

                # Даем время на запуск
                print("  Ожидание запуска (5 секунд)...")
                time.sleep(5)

                # Проверяем статус службы
                status_success, status_output = self._run_command("systemctl is-active zapret", use_sudo=False)

                if status_success and "active" in status_output:
                    print(f"  ✅ Служба zapret запущена")
                else:
                    print(f"  ⚠️  Служба zapret не активна: {status_output}")
                    # Проверяем процессы nfqws
                    pgrep_success, pgrep_output = self._run_command("pgrep nfqws", use_sudo=False)
                    if pgrep_success and pgrep_output.strip():
                        print(f"  ✅ Процесс nfqws запущен (PID: {pgrep_output.strip()})")
                    else:
                        print(f"  ❌ Процесс nfqws не запущен")

            # 4. ТЕСТИРУЕМ ЦЕЛИ
            print(f"  Тестируем {len(targets)} целей...")

            # Переменные для отслеживания статусов обязательных целей
            youtube_passed = False
            discord_passed = False

            target_results = []
            successful = 0
            failed = 0
            blocked = 0

            for target in targets:

                # ПРОВЕРЯЕМ ФЛАГ ОСТАНОВКИ ПЕРЕД КАЖДОЙ ЦЕЛЬЮ
                if self.stop_requested:
                    print(f"  ⏹️  Остановка тестирования текущей стратегии")
                    break

                target_result = await self._test_single_target(target)
                target_result["strategy"] = strategy_name
                target_results.append(target_result)

                if target_result["success"]:
                    successful += 1
                    status = "✓ УСПЕХ"
                    # Отмечаем успешные обязательные цели
                    if "youtube" in target["name"].lower():
                        youtube_passed = True
                    elif "discord" in target["name"].lower():
                        discord_passed = True
                elif target_result["blocked"]:
                    blocked += 1
                    status = "✗ БЛОКИРОВКА"
                else:
                    failed += 1
                    status = "✗ ОШИБКА"

                print(f"    {status}: {target['name']} - {target_result['details']}")

            # Проверяем, была ли остановка
            if self.stop_requested:
                print(f"  ⏹️  Тестирование стратегии прервано")
                # Возвращаем частичные результаты

        except Exception as e:
            print(f"  ❌ Ошибка тестирования: {e}")
            import traceback
            traceback.print_exc()
            target_results = []
            successful = failed = blocked = 0
            youtube_passed = discord_passed = False

        finally:
            # ВОССТАНАВЛИВАЕМ ОРИГИНАЛЬНОЕ СОСТОЯНИЕ
            print("  Завершение теста и восстановление...")

            try:
                # 1. Останавливаем службу
                self._run_command("systemctl stop zapret", use_sudo=True)
                self._run_command("pkill -9 nfqws", use_sudo=True)
                time.sleep(2)

                # 2. Восстанавливаем оригинальный config.txt
                if 'backup_config' in locals() and backup_config.exists():
                    shutil.copy2(backup_config, config_file)
                    backup_config.unlink()
                    print(f"  ✅ Оригинальный config.txt восстановлен")

                # 3. Запускаем оригинальную службу (если она была включена)
                # Проверяем, была ли служба запущена до теста
                if hasattr(self, 'service_was_running') and self.service_was_running:
                    print("  Восстанавливаем оригинальную службу...")
                    self._run_command("systemctl start zapret", use_sudo=True)

                # 4. Восстанавливаем ipset для DPI режима
                if mode == "dpi":
                    self._restore_ipset()

                # 5. Удаляем временные файлы
                if 'temp_config' in locals() and temp_config and temp_config.exists():
                    try:
                        temp_config.unlink()
                    except:
                        pass

            except Exception as e:
                print(f"  ⚠️  Ошибка при восстановлении: {e}")

        # Проверяем обязательные цели
        critical_fail = False
        critical_fail_reason = ""

        # Проверяем наличие обязательных целей в тесте
        if youtube_target and discord_target:
            if not youtube_passed and not discord_passed:
                critical_fail = True
                critical_fail_reason = "YouTube и Discord не работают"
            elif youtube_passed and not discord_passed:
                critical_fail = True
                critical_fail_reason = "YouTube работает, но Discord не работает"
            elif not youtube_passed and discord_passed:
                critical_fail = True
                critical_fail_reason = "Discord работает, но YouTube не работает"
        elif youtube_target and not youtube_passed:
            critical_fail = True
            critical_fail_reason = "YouTube не работает"
        elif discord_target and not discord_passed:
            critical_fail = True
            critical_fail_reason = "Discord не работает"

        if critical_fail:
            print(f"  ⚠️  КРИТИЧЕСКАЯ ОШИБКА: {critical_fail_reason}")

        # Собираем результаты
        results = {
            "strategy": strategy_name,
            "mode": mode,
            "timestamp": datetime.now().isoformat(),
            "total_targets": len(targets),
            "successful": successful,
            "failed": failed,
            "blocked": blocked,
            "success_rate": (successful / len(targets) * 100) if targets else 0,
            "youtube_passed": youtube_passed,
            "discord_passed": discord_passed,
            "critical_fail": critical_fail,
            "critical_fail_reason": critical_fail_reason,
            "target_results": target_results
        }

        # Корректируем процент успеха при критической ошибке
        if critical_fail:
            print(f"  Итог: {successful}/{len(targets)} успешно, но КРИТИЧЕСКАЯ ОШИБКА: {critical_fail_reason}")
        else:
            print(f"  Итог: {successful}/{len(targets)} успешно ({results['success_rate']:.1f}%)")

        if self.stop_requested:
            print(f"  ⏹️  Тестирование стратегии остановлено досрочно")

        return results
    def check_service_status(self) -> bool:
        """
        Проверяет, запущена ли служба zapret перед тестом
        """
        success, output = self._run_command("systemctl is-active zapret", use_sudo=False)
        self.service_was_running = success and "active" in output.lower()

        if self.service_was_running:
            print(f"  ℹ️  Служба zapret была запущена до теста")
        else:
            print(f"  ℹ️  Служба zapret не была запущена")

        return self.service_was_running

    def get_available_strategies(self) -> List[str]:
        """
        Получает список доступных стратегий

        :return: Список имен стратегий (без расширения)
        """
        strategies = []

        try:
            # Получаем все файлы в папке strategies (без расширений)
            for file in self.strategies_dir.iterdir():
                if file.is_file():
                    # Получаем имя файла без пути
                    strategy_name = file.name

                    # Пропускаем скрытые файлы и технические
                    if strategy_name.startswith('.'):
                        continue

                    # Пропускаем файлы с известными расширениями
                    lower_name = strategy_name.lower()
                    if any(lower_name.endswith(ext) for ext in
                        ['.txt', '.md', '.bak', '.tmp', '.old']):
                        continue

                    # Пропускаем технические файлы
                    if lower_name in ['readme', 'info', 'notes', 'changelog']:
                        continue

                    if strategy_name not in strategies:
                        strategies.append(strategy_name)

            # Сортируем по алфавиту
            strategies.sort()

            print(f"  Найдено стратегий: {len(strategies)}")
            for strategy in strategies:
                print(f"    - {strategy}")

        except Exception as e:
            print(f"Ошибка чтения стратегий: {e}")
            strategies = []

        return strategies

    def generate_report(self, results: List[Dict], filename: Optional[str] = None) -> str:
        """
        Генерирует HTML отчет
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"zapret_test_report_{timestamp}.html"

        report_path = self.reports_dir / filename

        # Сортируем результаты по эффективности
        sorted_results = sorted(results,
                              key=lambda x: x.get('success_rate', 0),
                              reverse=True)

        # Генерируем HTML
        html = self._generate_html_report(sorted_results)

        # Сохраняем отчет
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"\n📄 Отчет сохранен: {report_path}")
        return str(report_path)

    def _generate_html_report(self, results: List[Dict]) -> str:
        """Генерирует HTML содержимое отчета"""

        total_tests = sum(r.get('total_targets', 0) for r in results)
        total_success = sum(r.get('successful', 0) for r in results)

        # Разделяем стратегии на рабочие, частично рабочие и нерабочие
        working_strategies = []
        partially_working_strategies = []  # Частично рабочие (YouTube или Discord работает)
        non_working_strategies = []  # Не рабочие (<60% или оба сервиса не работают)

        for result in results:
            success_rate = result.get('success_rate', 0)
            youtube_passed = result.get('youtube_passed', False)
            discord_passed = result.get('discord_passed', False)

            # Если процент успеха < 60% - сразу в нерабочие
            if success_rate < 60:
                non_working_strategies.append(result)
                result["critical_fail"] = True
                result["critical_fail_reason"] = f"YouTube и Discord не работает"
                continue

            # Если процент успеха ≥ 60%, проверяем YouTube/Discord
            youtube_working = youtube_passed is True
            discord_working = discord_passed is True

            if not youtube_working and not discord_working:
                # Оба не работают при хорошем проценте - нерабочие
                non_working_strategies.append(result)
                result["critical_fail"] = True
                result["critical_fail_reason"] = "YouTube и Discord не работают"
            elif not youtube_working or not discord_working:
                # Один не работает - частично рабочие
                partially_working_strategies.append(result)
                result["critical_fail"] = True
                if not youtube_working and discord_working:
                    result["critical_fail_reason"] = "Discord работает, но YouTube не работает"
                elif youtube_working and not discord_working:
                    result["critical_fail_reason"] = "YouTube работает, но Discord не работает"
            else:
                # Оба работают - рабочие
                working_strategies.append(result)

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет тестирования Zapret DPI</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(45, 45, 45, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            border: 1px solid rgba(79, 195, 247, 0.2);
        }}

        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #4fc3f7;
            position: relative;
        }}

        .header::after {{
            content: '';
            position: absolute;
            bottom: -2px;
            left: 25%;
            width: 50%;
            height: 4px;
            background: linear-gradient(90deg, transparent, #4fc3f7, transparent);
        }}

        h1 {{
            color: #4fc3f7;
            font-size: 2.5em;
            margin: 0 0 10px 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}

        .subtitle {{
            color: #bb86fc;
            font-size: 1.2em;
            margin-bottom: 10px;
        }}

        .summary-card {{
            background: linear-gradient(135deg, #37474f 0%, #263238 100%);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 40px;
            border: 1px solid rgba(79, 195, 247, 0.3);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .stat-item {{
            text-align: center;
            padding: 20px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            transition: transform 0.3s ease;
        }}

        .stat-item:hover {{
            transform: translateY(-5px);
            background: rgba(79, 195, 247, 0.1);
        }}

        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}

        .success {{ color: #66bb6a; text-shadow: 0 0 10px rgba(102, 187, 106, 0.3); }}
        .warning {{ color: #ffb74d; text-shadow: 0 0 10px rgba(255, 183, 77, 0.3); }}
        .danger {{ color: #ff7043; text-shadow: 0 0 10px rgba(255, 112, 67, 0.3); }}
        .info {{ color: #4fc3f7; text-shadow: 0 0 10px rgba(79, 195, 247, 0.3); }}

        .strategy-card {{
            background: linear-gradient(135deg, #263238 0%, #1c262b 100%);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
            border-left: 5px solid #4fc3f7;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .strategy-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, #4fc3f7, #bb86fc, #4fc3f7);
        }}

        .strategy-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.3);
            border-left-color: #bb86fc;
        }}

        .strategy-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}

        .strategy-name {{
            font-size: 1.4em;
            font-weight: bold;
            color: #bb86fc;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .strategy-badge {{
            background: rgba(187, 134, 252, 0.2);
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            color: #bb86fc;
        }}

        .progress-container {{
            margin: 20px 0;
        }}

        .progress-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}

        .progress-bar {{
            height: 25px;
            background: rgba(55, 71, 79, 0.5);
            border-radius: 12px;
            overflow: hidden;
            position: relative;
        }}

        .progress-fill {{
            height: 100%;
            border-radius: 12px;
            background: linear-gradient(90deg, #66bb6a, #4caf50);
            position: relative;
            transition: width 1s ease-in-out;
        }}

        .progress-fill.warning-progress {{
            background: linear-gradient(90deg, #ffb74d, #ff9800);
        }}

        .progress-fill.danger-progress {{
            background: linear-gradient(90deg, #ff7043, #f44336);
        }}

        .target-list {{
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid rgba(79, 195, 247, 0.2);
        }}

        .target-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}

        .target-item {{
            padding: 15px;
            background: rgba(55, 71, 79, 0.3);
            border-radius: 8px;
            border-left: 4px solid #66bb6a;
            transition: all 0.3s ease;
        }}

        .target-item:hover {{
            background: rgba(55, 71, 79, 0.5);
            transform: translateX(5px);
        }}

        .target-item.blocked {{
            border-left-color: #ffb74d;
        }}

        .target-item.failed {{
            border-left-color: #ff7043;
        }}

        .target-name {{
            font-weight: bold;
            color: #e0e0e0;
            margin-bottom: 5px;
        }}

        .target-details {{
            font-size: 0.9em;
            color: #b0bec5;
        }}

        .protocol-badge {{
            display: inline-block;
            padding: 2px 8px;
            background: rgba(79, 195, 247, 0.2);
            border-radius: 10px;
            font-size: 0.8em;
            color: #4fc3f7;
            margin-right: 5px;
        }}

        .timestamp {{
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid rgba(79, 195, 247, 0.2);
            color: #78909c;
            font-size: 0.9em;
        }}

        .recommendation {{
            background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%);
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
            border: 2px solid #66bb6a;
            animation: pulse 2s infinite;
        }}

        .top-strategies {{
            background: linear-gradient(135deg, #37474f 0%, #263238 100%);
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
            border: 1px solid rgba(79, 195, 247, 0.3);
        }}

        .top-strategies-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}

        .top-strategy-item {{
            padding: 15px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            border-left: 4px solid #4fc3f7;
            transition: all 0.3s ease;
        }}

        .top-strategy-item:hover {{
            transform: translateY(-3px);
            background: rgba(79, 195, 247, 0.1);
            border-left-color: #bb86fc;
        }}

        .top-strategy-item.working {{
            border-left-color: #66bb6a;
        }}

        .top-strategy-item.partial {{
            border-left-color: #ffb74d;
        }}

        .top-strategy-item.non-working {{
            border-left-color: #ff7043;
        }}

        .top-strategy-name {{
            font-weight: bold;
            color: #e0e0e0;
            margin-bottom: 5px;
            font-size: 1.1em;
        }}

        .top-strategy-percent {{
            font-size: 1.8em;
            font-weight: bold;
            margin: 10px 0;
        }}

        .top-strategy-percent.working {{
            color: #66bb6a;
        }}

        .top-strategy-percent.partial {{
            color: #ffb74d;
        }}

        .top-strategy-percent.non-working {{
            color: #ff7043;
        }}

        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(102, 187, 106, 0.4); }}
            70% {{ box-shadow: 0 0 0 10px rgba(102, 187, 106, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(102, 187, 106, 0); }}
        }}

        .recommendation h3 {{
            color: #a5d6a7;
            margin-top: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .critical-fail {{
            background: linear-gradient(135deg, #8b0000 0%, #b22222 100%);
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
            border: 2px solid #ff4444;
            animation: critical-pulse 2s infinite;
        }}

        @keyframes critical-pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(255, 68, 68, 0.4); }}
            70% {{ box-shadow: 0 0 0 10px rgba(255, 68, 68, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(255, 68, 68, 0); }}
        }}

        .critical-fail h3 {{
            color: #ffaaaa;
            margin-top: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .partial-warning {{
            background: linear-gradient(135deg, #b26a00 0%, #cc7a00 100%);
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
            border: 2px solid #ffb74d;
            animation: partial-pulse 2s infinite;
        }}

        @keyframes partial-pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(255, 183, 77, 0.4); }}
            70% {{ box-shadow: 0 0 0 10px rgba(255, 183, 77, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(255, 183, 77, 0); }}
        }}

        .partial-warning h3 {{
            color: #ffd699;
            margin-top: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .low-percent-warning {{
            background: linear-gradient(135deg, #8b4513 0%, #a0522d 100%);
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
            border: 2px solid #ff7043;
            animation: low-percent-pulse 2s infinite;
        }}

        @keyframes low-percent-pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(255, 112, 67, 0.4); }}
            70% {{ box-shadow: 0 0 0 10px rgba(255, 112, 67, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(255, 112, 67, 0); }}
        }}

        .low-percent-warning h3 {{
            color: #ffb8a3;
            margin-top: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}

            .strategy-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }}

            .target-grid {{
                grid-template-columns: 1fr;
            }}

            .top-strategies-list {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Отчет тестирования Zapret DPI</h1>
            <div class="subtitle">Автоматический тест стратегий обхода блокировок</div>
            <div>Дата тестирования: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</div>
        </div>

        <div class="summary-card">
            <h2 style="color: #4fc3f7; margin-top: 0;">📈 Общая статистика</h2>
            <div style="color: #b0bec5; font-size: 0.9em; margin-bottom: 15px; font-style: italic;">
                * Частично рабочие стратегии: не работает либо YouTube, либо Discord
            </div>
            <div class="stats-grid">
                <div class="stat-item">
                    <div>Протестировано стратегий</div>
                    <div class="stat-value info">{len(results)}</div>
                </div>
                <div class="stat-item">
                    <div>Рабочих стратегий</div>
                    <div class="stat-value success">{len(working_strategies)}</div>
                </div>
                <div class="stat-item">
                    <div>Частично рабочих стратегий*</div>
                    <div class="stat-value warning">{len(partially_working_strategies)}</div>
                </div>
                <div class="stat-item">
                    <div>Не рабочих стратегий</div>
                    <div class="stat-value danger">{len(non_working_strategies)}</div>
                </div>
            </div>
        </div>
"""

        # Добавляем рекомендацию для лучшей стратегии
        if working_strategies:
            best_strategy = working_strategies[0]  # Уже отсортированы по эффективности
            html += f"""
        <div class="recommendation">
            <h3>⭐ Рекомендуемая стратегия (применена)</h3>
            <div style="font-size: 1.2em; margin-bottom: 10px;">
                <strong>{best_strategy.get('strategy', 'Неизвестная')}</strong>
                <span style="margin-left: 20px; color: #66bb6a;">
                    Эффективность: <strong>{best_strategy.get('success_rate', 0):.1f}%</strong>
                </span>
            </div>
            <div style="color: #b0bec5;">
                Успешно: {best_strategy.get('successful', 0)}/{best_strategy.get('total_targets', 0)} •
                Блокировок: {best_strategy.get('blocked', 0)} •
                Неудачно: {best_strategy.get('failed', 0)}
            </div>
        </div>
"""

        # Добавляем топ стратегий
        if working_strategies or partially_working_strategies or non_working_strategies:
            html += """
        <div class="top-strategies">
            <h2 style="color: #4fc3f7; margin-top: 0;">Краткая сводка по тесту</h2>
            <div class="top-strategies-list">
"""

            # Сначала выводим рабочие стратегии (отсортированы по убыванию эффективности)
            for strategy in working_strategies:
                strategy_name = strategy.get('strategy', 'Неизвестная')
                success_rate = strategy.get('success_rate', 0)

                html += f"""
                <div class="top-strategy-item working">
                    <div class="top-strategy-name">{strategy_name}</div>
                    <div class="top-strategy-percent working">{success_rate:.1f}%</div>
                    <div style="color: #b0bec5; font-size: 0.9em;">
                        Успешно: {strategy.get('successful', 0)}/{strategy.get('total_targets', 0)}
                    </div>
                </div>
"""

            # Затем выводим частично рабочие стратегии
            for strategy in partially_working_strategies:
                strategy_name = strategy.get('strategy', 'Неизвестная')
                success_rate = strategy.get('success_rate', 0)
                critical_reason = strategy.get('critical_fail_reason', '')

                html += f"""
                <div class="top-strategy-item partial">
                    <div class="top-strategy-name">{strategy_name}</div>
                    <div class="top-strategy-percent partial">{success_rate:.1f}%</div>
                    <div style="color: #b0bec5; font-size: 0.9em;">
                        Успешно: {strategy.get('successful', 0)}/{strategy.get('total_targets', 0)}
                        {f'<br><span style="color: #ffb74d;">⚠️ {critical_reason}</span>' if critical_reason else ''}
                    </div>
                </div>
"""

            # Затем выводим нерабочие стратегии
            for strategy in non_working_strategies:
                strategy_name = strategy.get('strategy', 'Неизвестная')
                success_rate = strategy.get('success_rate', 0)
                critical_reason = strategy.get('critical_fail_reason', '')

                html += f"""
                <div class="top-strategy-item non-working">
                    <div class="top-strategy-name">{strategy_name}</div>
                    <div class="top-strategy-percent non-working">{success_rate:.1f}%</div>
                    <div style="color: #b0bec5; font-size: 0.9em;">
                        Успешно: {strategy.get('successful', 0)}/{strategy.get('total_targets', 0)}
                        {f'<br><span style="color: #ff4444;">⚠️ {critical_reason}</span>' if critical_reason else ''}
                    </div>
                </div>
"""

            html += """
            </div>
        </div>
"""

        # Добавляем полную информацию по стратегиям
        html += """
        <h2 style="color: #4fc3f7; margin-bottom: 25px;">🎯 Детальные результаты по стратегиям</h2>
"""

        # Выводим сначала рабочие стратегии
        if working_strategies:
            html += f"""
        <h3 style="color: #66bb6a; margin-bottom: 15px;">✅ Рабочие стратегии</h3>
"""

            for i, result in enumerate(working_strategies, 1):
                html += self._generate_strategy_card(result, i)

        # Выводим частично рабочие стратегии
        if partially_working_strategies:
            html += f"""
        <h3 style="color: #ffb74d; margin-bottom: 15px; margin-top: 40px;">⚠️ Частично рабочие стратегии (работает только YouTube или Discord)*</h3>
"""

            for i, result in enumerate(partially_working_strategies, 1):
                html += self._generate_strategy_card(result, i + len(working_strategies))

        # Выводим нерабочие стратегии
        if non_working_strategies:
            # Фильтруем по типу нерабочих
            low_percent = [s for s in non_working_strategies if "Эффективность ниже порога" in s.get('critical_fail_reason', '')]
            both_broken = [s for s in non_working_strategies if "YouTube и Discord не работают" in s.get('critical_fail_reason', '')]

            if low_percent:
                html += f"""
        <h3 style="color: #ff7043; margin-bottom: 15px; margin-top: 40px;">❌ Не рабочие стратегии</h3>
"""

                for i, result in enumerate(low_percent, 1):
                    html += self._generate_strategy_card(result, i + len(working_strategies) + len(partially_working_strategies))

            if both_broken:
                html += f"""
        <h3 style="color: #ff4444; margin-bottom: 15px; margin-top: 40px;">🚫 Критические ошибки (YouTube и Discord не работают)</h3>
"""

                for i, result in enumerate(both_broken, 1):
                    html += self._generate_strategy_card(result, i + len(working_strategies) + len(partially_working_strategies) + len(low_percent))

        html += f"""
        <div class="timestamp">
            Сгенерировано Zapret DPI Manager • Steam Deck • {datetime.now().strftime("%d.%m.%Y %H:%M")}
        </div>
    </div>
</body>
</html>"""

        return html

    def _generate_strategy_card(self, result: Dict, index: int) -> str:
        """Генерирует HTML карточку для одной стратегии"""
        strategy_name = result.get('strategy', 'Неизвестная')
        success_rate = result.get('success_rate', 0)
        successful = result.get('successful', 0)
        total = result.get('total_targets', 1)
        failed = result.get('failed', 0)
        blocked = result.get('blocked', 0)
        mode = result.get('mode', 'standard')
        critical_fail = result.get('critical_fail', False)
        critical_reason = result.get('critical_fail_reason', '')

        # Определяем тип стратегии для цветового кодирования
        is_partial = False
        is_low_percent = False
        is_both_broken = False

        if critical_fail and critical_reason:
            if "Эффективность ниже порога" in critical_reason:
                is_low_percent = True
            elif "YouTube и Discord не работают" in critical_reason:
                is_both_broken = True
            elif "работает, но" in critical_reason:
                is_partial = True

        # Определяем класс прогресс-бара
        progress_class = "progress-fill"
        if is_both_broken:
            progress_class += " danger-progress"
        elif is_low_percent:
            progress_class += " danger-progress"
        elif is_partial:
            progress_class += " warning-progress"
        elif success_rate < 50:
            progress_class += " danger-progress"
        elif success_rate < 80:
            progress_class += " warning-progress"

        # Определяем иконку для стратегии
        icon = "🔧"
        if 'http' in strategy_name.lower():
            icon = "🌐"
        elif 'tls' in strategy_name.lower():
            icon = "🔒"
        elif 'quic' in strategy_name.lower():
            icon = "⚡"
        elif 'mixed' in strategy_name.lower():
            icon = "🔄"

        # Добавляем иконку в зависимости от типа
        if is_both_broken:
            icon = "🚫"
        elif is_low_percent:
            icon = "❌"
        elif is_partial:
            icon = "⚠️"

        # Определяем цвет заголовка
        title_color = "#66bb6a"  # по умолчанию зеленый
        if is_both_broken:
            title_color = "#ff4444"  # красный для критических
        elif is_low_percent:
            title_color = "#ff7043"  # темно-оранжевый для низкого процента
        elif is_partial:
            title_color = "#ffb74d"  # оранжевый для частично рабочих

        html = f"""
        <div class="strategy-card">
            <div class="strategy-header">
                <div class="strategy-name">
                    {icon} {strategy_name}
                    <span class="strategy-badge">{mode.upper()}</span>
                    {f"<span style='color: {title_color}; margin-left: 10px; font-size: 0.9em;'>🚫 КРИТИЧЕСКАЯ ОШИБКА</span>" if is_both_broken else ""}
                    {f"<span style='color: {title_color}; margin-left: 10px; font-size: 0.9em;'>❌ НИЗКАЯ ЭФФЕКТИВНОСТЬ</span>" if is_low_percent else ""}
                    {f"<span style='color: {title_color}; margin-left: 10px; font-size: 0.9em;'>⚠️ ЧАСТИЧНО РАБОТАЕТ</span>" if is_partial else ""}
                </div>
                <div style="font-size: 1.3em; font-weight: bold; color: {title_color};">
                    {success_rate:.1f}%
                </div>
            </div>
    """

        # Добавляем блок с предупреждением в зависимости от типа
        if is_both_broken:
            html += f"""
            <div class="critical-fail" style="margin-bottom: 20px;">
                <h3>⚠️ Критическая ошибка</h3>
                <div style="color: #ffaaaa; font-size: 1.1em;">
                    {critical_reason}
                </div>
            </div>
    """
        elif is_low_percent:
            html += f"""
            <div class="low-percent-warning" style="margin-bottom: 20px;">
                <h3>⚠️ Низкая эффективность</h3>
                <div style="color: #ffb8a3; font-size: 1.1em;">
                    {critical_reason}
                </div>
            </div>
    """
        elif is_partial:
            html += f"""
            <div class="partial-warning" style="margin-bottom: 20px;">
                <h3>⚠️ Частично работает</h3>
                <div style="color: #ffd699; font-size: 1.1em;">
                    {critical_reason}
                </div>
            </div>
    """

        html += f"""
            <div class="progress-container">
                <div class="progress-label">
                    <span>Эффективность</span>
                    <span>{successful}/{total} успешно</span>
                </div>
                <div class="progress-bar">
                    <div class="{progress_class}" style="width: {success_rate}%"></div>
                </div>
            </div>

            <div style="display: flex; gap: 20px; margin: 15px 0;">
                <div style="text-align: center;">
                    <div style="font-size: 1.8em; color: #66bb6a; font-weight: bold;">{successful}</div>
                    <div style="font-size: 0.9em; color: #b0bec5;">Успешно</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.8em; color: #ff7043; font-weight: bold;">{failed}</div>
                    <div style="font-size: 0.9em; color: #b0bec5;">Неудачно</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 1.8em; color: #ffb74d; font-weight: bold;">{blocked}</div>
                    <div style="font-size: 0.9em; color: #b0bec5;">Блокировки</div>
                </div>
            </div>
    """

        # Добавляем детали по целям с отладочной информацией
        if result.get('target_results'):
            html += """
            <div class="target-list">
                <h3 style="color: #4fc3f7; margin-top: 0; font-size: 1.1em;">Детальные результаты:</h3>
                <div class="target-grid">
    """

            for target_result in result.get('target_results', []):
                target_name = target_result.get('target_name', 'Неизвестная цель')
                details = target_result.get('details', 'Нет данных')
                protocol = target_result.get('protocol', 'N/A')
                success = target_result.get('success', False)
                blocked = target_result.get('blocked', False)

                # Определяем класс и иконку
                item_class = "target-item"
                icon = "✅"

                if blocked:
                    item_class += " blocked"
                    icon = "🛑"
                elif not success:
                    item_class += " failed"
                    icon = "❌"

                html += f"""
                    <div class="{item_class}">
                        <div class="target-name">{icon} {target_name}</div>
                        <div class="target-details">
                            <span class="protocol-badge">{protocol}</span>
                            {details}
                        </div>
                    </div>
    """

            html += """
                </div>
            </div>
    """

        html += "</div>"
        return html

    async def run_full_test(self, mode: str = "standard",
                        strategies: Optional[List[str]] = None,
                        stop_callback: Optional[callable] = None) -> List[Dict]:
        """
        Выполняет полное тестирование всех стратегий
        """
        print("🚀 Zapret DPI Strategy Tester")
        print("="*60)

        # Сбрасываем флаг остановки
        self.stop_requested = False

        # Получаем список стратегий
        if strategies is None:
            strategies = self.get_available_strategies()

        if not strategies:
            print("❌ Не найдено ни одной стратегии для тестирования")
            print(f"   Проверьте папку: {self.strategies_dir}")
            return []

        print(f"📁 Папка стратегий: {self.strategies_dir}")
        print(f"📋 Будет протестировано: {len(strategies)} стратегий")
        print(f"🎯 Режим тестирования: {mode}")
        print("="*60)

        all_results = []

        for i, strategy in enumerate(strategies, 1):
            # ПРОВЕРЯЕМ, НЕ ЗАПРОШЕНА ЛИ ОСТАНОВКА
            if self.stop_requested:
                print(f"\n⏹️  Тестирование остановлено пользователем")
                print(f"   Завершено стратегий: {i-1}/{len(strategies)}")
                break

            # Также проверяем callback, если он предоставлен
            if stop_callback and stop_callback():
                print(f"\n⏹️  Тестирование остановлено через callback")
                print(f"   Завершено стратегий: {i-1}/{len(strategies)}")
                break

            print(f"\n[{i}/{len(strategies)}] Тестируем стратегию: {strategy}")

            try:
                # Добавляем проверку флага в метод test_strategy (изменение ниже)
                result = await self.test_strategy(strategy, mode)

                if result.get('error') == 'Test stopped by user':
                    print(f"   ⏹️  Тестирование стратегии остановлено")
                    all_results.append(result)
                    break

                all_results.append(result)

                # Выводим краткий результат
                success = result.get('successful', 0)
                total = result.get('total_targets', 0)
                success_rate = result.get('success_rate', 0)

                if success_rate >= 80:
                    rating = "⭐ ОТЛИЧНО"
                elif success_rate >= 60:
                    rating = "⚠️  НОРМАЛЬНО"
                else:
                    rating = "❌ ПЛОХО"

                print(f"   Результат: {rating} ({success}/{total} успешно, {success_rate:.1f}%)")

            except Exception as e:
                print(f"   ❌ Ошибка тестирования: {e}")
                all_results.append({
                    "strategy": strategy,
                    "error": str(e),
                    "success": False
                })

        if all_results and not self.stop_requested:
            # Сохраняем список рабочих стратегий
            working_names = []
            for result in all_results:
                success_rate = result.get('success_rate', 0)
                youtube_passed = result.get('youtube_passed', False)
                discord_passed = result.get('discord_passed', False)

                # Критерии рабочей стратегии:
                # 1. Успешность ≥ 60%
                # 2. ОБА YouTube и Discord работают
                if success_rate >= 60 and youtube_passed is True and discord_passed is True:
                    working_names.append(result.get('strategy', ''))

            if working_names:
                try:
                    # Сохраняем в файл working_strategies.txt
                    working_strategies_file = self.utils_dir / "working_strategies.txt"
                    with open(working_strategies_file, 'w', encoding='utf-8') as f:
                        for name in working_names:
                            if name:  # Проверяем что имя не пустое
                                f.write(name + '\n')
                    print(f"💾 Сохранено {len(working_names)} рабочих стратегий в файл")
                except Exception as e:
                    print(f"⚠️ Не удалось сохранить список рабочих стратегий: {e}")

            report_path = self.generate_report(all_results)
            print(f"\n✅ Тестирование завершено!")
            print(f"📄 Отчет сохранен: {report_path}")

            # Открываем отчет в браузере
            try:
                import webbrowser
                webbrowser.open(f"file://{report_path}")
            except:
                print("   ℹ️  Отчет можно открыть вручную")
        elif self.stop_requested:
            print(f"\n⏹️  Тестирование остановлено")
            print(f"   Протестировано стратегий: {len(all_results)}")
            # Можно сохранить частичный отчет
            if all_results:
                report_path = self.generate_report(all_results, "partial_test_report.html")
                print(f"📄 Частичный отчет сохранен: {report_path}")

        return all_results


# Упрощенная функция для использования
async def test_all_strategies(project_root: str, mode: str = "standard",
                            sudo_password: Optional[str] = None,
                            stop_callback: Optional[callable] = None) -> List[Dict]:
    """
    Простая функция для тестирования всех стратегий
    """
    tester = StrategyTester(project_root, sudo_password)
    return await tester.run_full_test(mode, stop_callback=stop_callback)


if __name__ == "__main__":
    # Пример использования из командной строки
    import sys
    import getpass

    async def main():
        project_root = "/home/deck/Zapret_DPI_Manager"

        if len(sys.argv) > 1:
            mode = sys.argv[1]
        else:
            print("Выберите режим тестирования:")
            print("  1. Standard (YouTube, Discord)")
            print("  2. DPI (технический тест)")
            choice = input("Ваш выбор (1/2): ").strip()
            mode = "dpi" if choice == "2" else "standard"

        print("\n🔐 Для тестирования требуется пароль sudo")
        sudo_password = getpass.getpass("Введите пароль sudo: ")

        if not sudo_password:
            print("❌ Пароль не введен. Тестирование невозможно.")
            sys.exit(1)

        tester = StrategyTester(project_root, sudo_password)
        await tester.run_full_test(mode)

    asyncio.run(main())
