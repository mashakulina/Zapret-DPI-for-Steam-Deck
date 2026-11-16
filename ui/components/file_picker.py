"""Use the desktop's file chooser without adding Qt/Gtk Python dependencies."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
from tkinter import TclError, filedialog


def _x11_parent_id(parent):
    # A Tk XWayland ID cannot be used as the parent of a native Wayland dialog.
    if os.environ.get('XDG_SESSION_TYPE', '').lower() == 'wayland':
        return None
    try:
        if parent.tk.call('tk', 'windowingsystem') == 'x11':
            parent.update_idletasks()
            return str(parent.winfo_id())
    except (AttributeError, RuntimeError, TclError):
        pass
    return None


def ask_open_file(parent, *, title, suffix, initialdir=None):
    """Return one filename, or an empty string when the user cancels."""
    directory = Path(initialdir).expanduser() if initialdir is not None else Path.home()
    if not directory.is_dir():
        directory = Path.home()
    patterns = f'*{suffix.lower()} *{suffix.upper()}'
    label = suffix.lstrip('.').upper()

    if sys.platform.startswith('linux'):
        desktop = ':'.join(os.environ.get(key, '') for key in
                           ('XDG_CURRENT_DESKTOP', 'DESKTOP_SESSION')).lower()
        kde = 'kde' in desktop or 'plasma' in desktop or os.environ.get('KDE_FULL_SESSION') == 'true'
        backends = ('kdialog', 'zenity') if kde else ('zenity', 'kdialog')
        parent_id = _x11_parent_id(parent)
        for backend in backends:
            executable = shutil.which(backend)
            if not executable:
                continue
            if backend == 'kdialog':
                # KDE name filters: https://develop.kde.org/docs/administration/kdialog/
                argv = [executable, '--getopenfilename', str(directory),
                        f'Файлы {label} ({patterns});;Все файлы (*)', '--title', title]
                if parent_id:
                    argv.extend(['--attach', parent_id])
            else:
                argv = [executable, '--file-selection', f'--title={title}',
                        '--filename=' + str(directory) + os.sep,
                        f'--file-filter={label} | {patterns}', '--file-filter=Все файлы | *']
                if parent_id:
                    argv.append('--attach=' + parent_id)
            try:
                result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
            except OSError:
                continue
            if result.returncode == 0:
                return os.fsdecode(result.stdout).rstrip('\r\n')
            if result.returncode == 1:
                # Cancel is final: never open a second dialog after dismissing one.
                return ''

    # Keep browsing available on systems without a desktop helper. Tk uses the
    # native file chooser on Windows/macOS as well.
    return filedialog.askopenfilename(
        parent=parent, title=title, initialdir=str(directory),
        filetypes=[(f'Файлы {label}', patterns), ('Все файлы', '*')],
    )
