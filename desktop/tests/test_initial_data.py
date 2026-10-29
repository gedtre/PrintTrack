import copy

import pytest

from printtrack.initial_data import apply_initial_data, bundled_initial_data, room_number
from printtrack.store import Store, ValidationError, demo_store, kpis


@pytest.mark.parametrize('raw,expected', [
    ('118.', '118'), ('119 kab.', '119'), ('119_1', '119'),
    ('202(II lygis)', '202'), ('510 - II Lygis', '510'),
    ('4.blogas', '4'), ('245A', '245A'), ('237a', '237A'), ('Numeris', ''),
])
def test_room_number(raw, expected):
    assert room_number(raw) == expected


def test_bundled_data_is_complete_unique_and_unassigned(tmp_path):
    payload = bundled_initial_data()
    assert payload is not None
    store = Store(tmp_path, initial_catalogue=False)
    assert apply_initial_data(store, payload)
    state = store.read()
    assert len(state['rooms']) == len({room_number(r['name']) for r in state['rooms']}) == 102
    assert len(state['printers']) == 25
    assert len(state['cartridges']) == 34
    assert all(p['status'] == 'Nepriskirtas' and not p['room_id'] and not p['serial'] for p in state['printers'])
    assert not state['movements'] and not state['compatibility']
    assert kpis(state)['stock'] == 0
    assert next(p for p in state['printers'] if p['model'] == 'UTAX CD5130')['source_cartridge_codes'] == ''
    assert next(r for r in state['rooms'] if r['name'] == '118')['department'].count(' / ') == 2
    before = store.read()
    assert apply_initial_data(store, payload) is False
    assert Store(tmp_path).read() == before


def test_existing_inventory_and_history_survive_merge(tmp_path):
    store = Store(tmp_path)
    room = store.save('rooms', dict(name='118.', department='Mano skyrius', floor='2'))
    printer = store.save('printers', dict(name='Esamas', model='HP LaserJet 1020',
        ip='', serial='SN-1', room_id=room, status='Veikia', image=''))
    cartridge = store.read()['cartridges'][0]['id']
    store.movement('receipt', cartridge, 7, note='Esami likučiai')
    before = store.read()
    apply_initial_data(store, bundled_initial_data())
    after = store.read()
    assert after['movements'] == before['movements']
    assert next(p for p in after['printers'] if p['id'] == printer) == before['printers'][0]
    assert next(r for r in after['rooms'] if r['id'] == room) == before['rooms'][0]
    assert sum(room_number(r['name']) == '118' for r in after['rooms']) == 1
    assert sum(p['model'] == 'HP LaserJet 1020' for p in after['printers']) == 1


def test_invalid_package_rolls_back_atomically(tmp_path):
    store = Store(tmp_path)
    before = store.read()
    payload = copy.deepcopy(bundled_initial_data())
    payload['printers'][0]['model'] = ''
    with pytest.raises(ValidationError):
        apply_initial_data(store, payload)
    assert store.read() == before


def test_demo_does_not_receive_user_data(tmp_path):
    store = demo_store(tmp_path)
    before = store.read()
    assert apply_initial_data(store, bundled_initial_data()) is False
    assert store.read() == before
