"""Supervise a separate image process, including crashes and timeouts."""
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QProcess, QEventLoop, QTimer

from .store import ValidationError


def worker_command(output, source):
    arguments = ['--photo-worker', str(output)]
    if not getattr(sys, 'frozen', False):
        arguments.insert(0, str(Path(__file__).resolve().parents[1] / 'main.py'))
    if source is not None:
        arguments.append(str(source))
    return sys.executable, arguments


def isolated_photo(source=None):
    with tempfile.TemporaryDirectory(prefix='printtrack-upload-') as temporary:
        output = Path(temporary) / 'photo.png'
        executable, arguments = worker_command(output, source)
        process = QProcess()
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        process.finished.connect(loop.quit)
        process.errorOccurred.connect(loop.quit)
        timer.timeout.connect(loop.quit)
        process.start(executable, arguments)
        timer.start(30000 if source is not None else 300000)
        if process.state() != QProcess.NotRunning:
            loop.exec()
        timer.stop()
        if process.state() != QProcess.NotRunning:
            process.kill()
            process.waitForFinished(5000)
            raise ValidationError('Nuotraukos įkėlimas užtruko per ilgai. Ankstesnė nuotrauka nepakeista.')
        if process.exitStatus() == QProcess.NormalExit and process.exitCode() == 10:
            return None
        if process.exitStatus() != QProcess.NormalExit or process.exitCode() != 0 or not output.is_file():
            detail = Path(str(output) + '.error.txt')
            message = detail.read_text('utf-8')[:1200] if detail.exists() else 'Nuotraukų modulis nustojo veikti (kodas ' + str(process.exitCode()) + ').'
            raise ValidationError(message + '\nPrograma ir įrašai išsaugoti. Pabandykite kitą nuotrauką.')
        return output.read_bytes()
