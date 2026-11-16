"""Open the real config in Kate and observe successful saves without writing it."""
import shutil
import subprocess

from core.strategy_settings import ConfigDocument


class KateEditorSession:
    def __init__(self, document):
        self.document = document
        self.process = None

    def start(self):
        executable = shutil.which('kate')
        if not executable:
            raise FileNotFoundError('Редактор Kate не найден. Установите Kate и повторите открытие config.')
        self.process = subprocess.Popen(
            [executable, '--new', '--block', str(self.document.path.resolve())],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def check_saved(self):
        current = ConfigDocument(self.document.path, self.document.root)
        if current.original == self.document.original:
            return False
        self.document = current
        return True

    def poll(self):
        return self.process.poll()
