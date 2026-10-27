import csv
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from printtrack.store import CATALOGUE, Store, ValidationError, demo_store, kpis, stock, usage


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / 'data')
    room = store.save('rooms', dict(name='201', department='Terapija', floor='2'))
    values = dict(name='Registratūra', model='HP 1020', ip='192.168.0.2', serial='SN001', room_id=room, status='Veikia', image='')
    printer = store.save('printers', values)
    cartridge = store.read()['cartridges'][0]['id']
    return store, room, printer, cartridge


def verify(store, printer, cartridge):
    return store.save('compatibility', dict(printer_id=printer, cartridge_id=cartridge, evidence='Gamintojo vadovas; V. Pavardenis'))


def test_empty_persistence_and_catalogue(tmp_path):
    s = Store(tmp_path)
    assert [c['code'] for c in s.read()['cartridges']] == CATALOGUE
    assert not s.read()['compatibility']
    assert kpis(s.read()) == dict(printers=0, stock=0, low=0, issued=0)
    assert Store(tmp_path).read() == s.read()


def test_register_edit_and_validation(setup):
    s, room, printer, cartridge = setup
    p = s.read()['printers'][0]
    s.save('printers', dict(p, name='Naujas vardas'), printer)
    assert s.read()['printers'][0]['name'] == 'Naujas vardas'
    s.save('cartridges', dict(code='TEST-99', kind='Suderinama', chip='Taip', minimum=3, image=''))
    before = s.read()
    with pytest.raises(ValidationError):
        s.save('printers', dict(p, ip='999.1.1.1'), printer)
    assert s.read() == before
    with pytest.raises(ValidationError):
        s.save('rooms', dict(name='', department='', floor=''))


def test_issue_requires_explicit_verification(setup):
    s, _, p, c = setup
    s.movement('receipt', c, 5, note='Sąskaita 1')
    with pytest.raises(ValidationError, match='nepatvirtintas'):
        s.movement('issue', c, 1, p, 'Dokumentas 1')
    record = verify(s, p, c)
    s.movement('issue', c, 2, p, 'Dokumentas 2')
    assert stock(s.read(), c) == 3
    m = s.read()['movements'][-1]
    assert (m['department'], m['room'], m['printer']) == ('Terapija', '201', 'Registratūra')
    assert m['evidence']
    s.revoke(record)
    with pytest.raises(ValidationError):
        s.movement('issue', c, 1, p, 'Dokumentas 3')


def test_change_identity_invalidates_verification(setup):
    s, _, p, c = setup
    verify(s, p, c)
    item = s.read()['printers'][0]
    s.save('printers', dict(item, model='Kitas modelis'), p)
    assert not s.read()['compatibility']
    verify(s, p, c)
    item = s.read()['cartridges'][0]
    s.save('cartridges', dict(item, chip='Taip'), c)
    assert not s.read()['compatibility']


def test_negative_and_invalid_inventory_rejected(setup):
    s, _, p, c = setup
    verify(s, p, c)
    s.movement('receipt', c, 2, note='Gavimas')
    before = s.read()
    for kind, amount in [('issue', 3), ('receipt', -1), ('adjustment', -3), ('issue', 0), ('receipt', 1.5), ('receipt', True)]:
        with pytest.raises(ValidationError):
            s.movement(kind, c, amount, p, 'Bandymas')
    assert s.read() == before
    s.movement('adjustment', c, -1, note='Inventorizacija')
    assert stock(s.read(), c) == 1


def test_concurrent_issues_cannot_overspend(setup):
    s, _, p, c = setup
    verify(s, p, c)
    s.movement('receipt', c, 1, note='Gavimas')
    def issue(_):
        try:
            s.movement('issue', c, 1, p, 'Išdavimas')
            return True
        except ValidationError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(issue, range(2))) == [False, True]
    assert stock(s.read(), c) == 0


def test_backup_restore_keeps_history(setup, tmp_path):
    s, _, p, c = setup
    s.movement('receipt', c, 5, note='Gavimas')
    backup = tmp_path / 'backup.json'
    s.backup(backup)
    s.movement('adjustment', c, -2, note='Inventorizacija')
    old = s.read()['movements'][:]
    s.restore(backup)
    assert stock(s.read(), c) == 5
    assert s.read()['movements'][:len(old)] == old
    assert s.read()['movements'][-1]['kind'] == 'restore'
    assert list(s.backups.glob('*.json'))


def test_journal_recovery_after_interrupted_commit(setup, monkeypatch):
    s, _, _, c = setup
    original = s._atomic
    def fail(path, value):
        if path == s.path:
            raise OSError('simulated power failure')
        original(path, value)
    monkeypatch.setattr(s, '_atomic', fail)
    with pytest.raises(OSError):
        s.movement('receipt', c, 7, note='Gavimas')
    assert s.journal.exists()
    reopened = Store(s.directory)
    assert stock(reopened.read(), c) == 7
    assert not s.journal.exists()


def test_corrupt_file_emergency_recovery(setup):
    s, _, _, c = setup
    s.movement('receipt', c, 4, note='Gavimas')
    backup = s.backup()
    s.path.write_text('broken', encoding='utf-8')
    with pytest.raises(ValidationError):
        Store(s.directory)
    recovered = Store.recover_backup(s.directory, backup)
    assert stock(recovered.read(), c) == 4
    assert list(s.directory.glob('*.damaged-*'))


def test_csv_roundtrip_and_atomic_validation(setup, tmp_path):
    s, _, p, c = setup
    for kind in ['rooms', 'printers', 'cartridges']:
        path = tmp_path / f'{kind}.csv'
        s.export_csv(kind, path)
        before = s.read()[kind]
        assert s.import_csv(kind, path) == len(before)
        assert s.read()[kind] == before
    path = tmp_path / 'bad.csv'
    path.write_text('id,department,floor,name\n,Terapija,1,101\n,,,\n', encoding='utf-8')
    before = s.read()
    with pytest.raises(ValidationError):
        s.import_csv('rooms', path)
    assert s.read() == before


def test_reports_snapshot_and_kpis(setup):
    s, room, p, c = setup
    verify(s, p, c)
    s.movement('receipt', c, 10, note='Gavimas')
    s.movement('issue', c, 3, p, 'Išdavimas')
    row = s.read()['rooms'][0]
    s.save('rooms', dict(row, department='Kitas skyrius'), room)
    assert usage(s.read(), 'department') == [('Terapija', 3)]
    assert usage(s.read(), 'room', department='Terapija') == [('201', 3)]
    assert usage(s.read(), 'printer', cartridge='Q2612A') == [('Registratūra', 3)]
    assert usage(s.read(), department='Kitas skyrius') == []
    assert kpis(s.read())['issued'] == 3
    assert kpis(s.read())['stock'] == 7


def test_demo_is_separate(tmp_path):
    real = Store(tmp_path / 'real')
    demo = demo_store(tmp_path / 'demo')
    assert demo.read()['demo'] is True
    assert kpis(demo.read())['stock'] == 10
    assert real.read()['printers'] == []
