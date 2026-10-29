"""Image selection/decoding is isolated from the inventory application process."""
import sys
from pathlib import Path


def run(output, source=None):
    try:
        from PySide6.QtWidgets import QApplication, QFileDialog
        from PySide6.QtGui import QPixmap
        from .images import photo_png
        app = QApplication(sys.argv[:1])
        app.setApplicationName('PrintTrack · Nuotrauka')
        if source is None:
            source, _ = QFileDialog.getOpenFileName(None, 'PrintTrack · Pasirinkti nuotrauką', '',
                'Nuotraukos (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff *.ico);;Visi failai (*)',
                options=QFileDialog.DontUseNativeDialog)
            if not source:
                return 10
        content = photo_png(source)
        pix = QPixmap()
        if not pix.loadFromData(content, 'PNG'):
            raise ValueError('Nepavyko patikrinti nuotraukos peržiūros.')
        Path(output).write_bytes(content)
        return 0
    except Exception as error:
        Path(str(output) + '.error.txt').write_text(str(error), encoding='utf-8')
        return 2
