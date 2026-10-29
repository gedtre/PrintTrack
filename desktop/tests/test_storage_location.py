import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QFileDialog, QLineEdit, QPushButton

from printtrack.storage_location import open_existing, relocate, selected_file, remember_file
from printtrack.store import Store, ValidationError, demo_store
from printtrack.ui import Window


def populated_store(path):
    store = Store(path)
    store.save('rooms', dict(name='101', department='IT', floor='1'))
    store.movement('receipt', store.read()['cartridges'][0]['id'], 3, note='Testas')
    return store


def test_move_preserves_records_history_and_backups_and_remembers_path(tmp_path):
    store = populated_store(tmp_path / 'original')
    before = store.read()
    destination = tmp_path / 'network-like'
    destination.mkdir()
    config = tmp_path / 'user-settings.json'
    target = relocate(store, destination / 'bendri-duomenys.json', config)
    assert target.read() == before
    assert store.read() == before
    assert set(p.name for p in store.backups.glob('*.json')).issubset({p.name for p in target.backups.glob('*.json')})
    assert selected_file(config) == target.path
    assert open_existing(selected_file(config), config).read() == before
    target.save('rooms', dict(name='102', department='IT', floor='1'))
    assert len(store.read()['rooms']) == 1
    assert len(target.read()['rooms']) == 2


def test_custom_filename_in_same_directory_has_independent_journal_and_backups(tmp_path):
    store = populated_store(tmp_path / 'data')
    target = relocate(store, store.directory / 'kitas.json', tmp_path / 'settings.json')
    assert target.path.name == 'kitas.json'
    assert target.journal != store.journal
    assert target.backups != store.backups
    assert target.read() == store.read()


def test_existing_destination_is_not_overwritten(tmp_path):
    source = populated_store(tmp_path / 'source')
    other = Store(tmp_path / 'other')
    before = other.path.read_bytes()
    config = tmp_path / 'settings.json'
    remember_file(source.path, config)
    with pytest.raises(ValidationError, match='jau egzistuoja'):
        relocate(source, other.path, config)
    assert other.path.read_bytes() == before
    assert selected_file(config) == source.path


def test_switch_does_not_merge_or_initialize_missing_target(tmp_path):
    source = populated_store(tmp_path / 'source')
    target = Store(tmp_path / 'other')
    config = tmp_path / 'settings.json'
    remember_file(source.path, config)
    missing = tmp_path / 'offline' / 'inventory.json'
    with pytest.raises(ValidationError, match='nepasiekiamas'):
        open_existing(missing, config)
    assert not missing.parent.exists()
    assert selected_file(config) == source.path
    switched = open_existing(target.path, config)
    assert not switched.read()['rooms']
    assert len(source.read()['rooms']) == 1
    assert selected_file(config) == target.path


def test_invalid_file_and_demo_do_not_replace_saved_location(tmp_path):
    source = Store(tmp_path / 'source')
    config = tmp_path / 'settings.json'
    remember_file(source.path, config)
    corrupt = tmp_path / 'corrupt.json'
    corrupt.write_text('not json')
    for path in [corrupt, demo_store(tmp_path / 'demo').path]:
        with pytest.raises(ValidationError):
            open_existing(path, config)
        assert selected_file(config) == source.path


@pytest.mark.parametrize('name', ['pending.json', 'settings.json', 'license.json', 'x.pending.json'])
def test_reserved_names_are_not_written(tmp_path, name):
    source = Store(tmp_path / 'source')
    with pytest.raises(ValidationError):
        relocate(source, tmp_path / name, tmp_path / 'config.json')
    assert not (tmp_path / name).exists()


def test_failed_config_save_keeps_original_intact(tmp_path, monkeypatch):
    from printtrack import storage_location
    source = populated_store(tmp_path / 'source')
    before = source.read()
    def fail(*args, **kwargs):
        raise OSError('Settings unavailable')
    monkeypatch.setattr(storage_location, 'remember_file', fail)
    with pytest.raises(OSError):
        relocate(source, tmp_path / 'new.json', tmp_path / 'config.json')
    assert source.read() == before


def test_custom_filename_emergency_recovery_preserves_damaged_file(tmp_path):
    store = Store(tmp_path, filename='bendri.json')
    backup = store.backup()
    store.path.write_text('broken')
    restored = Store.recover_backup(tmp_path, backup, filename='bendri.json')
    assert restored.path.name == 'bendri.json'
    assert list(tmp_path.glob('bendri.json.damaged-*'))
    assert restored.read()['version'] == 1


def test_settings_move_and_switch_update_live_store(qtbot, tmp_path, monkeypatch):
    source = populated_store(tmp_path / 'source')
    window = Window(source, config_path=tmp_path / 'config.json')
    qtbot.addWidget(window)
    window.nav.setCurrentRow(9)
    assert any(b.text() == 'Perkelti dabartinius duomenis…' for b in window.findChildren(QPushButton))
    monkeypatch.setattr(window, 'confirm', lambda text: True)
    destination = tmp_path / 'perkeltas.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (str(destination), ''))
    window.move_data()
    assert window.store.path == destination
    assert window.findChild(QLineEdit, '').text() == str(destination)
    other = Store(tmp_path / 'other')
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *a: (str(other.path), ''))
    window.choose_data()
    assert window.store.path == other.path
    assert not window.store.read()['rooms']


def test_real_restart_uses_saved_file_and_ignores_old_expired_licence(tmp_path):
    app_data = tmp_path / 'profile'
    config = app_data / 'PrintTrack' / 'settings.json'
    source = populated_store(tmp_path / 'external')
    before = source.read()
    remember_file(source.path, config)
    (config.parent / 'license.json').write_text('{"version":1,"issued_at":"2020-01-01T00:00:00+00:00","expires_at":"2022-01-01T00:00:00+00:00"}')
    env = dict(os.environ, LOCALAPPDATA=str(app_data), QT_QPA_PLATFORM='offscreen')
    main = Path(__file__).resolve().parents[1] / 'main.py'
    result = subprocess.run([sys.executable, str(main), '--smoke-test'], env=env, timeout=45, capture_output=True)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    assert Store(source.directory).read() == before
    assert not (app_data / 'PrintTrack' / 'data' / 'inventory.json').exists()
    source.path.unlink()
    result = subprocess.run([sys.executable, str(main), '--smoke-test'], env=env, timeout=45, capture_output=True)
    assert result.returncode == 2
    assert not source.path.exists()
    assert not (app_data / 'PrintTrack' / 'data' / 'inventory.json').exists()
