import base64
import io
import json

from PIL import Image
from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QTableWidget

from printtrack.store import Store
from printtrack.ui import Window, PhotoLabel, PhotoDelegate
from printtrack.storage_location import relocate


def photo_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (640, 480), (50, 80, 100)).save(buffer, format='PNG')
    return buffer.getvalue()


def test_real_modal_save_refresh_reopen_and_main_hover(qtbot, tmp_path):
    store = Store(tmp_path / 'data')
    row_id = store.save('printers', dict(name='HP 400', model='HP 400', ip='',
        serial='', room_id='', status='Nepriskirtas', image=''))
    window = Window(store)
    qtbot.addWidget(window)
    window.show()
    window.nav.setCurrentRow(1)
    for attempt in range(3):
        def save():
            dialog = QApplication.activeModalWidget()
            label = dialog.findChild(PhotoLabel)
            dialog.apply_photo(photo_bytes(), dialog.fields['image'], label)
            dialog.accept()
        QTimer.singleShot(0, save)
        window.edit_record('printers', row_id)
        QApplication.processEvents()
        row = Store(store.directory).read()['printers'][0]
        assert row['image'].startswith('images/')
        assert (store.directory / row['image']).read_bytes() == photo_bytes()
        table = window.page_area.widget().findChild(QTableWidget)
        table.selectRow(0)
        delegate = table.itemDelegateForColumn(0)
        assert isinstance(delegate, PhotoDelegate)
        point = table.visualItemRect(table.item(0, 0)).center()
        from PySide6.QtCore import QPointF
        event = QMouseEvent(QEvent.MouseMove, QPointF(point), QPointF(point), Qt.NoButton, Qt.NoButton, Qt.NoModifier)
        delegate.eventFilter(table.viewport(), event)
        assert delegate.popup.isVisible()
        assert delegate.popup.pixmap().width() > 100
        window.refresh()
        QApplication.processEvents()
    assert len(list((store.directory / 'images').glob('*.png'))) == 1


def test_files_relocate_and_portable_backup_restore(tmp_path):
    store = Store(tmp_path / 'data')
    row_id = store.save('printers', dict(name='Test', model='HP', ip='', serial='',
        room_id='', status='Nepriskirtas', image=base64.b64encode(photo_bytes()).decode()))
    state = store.read()
    assert state['printers'][0]['image'].startswith('images/')
    backup = tmp_path / 'portable-backup.json'
    store.backup(backup)
    assert base64.b64decode(json.loads(backup.read_text())['printers'][0]['image']) == photo_bytes()
    destination = tmp_path / 'relocated'
    destination.mkdir()
    target = relocate(store, destination / 'inventory.json', tmp_path / 'settings.json')
    assert target.read() == state
    assert target.image_bytes(target.read()['printers'][0]['image']) == photo_bytes()
    restored = Store(tmp_path / 'restored', initial_catalogue=False)
    restored.restore(backup)
    row = next(r for r in restored.read()['printers'] if r['id'] == row_id)
    assert row['image'].startswith('images/')
    assert restored.image_bytes(row['image']) == photo_bytes()
