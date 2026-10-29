import json
from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtWidgets import QMessageBox

from printtrack.licensing import CONTACT, EXPIRED_MESSAGE, Licence, two_years_after
from printtrack.store import Store, ValidationError
from printtrack.ui import Window


UTC = timezone.utc


def test_two_calendar_years_and_exact_expiry_boundary(tmp_path):
    clock = [datetime(2026, 10, 29, 10, 30, tzinfo=UTC)]
    licence = Licence(tmp_path / 'license.json', clock=lambda: clock[0])
    assert licence.status().active
    assert licence.status().expires_at == datetime(2028, 10, 29, 10, 30, tzinfo=UTC)
    clock[0] = licence.status().expires_at - timedelta(microseconds=1)
    assert licence.status().active
    clock[0] += timedelta(microseconds=1)
    assert not licence.status().active
    assert licence.status().message == EXPIRED_MESSAGE
    assert CONTACT == 'gedtre@gmail.com'


def test_leap_day_uses_february_28():
    assert two_years_after(datetime(2028, 2, 29, 12, tzinfo=UTC)) == datetime(2030, 2, 28, 12, tzinfo=UTC)


def test_relaunch_and_data_restore_do_not_extend_licence(tmp_path):
    clock = [datetime(2026, 10, 29, tzinfo=UTC)]
    path = tmp_path / 'license.json'
    licence = Licence(path, clock=lambda: clock[0])
    original = path.read_bytes()
    store = Store(tmp_path / 'data', write_check=licence.require_active)
    backup = store.backup()
    store.save('rooms', dict(name='101', department='IT', floor='1'))
    store.restore(backup)
    clock[0] = datetime(2027, 11, 1, tzinfo=UTC)
    reopened = Licence(path, clock=lambda: clock[0])
    assert reopened.status().active
    assert path.read_bytes() == original
    clock[0] = datetime(2028, 10, 29, tzinfo=UTC)
    assert not Licence(path, clock=lambda: clock[0]).status().active


def test_expiry_blocks_all_mutations_but_preserves_read_export_backup(tmp_path):
    clock = [datetime(2026, 1, 1, tzinfo=UTC)]
    licence = Licence(tmp_path / 'license.json', clock=lambda: clock[0])
    store = Store(tmp_path / 'data', write_check=licence.require_active)
    store.save('rooms', dict(name='101', department='IT', floor='1'))
    cartridge = store.read()['cartridges'][0]['id']
    store.movement('receipt', cartridge, 5, note='Gavimas')
    backup = store.backup()
    csv_path = tmp_path / 'rooms.csv'
    store.export_csv('rooms', csv_path)
    before = store.read()
    clock[0] = datetime(2028, 1, 1, tzinfo=UTC)
    for operation in [
        lambda: store.save('rooms', dict(name='102', department='IT', floor='1')),
        lambda: store.movement('receipt', cartridge, 1, note='Bandymas'),
        lambda: store.import_csv('rooms', csv_path),
        lambda: store.restore(backup),
        lambda: store.revoke('anything'),
    ]:
        with pytest.raises(ValidationError, match='gedtre@gmail.com'):
            operation()
        assert store.read() == before
    assert store.backup().exists()
    store.export_csv('rooms', csv_path)
    assert '101' in csv_path.read_text('utf-8-sig')
    assert json.loads(store.path.read_text('utf-8')) == before


@pytest.mark.parametrize('replacement', ['not json', '{}', '[]', '{"version":2}'])
def test_damaged_licence_does_not_reset(tmp_path, replacement):
    licence = Licence(tmp_path / 'license.json')
    licence.path.write_text(replacement)
    reopened = Licence(licence.path)
    assert not reopened.status().active
    with pytest.raises(ValidationError):
        reopened.require_active()
    assert licence.path.read_text() == replacement


def test_running_window_announces_expiry_once_and_keeps_pages_available(qtbot, tmp_path, monkeypatch):
    clock = [datetime(2026, 1, 1, tzinfo=UTC)]
    licence = Licence(tmp_path / 'license.json', clock=lambda: clock[0])
    store = Store(tmp_path / 'data', write_check=licence.require_active)
    window = Window(store, licence=licence)
    qtbot.addWidget(window)
    notices = []
    monkeypatch.setattr(QMessageBox, 'information', lambda parent, title, message: notices.append(message))
    window.check_licence()
    assert not notices
    clock[0] = datetime(2028, 1, 1, tzinfo=UTC)
    window.check_licence()
    window.check_licence()
    assert len(notices) == 1
    assert EXPIRED_MESSAGE in notices[0]
    assert 'Tik peržiūra' in window.licence_banner.text()
    for i in range(10):
        window.nav.setCurrentRow(i)
        assert window.page_area.widget() is not None
    assert licence.status().message in window.licence_banner.text()
