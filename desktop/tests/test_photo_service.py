import sys

import pytest
from PIL import Image
from PySide6.QtCore import QEvent
from PySide6.QtGui import QPixmap

from printtrack.photo_service import isolated_photo
from printtrack.store import ValidationError
from printtrack.ui import PhotoLabel


@pytest.mark.parametrize('extension', ['png', 'jpg', 'webp', 'bmp', 'gif', 'tiff', 'ico'])
def test_isolated_photo_formats(qtbot, tmp_path, extension):
    path = tmp_path / ('nuotrauka.' + extension)
    Image.new('RGB', (128, 128), (50, 80, 90)).save(path)
    content = isolated_photo(path)
    pix = QPixmap()
    assert pix.loadFromData(content, 'PNG')


def test_worker_crash_is_reported_without_terminating_parent(qtbot, monkeypatch):
    monkeypatch.setattr('printtrack.photo_service.worker_command',
        lambda *a: (sys.executable, ['-c', 'import os; os._exit(9)']))
    with pytest.raises(ValidationError, match='kodas 9'):
        isolated_photo('test.png')
    label = PhotoLabel()
    qtbot.addWidget(label)
    label.show()
    assert label.isVisible()


def test_hover_enlarges_and_leave_hides(qtbot):
    label = PhotoLabel()
    qtbot.addWidget(label)
    label.resize(90, 65)
    pix = QPixmap(640, 480)
    pix.fill()
    label.setPixmap(pix)
    label.show()
    from PySide6.QtGui import QEnterEvent
    from PySide6.QtCore import QPointF
    label.enterEvent(QEnterEvent(QPointF(), QPointF(), QPointF()))
    assert label.popup.isVisible()
    assert label.popup.pixmap().width() > label.width()
    label.leaveEvent(QEvent(QEvent.Leave))
    assert not label.popup.isVisible()
