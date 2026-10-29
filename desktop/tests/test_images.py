import base64
import random

import pytest
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QLabel, QMessageBox, QTableWidget, QPushButton
from PySide6.QtCore import Qt
from PIL import Image
from printtrack.images import photo_png

from printtrack.store import Store
from printtrack.ui import RecordDialog, Window


@pytest.mark.parametrize('extension', ['png', 'jpg', 'webp'])
def test_large_photo_survives_upload_edit_save_and_restart(qtbot, tmp_path, monkeypatch, extension):
    # A non-uniform photo exceeds QLineEdit's old implicit 32767-character limit.
    image = QImage(640, 480, QImage.Format_RGB888)
    image.bits()[:] = random.Random(17).randbytes(image.sizeInBytes())
    photo = tmp_path / ('spausdintuvas.' + extension)
    assert image.save(str(photo))
    store = Store(tmp_path / 'data')
    printer_id = store.save('printers', dict(name='Testas', model='HP 1020',
        ip='', serial='', room_id='', status='Veikia', image=''))
    window = Window(store)
    qtbot.addWidget(window)
    record = store.read()['printers'][0]
    dialog = RecordDialog(None, 'printers', store.read(), record)
    qtbot.addWidget(dialog)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a, **kw: (str(photo), ''))
    label = QLabel()
    qtbot.addWidget(label)
    dialog.load_photo(photo, dialog.fields['image'], label)
    encoded = dialog.values()['image']
    assert len(encoded) > 32767
    pix = QPixmap()
    assert pix.loadFromData(base64.b64decode(encoded, validate=True))
    assert not label.pixmap().isNull()
    store.save('printers', dialog.values(), printer_id)
    reopened = Store(store.directory)
    saved = reopened.read()['printers'][0]
    assert saved['image'].startswith('images/')
    assert reopened.image_bytes(saved['image']) == base64.b64decode(encoded)
    edited = RecordDialog(None, 'printers', reopened.read(), saved)
    qtbot.addWidget(edited)
    assert edited.values()['image'] == saved['image']
    window.nav.setCurrentRow(1)
    table = window.page_area.widget().findChild(QTableWidget)
    assert not table.item(0, 0).icon().isNull()
    table.selectRow(0)
    assert any(label.pixmap() and not label.pixmap().isNull()
               for label in window.page_area.widget().findChildren(QLabel))


def test_cancel_or_invalid_image_keeps_previous_photo(qtbot, tmp_path, monkeypatch):
    store = Store(tmp_path / 'data')
    window = Window(store)
    qtbot.addWidget(window)
    dialog = RecordDialog(None, 'printers', store.read())
    qtbot.addWidget(dialog)
    field = dialog.fields['image']
    field.setText('existing-photo')
    label = QLabel('Įkelta')
    qtbot.addWidget(label)
    monkeypatch.setattr('printtrack.ui.isolated_photo', lambda *a: None)
    dialog.pick_image(field, label)
    assert field.text() == 'existing-photo'
    invalid = tmp_path / 'invalid.png'
    invalid.write_text('not an image')
    monkeypatch.setattr('printtrack.ui.isolated_photo', lambda *a: photo_png(invalid))
    messages = []
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a, **kw: messages.append(a))
    dialog.pick_image(field, label)
    assert messages
    assert field.text() == 'existing-photo'


@pytest.mark.parametrize('mode', ['RGBA', 'P', 'LA', 'I;16'])
def test_png_variants_normalize_to_viewable_png(qtbot, tmp_path, mode):
    path = tmp_path / 'spausdintuvas.png'
    Image.new(mode, (960, 960)).save(path)
    data = photo_png(path)
    pix = QPixmap()
    assert pix.loadFromData(data, 'PNG')
    assert pix.width() == 640 and pix.height() == 640


def test_real_pick_button_uses_non_native_dialog(qtbot, tmp_path, monkeypatch):
    path = tmp_path / 'brother.png'
    Image.new('RGBA', (960, 960), (40, 50, 60, 128)).save(path)
    store = Store(tmp_path / 'data')
    dialog = RecordDialog(None, 'printers', store.read())
    qtbot.addWidget(dialog)
    calls = []
    def choose(*args):
        calls.append(True)
        return photo_png(path)
    monkeypatch.setattr('printtrack.ui.isolated_photo', choose)
    pick = next(b for b in dialog.findChildren(QPushButton) if b.text() == 'Pasirinkti…')
    qtbot.mouseClick(pick, Qt.LeftButton)
    assert calls
    assert dialog.values()['image']
