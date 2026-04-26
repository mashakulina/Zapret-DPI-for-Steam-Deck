"""Плагин Decky Zapret DPI."""
import os
import shlex
import subprocess
import threading
import tkinter as tk

from ui.components.custom_messagebox import ask_yesno, show_error, show_info

# Выполняется под root через sudo -S; скрипт сам вызывает sudo (systemctl, cp в plugins).
ZAPRET_DPI_PLUGIN_INSTALL_CMD = (
    "bash <(curl -fsSL https://raw.githubusercontent.com/mashakulina/DeckyZapretDPI/main/InstallPlugin.sh)"
)


class MainDeckyMixin:
    def is_decky_zapret_plugin_installed(self):
        """Плагин Zapret DPI (Decky) лежит в ~/homebrew/plugins/DeckyZapretDPI."""
        return os.path.isdir(self.decky_plugin_path)

    def install_decky_plugin(self):
        """Устанавливает плагин Zapret DPI для Decky через официальный скрипт (нужен sudo)."""
        self.close_settings_menu()
        if self.is_decky_zapret_plugin_installed():
            show_info(self.root, "Плагин Zapret DPI", "Плагин Zapret DPI уже установлен.")
            return

        if not self.ensure_sudo_password():
            return

        sudo_pwd = self.service_manager.sudo_password
        self.show_status_message("Установка плагина Zapret DPI...")

        def worker():
            try:
                result = subprocess.run(
                    ["sudo", "-S", "bash", "-c", ZAPRET_DPI_PLUGIN_INSTALL_CMD],
                    input=(sudo_pwd + "\n") if sudo_pwd else None,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=os.environ.copy(),
                )
                ok = result.returncode == 0 and self.is_decky_zapret_plugin_installed()

                def done():
                    self.decky_plugin_installed = self.is_decky_zapret_plugin_installed()
                    if ok:
                        self.show_status_message("Плагин Zapret DPI установлен", success=True)
                        show_info(
                            self.root,
                            "Плагин Zapret DPI",
                            "Плагин установлен. При необходимости перезапустите Decky Loader или Steam, "
                            "чтобы плагин появился в меню.",
                        )
                    else:
                        err_tail = (result.stderr or result.stdout or "").strip()
                        if len(err_tail) > 800:
                            err_tail = err_tail[-800:]
                        msg = "Не удалось установить плагин."
                        if err_tail:
                            msg += f"\n\n{err_tail}"
                        self.show_status_message("Ошибка установки плагина Zapret DPI", error=True)
                        show_error(self.root, "Установка плагина Zapret DPI", msg)

                self.root.after(0, done)
            except subprocess.TimeoutExpired:
                self.root.after(0, lambda: (
                    self.show_status_message("Таймаут установки плагина Zapret DPI", error=True),
                    show_error(
                        self.root,
                        "Установка плагина Zapret DPI",
                        "Превышено время ожидания. Проверьте соединение и попробуйте снова.",
                    ),
                ))
            except Exception as e:
                err = str(e)

                def show_ex():
                    self.show_status_message(f"Ошибка установки плагина: {err}", error=True)
                    show_error(self.root, "Установка плагина Zapret DPI", err)

                self.root.after(0, show_ex)

        threading.Thread(target=worker, daemon=True).start()

    def remove_decky_plugin(self):
        """Удаляет каталог плагина Zapret DPI из ~/homebrew/plugins/ (через sudo)."""
        self.close_settings_menu()
        if not self.is_decky_zapret_plugin_installed():
            show_info(self.root, "Плагин Zapret DPI", "Плагин Zapret DPI не найден.")
            self.decky_plugin_installed = False
            return

        if not ask_yesno(
            self.root,
            "Удаление плагина Zapret DPI",
            "Удалить плагин Zapret DPI из папки homebrew/plugins?"
        ):
            return

        if not self.ensure_sudo_password():
            return

        self.show_status_message("Удаление плагина Zapret DPI...")

        def worker():
            try:
                rm_target = shlex.quote(self.decky_plugin_path)
                success, out = self.service_manager._run_sudo_command(f"rm -rf {rm_target}")

                def done():
                    if success and not self.is_decky_zapret_plugin_installed():
                        self._on_decky_plugin_removed_ok()
                    elif success:
                        self._on_decky_plugin_removed_err(
                            "Каталог всё ещё существует после удаления."
                        )
                    else:
                        self._on_decky_plugin_removed_err(out or "Не удалось удалить каталог.")

                self.root.after(0, done)
            except Exception as e:
                self.root.after(0, lambda err=str(e): self._on_decky_plugin_removed_err(err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_decky_plugin_removed_ok(self):
        self.decky_plugin_installed = False
        self.show_status_message("Плагин Zapret DPI удалён", success=True)
        show_info(
            self.root,
            "Плагин Zapret DPI",
            "Каталог плагина удалён. Перезапустите Decky Loader при необходимости.",
        )

    def _on_decky_plugin_removed_err(self, err):
        self.show_status_message("Не удалось удалить плагин Zapret DPI", error=True)
        show_error(self.root, "Удаление плагина Zapret DPI", err)
